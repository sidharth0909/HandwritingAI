from .diffusionpen import DiffusionPen
from .ganwriting import GANWriting
from .wordstylist import WordStylist

MODEL_REGISTRY = {
    "diffusionpen": DiffusionPen,
    "ganwriting": GANWriting,
    "wordstylist": WordStylist,
}

VALID_MODELS = set(MODEL_REGISTRY.keys()) | {"compare"}
