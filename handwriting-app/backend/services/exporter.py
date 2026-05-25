import io
from pathlib import Path

from PIL import Image, PngImagePlugin
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _png_info() -> PngImagePlugin.PngInfo:
    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Sidharth")
    info.add_text("Software", "HandwritingAI")
    info.add_text("Repository", "github.com/sidharth0909")
    return info


def _save_png(img: Image.Image, output) -> None:
    img.save(output, "PNG", pnginfo=_png_info())


def images_to_pdf(image_paths: list[str]) -> bytes:
    paths = [Path(p) for p in image_paths if Path(p).exists()]
    if not paths:
        blank = Image.new("RGB", (2480, 3508), color=(255, 255, 255))
        paths = [_save_temp(blank)]

    buffer = io.BytesIO()
    first = Image.open(paths[0]).convert("RGB")
    w, h = first.size
    pdf = canvas.Canvas(buffer, pagesize=(w, h))

    for idx, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        if idx > 0:
            pdf.showPage()
            pdf.setPageSize((img.size[0], img.size[1]))
        buf = io.BytesIO()
        _save_png(img, buf)
        buf.seek(0)
        pdf.drawImage(ImageReader(buf), 0, 0, width=img.size[0], height=img.size[1])

    pdf.save()
    buffer.seek(0)
    return buffer.read()


def _save_temp(img: Image.Image) -> Path:
    import tempfile

    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    _save_png(img, f.name)
    return Path(f.name)
