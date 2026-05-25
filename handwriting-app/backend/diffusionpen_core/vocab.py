# HandwritingAI — vocab.py
"""IAM character vocabulary used by DiffusionPen."""

import torch

ALPHABET = (
    ' !"#&\'()*+,-./0123456789:;?'
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)

LETTER2INDEX = {c: i for i, c in enumerate(ALPHABET)}
PAD_TOKEN = len(ALPHABET)


def word_to_tensor(word: str) -> torch.Tensor:
    """Convert a word to character index tensor (unknown chars -> space)."""
    indices = [LETTER2INDEX.get(c, LETTER2INDEX[" "]) for c in word]
    return torch.tensor(indices, dtype=torch.long)
