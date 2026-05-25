import os
import uuid
from pathlib import Path

import torch
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from models import MODEL_REGISTRY, VALID_MODELS
from models.diffusionpen import get_diffusionpen_instance
from services.generation import run_generation
from storage.job_store import get_job, has_style, set_job

router = APIRouter(prefix="/api", tags=["generate"])

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))
WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "weights"
EMA_CKPT = (
    WEIGHTS_DIR
    / "diffusionpen"
    / "diffusionpen_iam_model_path"
    / "models"
    / "ema_ckpt.pt"
)


def _weights_exist(model_name: str) -> bool:
    folder = WEIGHTS_DIR / model_name
    return folder.is_dir() and any(folder.iterdir())


def _model_status_entry(model_name: str) -> dict:
    if model_name == "diffusionpen":
        inst = get_diffusionpen_instance()
    else:
        inst = MODEL_REGISTRY[model_name]()
    return {
        "loaded": bool(getattr(inst, "is_loaded", False)),
        "weights_exist": _weights_exist(model_name),
    }


class GenerateRequest(BaseModel):
    session_id: str
    text: str = Field(..., min_length=1)
    model: str
    pages: int = Field(1, ge=1, le=10)


@router.get("/debug/checkpoint")
async def debug_checkpoint():
    """Inspect ema_ckpt.pt structure for wiring the full model."""
    if not EMA_CKPT.exists():
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {EMA_CKPT}")

    try:
        ckpt = torch.load(EMA_CKPT, map_location="cpu")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load checkpoint: {exc}")

    if not isinstance(ckpt, dict):
        return {"type": str(type(ckpt)), "keys": [], "sample_shapes": {}}

    keys = list(ckpt.keys())
    sample_shapes = {}
    for key in keys[:10]:
        val = ckpt[key]
        if hasattr(val, "shape"):
            sample_shapes[key] = list(val.shape)

    return {
        "path": str(EMA_CKPT),
        "num_keys": len(keys),
        "keys": keys[:50],
        "sample_shapes": sample_shapes,
    }


@router.get("/model-status")
async def model_status():
    return {
        "diffusionpen": _model_status_entry("diffusionpen"),
        "ganwriting": _model_status_entry("ganwriting"),
        "wordstylist": _model_status_entry("wordstylist"),
    }


@router.post("/generate")
async def generate_handwriting(body: GenerateRequest, background_tasks: BackgroundTasks):
    if not has_style(body.session_id):
        raise HTTPException(status_code=404, detail="Session not found. Upload samples first.")
    if body.model not in VALID_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"model must be one of: {', '.join(sorted(VALID_MODELS))}",
        )

    pages = min(body.pages, MAX_PAGES)
    job_id = str(uuid.uuid4())
    set_job(
        job_id,
        {
            "status": "pending",
            "model": body.model,
            "progress": 0,
            "message": "Queued",
            "session_id": body.session_id,
            "output_paths": None,
            "is_compare": body.model == "compare",
        },
    )

    background_tasks.add_task(
        run_generation,
        job_id,
        body.session_id,
        body.text,
        body.model,
        pages,
    )

    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
    }


def _file_urls(job_id: str, filenames: list[str]) -> list[str]:
    return [f"/api/file/{job_id}/{Path(f).name}" for f in filenames]


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"Job not ready. Status: {job.get('status')}")

    model = job.get("model")
    is_compare = job.get("is_compare", False)

    if is_compare:
        compare_paths = job.get("output_paths", {})
        return {
            "is_compare": True,
            "model": model,
            "compare": {
                k: _file_urls(job_id, v) for k, v in compare_paths.items()
            },
        }

    paths = job.get("output_paths", [])
    return {
        "is_compare": False,
        "model": model,
        "pages": _file_urls(job_id, paths),
    }


@router.get("/file/{job_id}/{filename}")
async def serve_file(job_id: str, filename: str):
    filepath = OUTPUT_DIR / job_id / filename
    if not filepath.exists() or ".." in filename:
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(filepath, media_type="image/png", filename=filename)
