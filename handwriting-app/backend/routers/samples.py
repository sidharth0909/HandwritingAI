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
):
    if len(files) < 5:
        raise HTTPException(status_code=400, detail="Upload at least 5 handwriting samples.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 samples allowed.")

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
