from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from ..models import OCRResult


class NoOCREngineAvailable(RuntimeError):
    """Raised when no OCR engine is installed / configured."""


class OCREngine(ABC):
    name: str = "abstract"

    @abstractmethod
    def run(self, image: Image.Image, lang: str = "heb+eng") -> OCRResult: ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool: ...
