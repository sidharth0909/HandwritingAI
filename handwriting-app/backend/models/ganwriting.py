from PIL import Image

from .base import BaseHandwritingModel
from .mock_draw import draw_mock_word


class GANWriting(BaseHandwritingModel):
    name = "ganwriting"

    def __init__(self) -> None:
        self.is_loaded = False

    def load(self) -> None:
        # TODO: Replace with real model inference — load GAN generator
        pass

    def generate(self, words: list[str], style_embedding: dict) -> list[Image.Image]:
        _ = style_embedding
        # TODO: Replace with real model inference
        return [draw_mock_word(w) for w in words]
