from __future__ import annotations

from PIL import Image

from ..models import OCRLine, OCRResult
from .base import OCREngine


class TesseractEngine(OCREngine):
    name = "tesseract"

    def __init__(self) -> None:
        import pytesseract  # noqa: F401  (raises ImportError if missing)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def run(self, image: Image.Image, lang: str = "heb+eng") -> OCRResult:
        import pytesseract
        from pytesseract import Output

        data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
        lines: list[OCRLine] = []
        for i, txt in enumerate(data["text"]):
            txt = (txt or "").strip()
            if not txt:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            try:
                conf = float(data["conf"][i]) / 100.0 if data["conf"][i] != "-1" else None
            except (TypeError, ValueError):
                conf = None
            lines.append(OCRLine(text=txt, bbox=(x, y, x + w, y + h), confidence=conf))

        full_text = "\n".join(l.text for l in lines)
        return OCRResult(text=full_text, lines=lines, engine=self.name, lang=lang)
