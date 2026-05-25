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

        update_job(job_id, progress=35, message="Generating words")

        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        models_to_run = (
            list(MODEL_REGISTRY.keys()) if model == "compare" else [model]
        )
        output_paths: dict = {}
        compare_outputs: dict = {}

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
        print(f"Using {len(style_paths)} style images from {upload_dir}")

        for model_name in models_to_run:
            if model_name == "diffusionpen":
                instance = get_diffusionpen_instance()
            else:
                instance = MODEL_REGISTRY[model_name]()
            instance.load()
            if model_name == "diffusionpen":
                word_images = instance.generate(words, style_paths)
            else:
                word_images = instance.generate(words, style)
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
            )
        else:
            update_job(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                output_paths=output_paths,
                is_compare=False,
            )
    except Exception as exc:
        update_job(
            job_id,
            status="error",
            progress=0,
            message=str(exc),
        )
