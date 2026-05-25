# HandwritingAI — download_weights.py
"""Download DiffusionPen and Stable Diffusion v1.5 weights from Hugging Face."""

import sys
from pathlib import Path

from huggingface_hub import snapshot_download

BACKEND_DIR = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = BACKEND_DIR / "weights"
DIFFUSIONPEN_DIR = WEIGHTS_DIR / "diffusionpen"
SD_DIR = WEIGHTS_DIR / "stable-diffusion-v1-5"

SD_ALLOW_PATTERNS = [
    "*.json",
    "*.txt",
    "tokenizer/*",
    "text_encoder/*",
    "vae/*",
    "unet/*",
    "scheduler/*",
]


def _download_repo(repo_id: str, local_dir: Path, allow_patterns: list[str] | None = None) -> None:
    print(f"Downloading {repo_id} -> {local_dir}")
    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        allow_patterns=allow_patterns,
        local_dir_use_symlinks=False,
    )
    print(f"Finished: {repo_id}")


def main() -> int:
    try:
        print("DiffusionPen weights download (~size varies by repo)")
        _download_repo("konnik/DiffusionPen", DIFFUSIONPEN_DIR)

        print("Stable Diffusion v1.5 base components (filtered files only)")
        _download_repo(
            "runwayml/stable-diffusion-v1-5",
            SD_DIR,
            allow_patterns=SD_ALLOW_PATTERNS,
        )

        print("Downloading Canine tokenizer (google/canine-c)...")
        from transformers import CanineModel, CanineTokenizer

        canine_dir = WEIGHTS_DIR / "canine"
        CanineTokenizer.from_pretrained("google/canine-c", cache_dir=str(canine_dir))
        CanineModel.from_pretrained("google/canine-c", cache_dir=str(canine_dir))
        print("Canine ready.")

        print("Weights downloaded to backend/weights/. You can now run the app.")
        return 0
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        print(
            "Check your internet connection and Hugging Face access "
            "(login with `huggingface-cli login` if the repo is gated).",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
