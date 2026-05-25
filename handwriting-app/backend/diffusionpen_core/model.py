# HandwritingAI — model.py
# DiffusionPen inference model — exact pipeline from original repo

from __future__ import annotations

import traceback
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from diffusers import AutoencoderKL, DDIMScheduler
from PIL import Image
from transformers import CanineModel, CanineTokenizer

from .style_encoder import StyleFeatureExtractor, preprocess_style_images
from .unet import UNetModel

IMG_HEIGHT = 64
IMG_WIDTH = 256
STYLE_CLASSES = 339
VOCAB_SIZE = 95
CANINE_MODEL = "google/canine-c"
LATENT_SHAPE = (1, 4, 8, 32)
VAE_SCALE = 0.18215


def crop_to_ink(img: Image.Image, padding: int = 8) -> Image.Image:
    gray = img.convert("L")
    pixels = gray.load()
    w, h = img.size
    min_x, max_x = w, 0
    min_y, max_y = h, 0
    for py in range(h):
        for px in range(w):
            if pixels[px, py] < 240:
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                min_y = min(min_y, py)
                max_y = max(max_y, py)
    if max_x < min_x:
        return Image.new("RGB", (20, 64), color=(255, 255, 255))
    left = max(0, min_x - padding)
    right = min(w, max_x + padding)
    top = max(0, min_y - padding)
    bottom = min(h, max_y + padding)
    return img.crop((left, top, right, bottom))


def scale_to_char_width(
    img: Image.Image, word: str, px_per_char: int = 40, target_h: int = 90
) -> Image.Image:
    """Scale word image to consistent height and char-proportional width."""
    target_w = max(px_per_char, len(word) * px_per_char)
    if img.size[0] == 0 or img.size[1] == 0:
        return img
    return img.resize((target_w, target_h), Image.LANCZOS)


class DiffusionPenArgs(SimpleNamespace):
    def __init__(self, device: str = "cpu") -> None:
        super().__init__(
            img_size=(IMG_HEIGHT, IMG_WIDTH),
            channels=4,
            emb_dim=320,
            num_heads=4,
            num_res_blocks=1,
            latent=True,
            img_feat=True,
            interpolation=False,
            color=True,
            model_name="diffusionpen",
            mix_rate=None,
            device=device,
        )


class DiffusionPenInference:
    """
    Exact DiffusionPen inference pipeline matching original sampling().

    Components:
    - ema_ckpt.pt: full model (UNet + Canine text encoder), loaded as one state dict
    - VAE: from stable-diffusion-v1-5
    - DDIM scheduler: from stable-diffusion-v1-5
    - Canine tokenizer: google/canine-c
    - Style: MobileNet feature extractor (weights from style_models/)
    """

    def __init__(self, sd_path: str, device: str = "cpu"):
        self.device = device
        self.sd_path = Path(sd_path)
        self.weights_root = self.sd_path.parent
        self.model = None
        self.vae = None
        self.scheduler = None
        self.tokenizer = None
        self.style_extractor = None
        self.args = DiffusionPenArgs(device)

    def load_components(self, ema_ckpt_path: str, style_ckpt_path: str):
        """Load all inference components."""
        canine_cache = str(self.weights_root / "canine")

        print("  Loading Canine tokenizer...")
        try:
            self.tokenizer = CanineTokenizer.from_pretrained(
                CANINE_MODEL, cache_dir=canine_cache
            )
        except Exception:
            self.tokenizer = CanineTokenizer.from_pretrained(CANINE_MODEL)

        print("  Loading VAE...")
        self.vae = AutoencoderKL.from_pretrained(str(self.sd_path / "vae"))
        self.vae.to(self.device).eval()

        print("  Loading DDIM scheduler...")
        self.scheduler = DDIMScheduler.from_pretrained(str(self.sd_path / "scheduler"))

        print("  Loading full model from checkpoint...")
        self._load_full_model(ema_ckpt_path)

        print("  Loading style feature extractor (MobileNet)...")
        self._load_style_extractor(style_ckpt_path)

    def _load_full_model(self, ckpt_path: str):
        """Load ema_ckpt.pt into custom UNetModel (Canine + style_lin inside unet.py)."""
        print(f"  torch.load: {ckpt_path}")
        state = torch.load(ckpt_path, map_location=self.device)
        if not isinstance(state, dict):
            raise TypeError(f"Expected state dict, got {type(state)}")

        clean_state = {}
        for k, v in state.items():
            new_k = k[len("module.") :] if k.startswith("module.") else k
            clean_state[new_k] = v

        remapped = {}
        for key, value in clean_state.items():
            if key.startswith("text_encoder.module."):
                remapped["text_encoder." + key[len("text_encoder.module.") :]] = value
            else:
                remapped[key] = value

        print(f"  Checkpoint keys (stripped): {len(remapped)}")
        print(f"  Sample keys: {list(remapped.keys())[:5]}")

        try:
            print("  Building UNetModel from diffusionpen_core.unet...")
            text_encoder = CanineModel.from_pretrained(
                CANINE_MODEL, cache_dir=str(self.weights_root / "canine")
            )

            self.model = UNetModel(
                image_size=self.args.img_size,
                in_channels=self.args.channels,
                model_channels=self.args.emb_dim,
                out_channels=self.args.channels,
                num_res_blocks=self.args.num_res_blocks,
                attention_resolutions=(1, 1),
                channel_mult=(1, 1),
                num_heads=self.args.num_heads,
                num_classes=STYLE_CLASSES,
                context_dim=self.args.emb_dim,
                vocab_size=VOCAB_SIZE,
                text_encoder=text_encoder,
                args=self.args,
            ).to(self.device)

            missing, unexpected = self.model.load_state_dict(remapped, strict=False)
            print(f"  UNet loaded. Missing: {len(missing)}, Unexpected: {len(unexpected)}")
            if missing:
                print(f"  First 5 missing: {missing[:5]}")
            if unexpected:
                print(f"  First 5 unexpected: {unexpected[:5]}")
            self.model.eval()

        except Exception as e:
            print(f"  Could not load UNetModel: {e}")
            traceback.print_exc()
            self.model = None

    def _load_style_extractor(self, style_ckpt_path: str):
        self.style_extractor = StyleFeatureExtractor()
        self.style_extractor.load_weights(style_ckpt_path, device=self.device)

    @torch.no_grad()
    def generate_word(
        self,
        word: str,
        style_image_paths: list,
        num_steps: int = 20,
    ) -> Image.Image:
        """
        Generate one handwritten word image.
        Matches original DiffusionPen sampling() exactly.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        if self.style_extractor is None:
            raise RuntimeError("Style extractor not loaded")

        text_input = self.tokenizer(
            word,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            max_length=40,
        )
        text_features = {k: v.to(self.device) for k, v in text_input.items()}

        paths = list(style_image_paths[:5])
        while len(paths) < 5:
            paths = paths + [paths[-1]]

        style_imgs = preprocess_style_images(paths, device=self.device)
        style_features = self.style_extractor(style_imgs)

        labels = torch.zeros(1, dtype=torch.long, device=self.device)
        x = torch.randn(*LATENT_SHAPE, device=self.device)

        self.scheduler.set_timesteps(num_steps, device=self.device)

        for t in self.scheduler.timesteps:
            t_batch = torch.full((1,), t.item(), device=self.device, dtype=torch.long)
            noise_pred = self.model(
                x,
                t_batch,
                context=text_features,
                y=labels,
                style_extractor=style_features,
            )
            if isinstance(noise_pred, tuple):
                noise_pred = noise_pred[0]
            x = self.scheduler.step(noise_pred, t, x).prev_sample

        decoded = self.vae.decode(x / VAE_SCALE).sample
        img = decoded.squeeze(0).cpu()
        img = (img.clamp(-1, 1) + 1) / 2
        img = (img.permute(1, 2, 0).numpy() * 255).astype("uint8")
        pil = Image.fromarray(img).convert("RGB")
        pil = crop_to_ink(pil)
        return scale_to_char_width(pil, word)


# Backward compatibility
DiffusionPenModel = DiffusionPenInference
