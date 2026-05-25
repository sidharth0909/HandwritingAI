# HandwritingAI — diffusionpen.py
# Loads real DiffusionPen weights and runs inference on CPU

import os
import traceback
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .base import BaseHandwritingModel

WEIGHTS_DIR = Path(__file__).parent.parent / "weights"
DIFFUSIONPEN_DIR = WEIGHTS_DIR / "diffusionpen"
SD_DIR = WEIGHTS_DIR / "stable-diffusion-v1-5"

EMA_CKPT = DIFFUSIONPEN_DIR / "diffusionpen_iam_model_path" / "models" / "ema_ckpt.pt"
STYLE_CKPT = DIFFUSIONPEN_DIR / "style_models" / "iam_style_diffusionpen.pth"

_instance: "DiffusionPen | None" = None


def get_diffusionpen_instance() -> "DiffusionPen":
    global _instance
    if _instance is None:
        _instance = DiffusionPen()
    return _instance


class DiffusionPen(BaseHandwritingModel):
    name = "diffusionpen"

    def __init__(self) -> None:
        self.device = os.environ.get("DEVICE", "cpu")
        self.model = None
        self.is_loaded = False

    def load(self) -> None:
        print("=" * 50)
        print("Loading DiffusionPen...")

        if not EMA_CKPT.exists():
            raise FileNotFoundError(f"Not found: {EMA_CKPT}")

        try:
            from diffusionpen_core.model import DiffusionPenInference

            self.model = DiffusionPenInference(
                sd_path=str(SD_DIR),
                device=self.device,
            )
            self.model.load_components(
                ema_ckpt_path=str(EMA_CKPT),
                style_ckpt_path=str(STYLE_CKPT),
            )
            self.is_loaded = True
            print("DiffusionPen ready.")
            print("=" * 50)

        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()
            print("Falling back to enhanced PIL mock.")
            self.model = None
            self.is_loaded = True

    def generate(self, words: list[str], style_image_paths: list) -> list[Image.Image]:
        """
        words: list of word strings
        style_image_paths: list of paths to uploaded handwriting sample images
        """
        if not self.is_loaded:
            self.load()

        if self.model is None or not hasattr(self.model, "generate_word"):
            return self._mock_generate(words, {})

        results: list[Image.Image] = []
        for word in words:
            try:
                img = self.model.generate_word(
                    word=word,
                    style_image_paths=style_image_paths,
                    num_steps=20,
                )
                results.append(img)
                print(f"  Generated: '{word}'")
            except Exception as e:
                print(f"  Failed '{word}': {e}. Using mock.")
                results.append(self._mock_single_word(word))

        return results

    def _mock_generate(self, words: list[str], style_embedding: dict) -> list[Image.Image]:
        _ = style_embedding
        return [self._mock_single_word(w) for w in words]

    def _mock_single_word(self, word: str) -> Image.Image:
        width = max(len(word) * 28 + 20, 60)
        height = 64
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except OSError:
            font = ImageFont.load_default()

        baseline_y = int(height * 0.8)
        draw.line([(10, baseline_y), (width - 10, baseline_y)], fill=(220, 220, 220), width=1)
        draw.text((10, 15), word, fill=(30, 30, 30), font=font)
        return img
