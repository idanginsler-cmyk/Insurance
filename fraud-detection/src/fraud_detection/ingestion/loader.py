from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image


SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
SUPPORTED_PDF = {".pdf"}


@dataclass
class Document:
    file_path: Path
    file_bytes: bytes
    file_type: str          # "image" | "pdf"
    sha256: str
    image: Image.Image      # rendered/loaded first page
    page_count: int = 1
    pdf_raw: Optional[bytes] = None  # only set for PDFs (used by metadata extractor)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def _render_pdf_first_page(data: bytes) -> tuple[Image.Image, int]:
    """Render PDF first page. Tries pdf2image (poppler), then falls back
    to extracting embedded images via pypdf."""
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(data, dpi=200, first_page=1, last_page=1)
        if pages:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(data))
                page_count = len(reader.pages)
            except Exception:
                page_count = 1
            return pages[0].convert("RGB"), page_count
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: try to extract first embedded image from page 1
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        if page_count > 0:
            first = reader.pages[0]
            for image_file in getattr(first, "images", []):
                return _load_image(image_file.data), page_count
    except Exception:
        pass

    raise RuntimeError(
        "Cannot render PDF: install `pdf2image` (and the system `poppler` binary), "
        "or provide an image file directly."
    )


def load_document(path: str | Path) -> Document:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    data = p.read_bytes()
    sha = _sha256(data)
    suffix = p.suffix.lower()

    if suffix in SUPPORTED_IMAGE:
        return Document(
            file_path=p,
            file_bytes=data,
            file_type="image",
            sha256=sha,
            image=_load_image(data),
            page_count=1,
        )

    if suffix in SUPPORTED_PDF:
        image, page_count = _render_pdf_first_page(data)
        return Document(
            file_path=p,
            file_bytes=data,
            file_type="pdf",
            sha256=sha,
            image=image,
            page_count=page_count,
            pdf_raw=data,
        )

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        f"Supported: {sorted(SUPPORTED_IMAGE | SUPPORTED_PDF)}"
    )
