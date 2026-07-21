from .diffusionpen import DiffusionPen
from .wordstylist import WordStylist

MODEL_REGISTRY = {
    "diffusionpen": DiffusionPen,
    "wordstylist": WordStylist,
}

VALID_MODELS = set(MODEL_REGISTRY.keys()) | {"compare"}
