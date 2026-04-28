from __future__ import annotations

import numpy as np
from PIL import Image

from ..models import OCRLine, OCRResult
from .base import OCREngine


class EasyOCREngine(OCREngine):
    name = "easyocr"

    def __init__(self) -> None:
        import easyocr
        # easyocr language codes: 'he' (Hebrew), 'en' (English)
        self._reader = easyocr.Reader(["he", "en"], gpu=False, verbose=False)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except Exception:
            return False

    def run(self, image: Image.Image, lang: str = "heb+eng") -> OCRResult:
        arr = np.array(image.convert("RGB"))
        results = self._reader.readtext(arr, detail=1, paragraph=False)

        lines: list[OCRLine] = []
        for bbox, text, conf in results:
            text = (text or "").strip()
            if not text:
                continue
            xs = [int(p[0]) for p in bbox]
            ys = [int(p[1]) for p in bbox]
            box = (min(xs), min(ys), max(xs), max(ys))
            lines.append(OCRLine(text=text, bbox=box, confidence=float(conf)))

        full_text = "\n".join(l.text for l in lines)
        return OCRResult(text=full_text, lines=lines, engine=self.name, lang=lang)
