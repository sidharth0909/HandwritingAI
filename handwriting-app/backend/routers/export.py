import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.exporter import images_to_pdf
from storage.job_store import get_job

router = APIRouter(prefix="/api", tags=["export"])


class ExportPdfRequest(BaseModel):
    job_id: str
    model: str | None = None


@router.post("/export/pdf")
async def export_pdf(body: ExportPdfRequest):
    job = get_job(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job not complete.")

    is_compare = job.get("is_compare", False)
    model_key = body.model or (None if is_compare else job.get("model"))

    if is_compare:
        if not model_key:
            raise HTTPException(status_code=400, detail="Provide model for compare export.")
        paths = job.get("output_paths", {}).get(model_key)
    else:
        paths = job.get("output_paths")

    if not paths:
        raise HTTPException(status_code=404, detail="No output files for this job.")

    pdf_bytes = images_to_pdf(paths)
    filename = f"{model_key or job.get('model', 'output')}_handwriting.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
