# HandwritingAI — style_encoder.py
# MobileNet-based style feature extractor matching original DiffusionPen

import torch
import torch.nn as nn
import timm
import torchvision.transforms as transforms
from PIL import Image


class StyleFeatureExtractor(nn.Module):
    """
    MobileNetV2-based style feature extractor.
    Matches the feature_extractor used in original DiffusionPen sampling().
    Uses timm mobilenetv2_100 (checkpoint keys: model.conv_stem, ...).
    Input:  batch of word images (N, 3, 64, 256), normalized [-1, 1]
    Output: (N, 1280) style feature vectors
    """

    def __init__(self):
        super().__init__()
        self.model = timm.create_model(
            "mobilenetv2_100",
            pretrained=False,
            num_classes=0,
            global_pool="max",
        )

    def forward(self, x):
        return self.model(x)

    def load_weights(self, pth_path: str, device: str = "cpu"):
        """
        Load weights from iam_style_diffusionpen.pth.
        Try multiple state dict wrapper formats.
        Print missing/unexpected counts.
        """
        state = torch.load(pth_path, map_location=device)

        for key in ("model", "state_dict", "encoder", "net", "feature_extractor"):
            if isinstance(state, dict) and key in state:
                state = state[key]
                print(f"  Unwrapped state dict from key: '{key}'")
                break

        clean = {}
        for k, v in state.items():
            new_k = k[len("module.") :] if k.startswith("module.") else k
            clean[new_k] = v

        model_dict = self.model.state_dict()
        filtered = {
            k: v for k, v in clean.items() if k in model_dict and model_dict[k].shape == v.shape
        }
        model_dict.update(filtered)
        missing, unexpected = self.model.load_state_dict(model_dict, strict=False)
        print(
            f"  Style extractor loaded. Missing: {len(missing)}, Unexpected: {len(unexpected)}"
        )
        if missing[:3]:
            print(f"  Sample missing: {missing[:3]}")
        self.to(device).eval()


def preprocess_style_images(image_paths: list, device: str = "cpu") -> torch.Tensor:
    """
    Load and preprocess style sample images for the feature extractor.
    Exactly matches original DiffusionPen preprocessing:
    - Resize to 64 x 256 (H x W)
    - Convert to RGB
    - Normalize to [-1, 1]
    Returns: (N, 3, 64, 256) tensor
    """
    transform = transforms.Compose(
        [
            transforms.Resize((64, 256)),
            transforms.ToTensor(),
            transforms.Normalize([0.5] * 3, [0.5] * 3),
        ]
    )

    imgs = []
    for p in image_paths:
        img = Image.open(p).convert("RGB")
        imgs.append(transform(img))

    return torch.stack(imgs).to(device)
