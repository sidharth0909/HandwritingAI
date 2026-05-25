import random

from PIL import Image, ImageDraw, ImageFont


def _serif_font(size: int = 28) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("times.ttf", "Times New Roman.ttf", "Georgia.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_mock_word(word: str, slant: float = 0.12) -> Image.Image:
    """Render a single mock word image with slight slant and per-letter jitter."""
    font = _serif_font(28)
    pad = 16
    probe = Image.new("RGB", (1, 1))
    draw_probe = ImageDraw.Draw(probe)
    bbox = draw_probe.textbbox((0, 0), word, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    width = int(text_w * (1 + slant)) + pad * 2
    height = 60
    img = Image.new("RGB", (max(width, 40), height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    x = pad
    baseline = height // 2 + text_h // 4
    for ch in word:
        ch_bbox = draw.textbbox((0, 0), ch, font=font)
        ch_w = ch_bbox[2] - ch_bbox[0]
        y_off = random.randint(-3, 3)
        draw.text((x, baseline + y_off - text_h // 2), ch, fill=(26, 26, 30), font=font)
        x += ch_w + random.randint(0, 2)

    return img
