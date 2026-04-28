from __future__ import annotations

import imagehash
from PIL import Image

from ..models import HashSet


def compute_hashes(image: Image.Image) -> HashSet:
    """Compute four perceptual hashes (each 64-bit) for robust duplicate detection.

    - phash: DCT-based, robust to brightness/contrast/JPEG compression.
    - dhash: gradient-based, robust to scaling.
    - ahash: average-based, fast but weakest.
    - whash: wavelet-based, robust to localized edits.
    """
    return HashSet(
        phash=str(imagehash.phash(image)),
        dhash=str(imagehash.dhash(image)),
        ahash=str(imagehash.average_hash(image)),
        whash=str(imagehash.whash(image)),
    )


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Hamming distance between two hex-encoded perceptual hashes."""
    return imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)
