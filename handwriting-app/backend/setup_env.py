# HandwritingAI — setup_env.py
"""Install backend dependencies into the active Python environment."""

import importlib.util
import subprocess
import sys


def _torch_installed() -> bool:
    return importlib.util.find_spec("torch") is not None


def _pip_install(*args: str) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args])


def main() -> int:
    try:
        if not _torch_installed():
            print("Installing CPU PyTorch...")
            _pip_install(
                "torch",
                "torchvision",
                "--index-url",
                "https://download.pytorch.org/whl/cpu",
            )
        else:
            print("torch already installed — skipping CPU torch install.")

        print("Installing remaining dependencies...")
        _pip_install(
            "diffusers",
            "transformers",
            "accelerate",
            "huggingface_hub",
            "omegaconf",
            "einops",
            "timm",
            "pdfplumber",
            "Pillow",
            "reportlab",
            "python-docx",
            "python-dotenv",
            "fastapi",
            "uvicorn[standard]",
            "python-multipart",
            "aiofiles",
        )

        print("Environment ready. Run: uvicorn main:app --reload --port 8000")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"Install failed (exit {exc.returncode}):", file=sys.stderr)
        if exc.cmd:
            print("Command:", " ".join(exc.cmd), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
