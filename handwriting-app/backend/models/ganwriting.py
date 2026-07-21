from PIL import Image

from .base import BaseHandwritingModel
from .mock_draw import draw_mock_word


class GANWriting(BaseHandwritingModel):
    name = "ganwriting"

    def __init__(self):
        self.is_loaded = False

    def load(self):
        pass

    def generate(self, words, style_image_paths):
        return [draw_mock_word(w) for w in words]
