from abc import ABC, abstractmethod

from PIL import Image


class BaseHandwritingModel(ABC):
    name: str = "base"

    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate(self, words: list[str], style_embedding: dict) -> list[Image.Image]:
        raise NotImplementedError
