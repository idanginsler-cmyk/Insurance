from __future__ import annotations

from .base import NoOCREngineAvailable, OCREngine


def get_engine(preference: str = "auto") -> OCREngine:
    """Return an OCR engine instance.

    preference: "tesseract" | "easyocr" | "auto"
    Falls back to whichever is installed; raises if none.
    """
    from .tesseract_engine import TesseractEngine
    from .easyocr_engine import EasyOCREngine

    candidates: list[type[OCREngine]]
    if preference == "tesseract":
        candidates = [TesseractEngine]
    elif preference == "easyocr":
        candidates = [EasyOCREngine]
    else:
        candidates = [TesseractEngine, EasyOCREngine]

    for cls in candidates:
        if cls.is_available():
            return cls()

    raise NoOCREngineAvailable(
        "No OCR engine available. Install one of:\n"
        "  pip install pytesseract  (and `apt install tesseract-ocr tesseract-ocr-heb`)\n"
        "  pip install easyocr"
    )
