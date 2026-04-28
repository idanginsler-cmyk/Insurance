from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "store" / "fraud_detection.db"


@dataclass
class Config:
    db_path: Path = DEFAULT_DB_PATH

    # OCR engine preference: "tesseract", "easyocr", or "auto"
    ocr_engine: str = "auto"
    ocr_lang: str = "heb+eng"

    # Perceptual hash thresholds (Hamming distance on 64-bit hashes).
    # Compared against max(phash_dist, dhash_dist) — i.e. both hashes
    # must agree.
    phash_exact_threshold: int = 4      # <= this => almost certainly the same image
    phash_near_threshold: int = 8       # <= this => visually similar

    # Text fingerprint thresholds (Jaccard similarity on normalized tokens)
    text_fingerprint_threshold: float = 0.85

    # Embedding similarity threshold (cosine)
    embedding_threshold: float = 0.95
    use_embeddings: bool = False        # off by default; opt-in (heavy deps)

    # PDF producer reputation lists (lower-cased substrings)
    producer_blacklist: tuple = (
        "smallpdf", "ilovepdf", "pdfescape", "sejda", "pdfsam",
        "pixelmator", "photoshop", "gimp", "paint.net", "ms paint",
    )
    producer_whitelist: tuple = (
        "adobe acrobat", "microsoft print to pdf", "abbyy finereader",
        "kofax", "nuance", "konica minolta", "xerox", "canon",
        "epson scan", "hp scan", "scanbot", "camscanner",
    )

    @classmethod
    def from_env(cls) -> "Config":
        cfg = cls()
        if path := os.environ.get("FD_DB_PATH"):
            cfg.db_path = Path(path)
        if eng := os.environ.get("FD_OCR_ENGINE"):
            cfg.ocr_engine = eng
        if lang := os.environ.get("FD_OCR_LANG"):
            cfg.ocr_lang = lang
        if os.environ.get("FD_USE_EMBEDDINGS", "").lower() in ("1", "true", "yes"):
            cfg.use_embeddings = True
        cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        return cfg
