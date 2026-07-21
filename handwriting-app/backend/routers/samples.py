import io
import os
import uuid
from pathlib import Path

from docx import Document
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.style_extractor import extract_style
from storage.job_store import set_style

router = APIRouter(prefix="/api", tags=["samples"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


@router.post("/samples")
async def upload_samples(
    files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
    model: str | None = Form(None),
):
    # Emuru (wordstylist) is zero-shot — 1 style image is enough.
    # DiffusionPen needs several samples for the style encoder.
    is_emuru = (model or "").lower() in ("wordstylist", "emuru")
    min_samples = 1 if is_emuru else 5
    max_samples = 5 if is_emuru else 10

    if len(files) < min_samples:
        raise HTTPException(
            status_code=400,
            detail=f"Upload at least {min_samples} handwriting sample{'s' if min_samples != 1 else ''}.",
        )
    if len(files) > max_samples:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_samples} samples allowed.",
        )

    sid = session_id or str(uuid.uuid4())
    session_dir = UPLOAD_DIR / sid
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for upload in files:
        filename = Path(upload.filename or "sample.png").name
        dest = session_dir / filename
        content = await upload.read()
        dest.write_bytes(content)
        saved_paths.append(str(dest))

    style = extract_style(saved_paths)
    set_style(sid, style)

    return {
        "session_id": sid,
        "file_count": len(files),
        "style_id": style["style_id"],
    }


@router.post("/parse-doc")
async def parse_document(file: UploadFile = File(...)):
    """Extract plain text from PDF or DOCX uploads."""
    name = (file.filename or "").lower()
    content = await file.read()

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return {"text": text or ""}

    if name.endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF parsing requires pdfplumber. Install pdfplumber or use DOCX.",
            )
        parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return {"text": "\n\n".join(parts)}

    if name.endswith(".txt"):
        return {"text": content.decode("utf-8", errors="replace")}

    raise HTTPException(status_code=400, detail="Supported formats: .pdf, .docx, .txt")
