"""Optional: deep image embeddings for near-duplicate detection.

Off by default. Requires `sentence-transformers` + `torch`.
Used when crops/rotations/re-photographs of the same receipt would
defeat perceptual hashes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PIL import Image as _Image


class EmbeddingEncoder:
    name: str = "clip-ViT-B-32"

    def __init__(self, model_name: str = "clip-ViT-B-32") -> None:
        from sentence_transformers import SentenceTransformer  # heavy import
        self._model = SentenceTransformer(model_name)
        self.name = model_name

    @classmethod
    def is_available(cls) -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except Exception:
            return False

    def encode(self, image: "_Image.Image") -> np.ndarray:
        vec = self._model.encode([image], convert_to_numpy=True, normalize_embeddings=True)[0]
        return vec.astype(np.float32)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        # both expected normalized; cosine == dot
        return float(np.dot(a, b))
