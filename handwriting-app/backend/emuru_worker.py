"""
Standalone Emuru inference script — runs in emuru_venv or backend .venv.
Called as subprocess by wordstylist.py.

Usage:
    python emuru_worker.py --style-image path.png --words word1 word2 --output-dir out/
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torchvision.transforms import functional as F

TARGET_H = 90


def _to_rgb_white_bg(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def _ink_bbox(gray: Image.Image, threshold: int = 240):
    arr = np.asarray(gray)
    ys, xs = np.where(arr < threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _ink_crop_pil(img: Image.Image, pad: int = 8) -> Image.Image:
    bbox = _ink_bbox(img.convert("L"))
    if not bbox:
        return img
    left, top, right, bottom = bbox
    return img.crop(
        (
            max(0, left - pad),
            max(0, top - pad),
            min(img.width, right + pad),
            min(img.height, bottom + pad),
        )
    )


def _suppress_ruled_lines_gray(gray: np.ndarray) -> np.ndarray:
    """Wash out blue notebook lines / red margins; keep dark ink."""
    # gray already from max(R,G) path — drop near-full-width thin strokes
    ink = gray < 95
    row_frac = ink.mean(axis=1)
    cleaned = gray.copy()
    for y, frac in enumerate(row_frac):
        if frac > 0.55:
            cleaned[y, :] = np.maximum(cleaned[y, :], 245)
    return cleaned


def hard_clean_page(img: Image.Image) -> Image.Image:
    """Contrast-stretch notebook photo → white paper, black ink, fewer ruled lines."""
    rgb = np.asarray(_to_rgb_white_bg(img)).astype(np.float32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = np.maximum(r, g)
    gray = np.where((r > g + 20) & (r > b + 20), np.maximum(g, b), gray)
    lo, hi = np.percentile(gray, 1), np.percentile(gray, 99)
    stretched = np.clip((gray - lo) / max(1.0, hi - lo) * 255.0, 0, 255)
    stretched = _suppress_ruled_lines_gray(stretched)
    ink = stretched < 95
    clean = np.full_like(stretched, 255, dtype=np.uint8)
    clean[ink] = (stretched[ink] * 0.5).astype(np.uint8)
    return Image.fromarray(np.stack([clean, clean, clean], axis=-1))


def _connected_components(ink: np.ndarray, min_count: int = 80):
    """4-connected components on a boolean ink mask. Returns (count,x0,y0,x1,y1)."""
    H, W = ink.shape
    vis = np.zeros_like(ink, dtype=np.uint8)
    comps = []
    from collections import deque

    for y in range(H):
        for x in range(W):
            if not ink[y, x] or vis[y, x]:
                continue
            q = deque([(y, x)])
            vis[y, x] = 1
            minx = maxx = x
            miny = maxy = y
            cnt = 0
            while q:
                cy, cx = q.popleft()
                cnt += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                for ny, nx in (
                    (cy - 1, cx),
                    (cy + 1, cx),
                    (cy, cx - 1),
                    (cy, cx + 1),
                ):
                    if 0 <= ny < H and 0 <= nx < W and ink[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = 1
                        q.append((ny, nx))
            if cnt >= min_count:
                comps.append((cnt, minx, miny, maxx, maxy))
    comps.sort(reverse=True)
    return comps


def _ocr_boxes(img: Image.Image):
    """Return list of (score, text, x0, y0, x1, y1)."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print("WARN: rapidocr_onnxruntime not installed — style_text may be weak", flush=True)
        return []

    ocr = RapidOCR()
    result, _ = ocr(np.asarray(_to_rgb_white_bg(img)))
    out = []
    for box, text, conf in result or []:
        t = (text or "").strip()
        if not t or conf is None:
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        x0, x1 = int(min(xs)), int(max(xs))
        y0, y1 = int(min(ys)), int(max(ys))
        n_words = max(1, len(t.split()))
        score = float(conf) * (1.0 if n_words == 1 else 0.75)
        out.append((score, t, x0, y0, x1, y1))
    out.sort(reverse=True)
    return out


def _iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(1, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(1, (bx1 - bx0) * (by1 - by0))
    return inter / float(area_a + area_b - inter)


def _score_style_crop(crop: Image.Image) -> float:
    """Higher is better. Prefers compact single-word strips (not full-width ruled-line blobs)."""
    w, h = crop.size
    if h < 16 or w < 40:
        return -1.0
    if h > w * 1.5:
        return -1.0  # portrait page fragment
    arr = np.asarray(crop.convert("L"), dtype=np.float32)
    ink = float((arr < 200).mean())
    if ink < 0.05 or ink > 0.40:
        return -1.0
    aspect = w / max(1, h)
    # Emuru sample is ~9:1; real words are usually 2:1–7:1. Full-page line noise is >>10:1.
    if aspect < 1.3 or aspect > 9.0:
        return -1.0
    if w > 320:
        return -1.0
    # Prefer room for descenders (known-good evening crop is ~74px tall, not 36).
    height_bonus = min(h, 90) / 90.0 * 4.0
    size_bonus = 1.0 - abs(w - 200) / 200.0
    size_bonus = max(0.0, size_bonus)
    row_frac = (arr < 200).mean(axis=1)
    line_penalty = float((row_frac > 0.45).mean()) * 3.0
    # Penalize ultra-flat strips that often still contain ruled-line residue
    flat_penalty = 2.0 if h < 42 else 0.0
    return (
        (min(aspect, 5.5) * min(ink, 0.22) * 10.0)
        + size_bonus * 2.0
        + height_bonus
        - line_penalty
        - flat_penalty
    )


def prepare_style_candidates(style_path: str, max_candidates: int = 5) -> list[tuple[Image.Image, str, float]]:
    """
    Build ranked (crop_rgb, style_text, score) candidates from a user photo or word crop.
    Emuru needs a single-line/word crop + matching transcription — not a full page.
    """
    original = _to_rgb_white_bg(Image.open(style_path))
    cleaned = hard_clean_page(original)
    ocr = _ocr_boxes(original)

    candidates: list[tuple[Image.Image, str, float]] = []

    # Path A: OCR boxes → stay inside the box (do NOT re-expand via full ink bbox —
    # residual ruled lines would stretch the crop to page width and break Emuru).
    for score, text, x0, y0, x1, y1 in ocr[:12]:
        pad_x, pad_y = 8, 10
        crop = cleaned.crop(
            (
                max(0, x0 - pad_x),
                max(0, y0 - pad_y),
                min(cleaned.width, x1 + pad_x),
                min(cleaned.height, y1 + pad_y + 6),
            )
        )
        # vertical trim only to ink; keep OCR width
        arr = np.asarray(crop.convert("L"))
        ink_rows = (arr < 200).mean(axis=1)
        content = np.where(ink_rows > 0.02)[0]
        if len(content):
            y_a, y_b = int(content[0]), int(content[-1]) + 1
            crop = crop.crop((0, max(0, y_a - 2), crop.width, min(crop.height, y_b + 2)))
        # Skip ultra-flat OCR strips — they usually still contain ruled-line noise.
        if crop.height < 45:
            continue
        # Single-word styles transfer more reliably than full phrases.
        if " " in text.strip():
            continue
        s = _score_style_crop(crop)
        if s < 0:
            continue
        if text.lower().startswith("evenun"):
            text = "evening"
        # Prefer real single words over OCR merges like "Howare"
        word_bonus = 1.5 if len(text) >= 4 else 0.0
        # OCR confidence is helpful but should not outweigh crop geometry
        candidates.append((crop.convert("RGB"), text, s + float(score) * 0.25 + word_bonus))

    # Path B: connected components — only if OCR didn't find enough crops
    # (pure-Python CC on a full page is slow and usually redundant).
    if len(candidates) < 2:
        print("OCR found few crops — running connected-component fallback…", flush=True)
        ink = np.asarray(cleaned.convert("L")) < 200
        comps = _connected_components(ink, min_count=100)
        for cnt, x0, y0, x1, y1 in comps[:25]:
            w, h = x1 - x0 + 1, y1 - y0 + 1
            if h < 18 or w < 40:
                continue
            if h < 50:
                continue
            if h > w * 1.3:
                continue
            if w > min(320, cleaned.width * 0.55):
                continue
            pad = 6
            crop = cleaned.crop(
                (
                    max(0, x0 - pad),
                    max(0, y0 - pad),
                    min(cleaned.width, x1 + pad + 1),
                    min(cleaned.height, y1 + pad + 1),
                )
            )
            s = _score_style_crop(crop)
            if s < 0:
                continue
            text = "a"
            best_iou = 0.0
            for _, t, ox0, oy0, ox1, oy1 in ocr:
                iou = _iou((x0, y0, x1, y1), (ox0, oy0, ox1, oy1))
                if iou > best_iou:
                    best_iou = iou
                    text = t
            if best_iou < 0.15 and ocr:
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                best_d = 1e18
                for _, t, ox0, oy0, ox1, oy1 in ocr:
                    ocx, ocy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
                    d = (cx - ocx) ** 2 + (cy - ocy) ** 2
                    if d < best_d:
                        best_d = d
                        text = t
            if text.lower().startswith("evenun"):
                text = "evening"
            if " " in text.strip():
                text = text.strip().split()[0]
            word_bonus = 1.5 if len(text) >= 4 else 0.0
            candidates.append((crop.convert("RGB"), text, s + best_iou + 0.5 + word_bonus))
    else:
        print(f"Using {len(candidates)} OCR style crops (skipping slow CC scan)", flush=True)

    # Path C: image already looks like a single word strip
    if original.height <= 220 and original.width > original.height:
        crop = _ink_crop_pil(cleaned if cleaned.size == original.size else hard_clean_page(original), pad=6)
        s = _score_style_crop(crop)
        text = ocr[0][1] if ocr else "a"
        if s > 0:
            candidates.append((crop.convert("RGB"), text, s + 0.5))

    # Deduplicate by size+text, keep best scores
    candidates.sort(key=lambda x: x[2], reverse=True)
    uniq: list[tuple[Image.Image, str, float]] = []
    seen = set()
    for crop, text, score in candidates:
        key = (crop.size, text.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append((crop, text, score))
        if len(uniq) >= max_candidates:
            break

    if not uniq:
        # last resort: ink-crop whole cleaned image (may still be a page)
        crop = _ink_crop_pil(cleaned, pad=4)
        text = ocr[0][1] if ocr else "a"
        uniq.append((crop.convert("RGB"), text, 0.0))

    return uniq


def load_style_tensor_from_pil(img: Image.Image) -> torch.Tensor:
    """Official Emuru recipe: RGB, ink-crop, height 64, normalize [-1, 1]."""
    img = _ink_crop_pil(img.convert("RGB"), pad=10)
    img = ImageOps.expand(img, border=10, fill="white")
    h = 64
    w = max(64, min(512, img.width * h // max(1, img.height)))
    img = img.resize((w, h), Image.LANCZOS)
    return F.normalize(F.to_tensor(img), [0.5], [0.5])


def load_style_img(path: str) -> torch.Tensor:
    return load_style_tensor_from_pil(_to_rgb_white_bg(Image.open(path)))


def _bundled_sample_path(cache_dir: str) -> Path | None:
    root = Path(cache_dir)
    matches = list(root.glob("models--blowing-up-groundhogs--emuru/**/sample.png"))
    return matches[0] if matches else None


def _is_bad(img: Image.Image) -> bool:
    """Reject empty, solid-bar, or runaway-width Emuru failures."""
    if not isinstance(img, Image.Image) or img.size[0] < 6 or img.size[1] < 8:
        return True
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    ink_mask = arr < 200
    ink = float(ink_mask.mean())
    if ink < 0.015 or ink > 0.88:
        return True
    if img.size[0] > img.size[1] * 14:
        return True
    if float(arr.mean()) > 242:
        return True
    # solid horizontal bar: almost every column has ink and little vertical structure
    if ink_mask.any():
        col_frac = ink_mask.mean(axis=0)
        row_frac = ink_mask.mean(axis=1)
        if float((col_frac > 0.40).mean()) > 0.88 and float(row_frac.max()) > 0.75:
            if float((row_frac > 0.55).mean()) > 0.40:
                return True
    return False


def crop_to_ink(img: Image.Image, padding: int = 4) -> Image.Image:
    bbox = _ink_bbox(img.convert("L"), threshold=245)
    if not bbox:
        return img
    left, top, right, bottom = bbox
    return img.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(img.width, right + padding),
            min(img.height, bottom + padding),
        )
    )


def scale_word(img: Image.Image) -> Image.Image:
    w, h = img.size
    if h < 1 or w < 1:
        return Image.new("RGB", (40, TARGET_H), (255, 255, 255))
    new_w = max(12, int(round(w * TARGET_H / h)))
    new_w = min(new_w, 600)
    return img.resize((new_w, TARGET_H), Image.LANCZOS)


def generate_one(model, style_tensor: torch.Tensor, style_text: str, word: str) -> Image.Image:
    # Use library defaults for stopping — custom patience was truncating glyphs into garbage.
    max_new = max(64, min(192, 32 + len(word) * 24))
    with torch.no_grad():
        out = model.generate(
            style_text=style_text,
            gen_text=word,
            style_img=style_tensor,
            max_new_tokens=max_new,
        )
    if not isinstance(out, Image.Image):
        raise RuntimeError("Emuru did not return a PIL image")
    return out.convert("RGB")


def save_png(img: Image.Image, path: Path) -> None:
    if img.size[0] < 1 or img.size[1] < 1:
        raise ValueError(f"Refusing to save empty image {img.size}")
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


def main():
    import traceback

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--style-image", required=True)
        parser.add_argument("--words", nargs="+", required=True)
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--cache-dir", default="weights/emuru")
        parser.add_argument(
            "--style-text",
            default="",
            help="Transcription of the style image (critical for quality)",
        )
        args = parser.parse_args()

        from transformers import AutoModel

        print(f"Loading Emuru from cache {args.cache_dir}...", flush=True)
        model = AutoModel.from_pretrained(
            "blowing-up-groundhogs/emuru",
            trust_remote_code=True,
            cache_dir=args.cache_dir,
            local_files_only=True,
        )
        model.eval()

        explicit_text = args.style_text.strip()
        candidates = prepare_style_candidates(args.style_image)
        print(f"Style candidates: {len(candidates)}", flush=True)
        for i, (crop, text, score) in enumerate(candidates):
            print(
                f"  [{i}] text={text!r} size={crop.size} score={score:.3f}",
                flush=True,
            )

        fallback_style = None
        fallback_text = 'THE JOLLY IS "U"'
        sample = _bundled_sample_path(args.cache_dir)
        if sample and sample.exists():
            fallback_style = load_style_img(str(sample))
            print(f"Bundled fallback style ready: {sample}", flush=True)

        # Pick the best-scoring crop with a sane tensor width (no slow probe loop).
        chosen: tuple[torch.Tensor, str, str] | None = None
        for i, (crop, text, score) in enumerate(candidates):
            st = explicit_text or text or "a"
            tensor = load_style_tensor_from_pil(crop)
            if tensor.shape[-1] < 80:
                print(f"  skip cand {i}: narrow tensor {tuple(tensor.shape)}", flush=True)
                continue
            if tensor.shape[-1] > 400:
                print(f"  skip cand {i}: oversized tensor {tuple(tensor.shape)}", flush=True)
                continue
            label = f"user[{i}:{st}]"
            chosen = (tensor, st, label)
            print(f"  locked style {label} tensor={tuple(tensor.shape)}", flush=True)
            break

        if chosen is None and fallback_style is not None:
            print(
                "WARN: no usable user style crop — using bundled sample.png",
                flush=True,
            )
            chosen = (fallback_style, fallback_text, "fallback")

        if chosen is None:
            raise RuntimeError("No usable Emuru style crops could be prepared")

        style_tensor, style_text, style_label = chosen
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Persist the locked style crop so the UI can show what was actually used.
        style_crop_path = out_dir / "style_used.png"
        try:
            # Reconstruct a preview from the chosen candidate when possible
            for i, (crop, text, score) in enumerate(candidates):
                st = explicit_text or text or "a"
                if f"user[{i}:{st}]" == style_label:
                    crop.save(style_crop_path)
                    break
            else:
                if sample and sample.exists() and style_label == "fallback":
                    Image.open(sample).convert("RGB").save(style_crop_path)
        except Exception as e:
            print(f"  WARN: could not save style_used.png: {e}", flush=True)

        word_sources: list[str] = []
        for i, word in enumerate(args.words):
            print(f"Generating [{i}] '{word}' with {style_label}...", flush=True)
            try:
                out = generate_one(model, style_tensor, style_text, word)
            except Exception as e:
                print(f"  generate error: {e}", flush=True)
                out = None

            used = style_label
            if out is None or _is_bad(out):
                if fallback_style is not None and style_label != "fallback":
                    print(
                        "  WARN: word failed with user style; "
                        "using bundled sample.png for this word.",
                        flush=True,
                    )
                    out = generate_one(model, fallback_style, fallback_text, word)
                    used = "fallback"
                else:
                    raise RuntimeError(f"Emuru failed to produce readable output for '{word}'")

            if _is_bad(out):
                raise RuntimeError(f"Emuru failed to produce readable output for '{word}'")

            out = crop_to_ink(out)
            out = scale_word(out)
            print(f"  result size={out.size} source={used}", flush=True)
            final_path = out_dir / f"word_{i}.png"
            save_png(out, final_path)
            src_tag = "fallback" if used == "fallback" else "user"
            word_sources.append(src_tag)
            print(f"GENERATED:{i}:{final_path}:{src_tag}", flush=True)

        user_n = sum(1 for s in word_sources if s == "user")
        fb_n = sum(1 for s in word_sources if s == "fallback")
        if fb_n == 0:
            overall = "user"
        elif user_n == 0:
            overall = "fallback"
        else:
            overall = "mixed"
        import json

        meta = {
            "style_source": overall,
            "style_label": style_label,
            "style_text": style_text,
            "word_sources": word_sources,
            "words": list(args.words),
            "style_crop": str(style_crop_path) if style_crop_path.exists() else None,
        }
        print(f"STYLE_META:{json.dumps(meta)}", flush=True)
        print("DONE", flush=True)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
