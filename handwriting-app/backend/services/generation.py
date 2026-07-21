import os
from pathlib import Path

from models import MODEL_REGISTRY
from models.diffusionpen import get_diffusionpen_instance
from services.compositor import compose_pages
from storage.job_store import get_style, update_job

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))


def _tokenize(text: str) -> list[str]:
    words = text.split()
    return words if words else ["handwriting"]


def _style_summary(model_name: str, instance, words: list[str]) -> dict:
    """Build a UI-facing summary of which style was used."""
    if model_name == "wordstylist":
        meta = getattr(instance, "last_meta", None) or {}
        source = meta.get("style_source") or "user"
        word_sources = meta.get("word_sources") or ["user"] * len(words)
        label_map = {
            "user": "Your uploaded handwriting style",
            "fallback": "Built-in Emuru sample style (user style failed quality check)",
            "mixed": "Mixed — some words used your style, some used the built-in sample",
            "mock": "Placeholder mock (Emuru unavailable)",
            "error": "Error fallback (Emuru failed)",
            "unavailable": "Style unavailable",
        }
        return {
            "style_source": source,
            "style_source_label": label_map.get(source, source),
            "style_text": meta.get("style_text"),
            "style_label": meta.get("style_label"),
            "word_sources": word_sources,
            "words": meta.get("words") or words,
        }

    # DiffusionPen / others always use the uploaded samples
    return {
        "style_source": "user",
        "style_source_label": "Your uploaded handwriting samples",
        "style_text": None,
        "style_label": None,
        "word_sources": ["user"] * len(words),
        "words": words,
    }


def run_generation(
    job_id: str,
    session_id: str,
    text: str,
    model: str,
    pages: int,
) -> None:
    try:
        update_job(
            job_id,
            status="processing",
            progress=10,
            message="Extracting style",
        )

        style = get_style(session_id)
        if not style:
            raise ValueError("Style not found for session")

        words = _tokenize(text)

        msg = (
            "Generating words (Emuru can take 1–3 min on CPU)…"
            if model == "wordstylist"
            else "Generating words"
        )
        update_job(job_id, progress=35, message=msg)
        print(f"Job {job_id}: {msg} model={model} words={len(words)}", flush=True)

        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        models_to_run = (
            list(MODEL_REGISTRY.keys()) if model == "compare" else [model]
        )
        output_paths: dict = {}
        compare_outputs: dict = {}
        run_meta: dict = {
            "input_text": text,
            "words": words,
            "model": model,
        }

        upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads")) / session_id
        style_paths = style.get("image_paths")
        if not style_paths and upload_dir.is_dir():
            style_paths = sorted(
                str(f)
                for f in upload_dir.iterdir()
                if f.is_file()
                and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
            )
        style_paths = style_paths or []
        print(f"Using {len(style_paths)} style images from {upload_dir}", flush=True)

        for model_name in models_to_run:
            if model_name == "diffusionpen":
                instance = get_diffusionpen_instance()
            else:
                instance = MODEL_REGISTRY[model_name]()
            instance.load()
            if model_name in ("diffusionpen", "wordstylist", "ganwriting"):
                word_images = instance.generate(words, style_paths)
            else:
                word_images = instance.generate(words, style)

            summary = _style_summary(model_name, instance, words)
            if model == "compare":
                run_meta.setdefault("models", {})[model_name] = summary
            else:
                run_meta.update(summary)

            # Persist Emuru's locked style crop for the output UI
            crop_img = getattr(instance, "_style_crop_image", None)
            if crop_img is not None:
                crop_name = (
                    f"{model_name}_style_used.png" if model == "compare" else "style_used.png"
                )
                crop_path = out_dir / crop_name
                crop_img.save(crop_path, format="PNG")
                crop_url = f"/api/file/{job_id}/{crop_name}"
                if model == "compare":
                    run_meta["models"][model_name]["style_crop_url"] = crop_url
                else:
                    run_meta["style_crop_url"] = crop_url

            page_images = compose_pages(word_images, pages)
            paths: list[str] = []
            for i, page_img in enumerate(page_images):
                filename = f"{model_name}_page_{i}.png" if model == "compare" else f"page_{i}.png"
                filepath = out_dir / filename
                page_img.save(filepath, format="PNG")
                paths.append(str(filepath))
            if model == "compare":
                compare_outputs[model_name] = paths
            else:
                output_paths = paths

        update_job(job_id, progress=75, message="Assembling pages")

        if model == "compare":
            update_job(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                output_paths=compare_outputs,
                is_compare=True,
                meta=run_meta,
            )
        else:
            update_job(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                output_paths=output_paths,
                is_compare=False,
                meta=run_meta,
            )
    except Exception as exc:
        update_job(
            job_id,
            status="error",
            progress=0,
            message=str(exc),
        )
