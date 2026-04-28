from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, ExifTags

from ..config import Config
from ..models import MetadataReport

if TYPE_CHECKING:
    from ..ingestion.loader import Document


def _decode(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return str(value)


def _classify_producer(text: str | None, cfg: Config) -> list[str]:
    """Return suspicions based on producer/creator/software string."""
    if not text:
        return ["missing_producer_metadata"]
    low = text.lower()
    suspicions = []
    for needle in cfg.producer_blacklist:
        if needle in low:
            suspicions.append(f"suspect_producer:{needle}")
    on_whitelist = any(w in low for w in cfg.producer_whitelist)
    if not on_whitelist and not suspicions:
        suspicions.append("unknown_producer")
    return suspicions


def _extract_pdf_metadata(data: bytes, cfg: Config) -> MetadataReport:
    from pypdf import PdfReader

    suspicions: list[str] = []
    raw: dict = {}

    # Count %%EOF markers — each one >1 indicates an incremental update,
    # which is a strong signal that the PDF was edited after creation.
    eof_count = data.count(b"%%EOF")
    incremental = max(0, eof_count - 1)
    if incremental > 0:
        suspicions.append(f"pdf_incremental_updates:{incremental}")

    producer = creator = creation_date = modified_date = None
    try:
        reader = PdfReader(io.BytesIO(data))
        info = reader.metadata or {}
        producer = _decode(info.get("/Producer"))
        creator = _decode(info.get("/Creator"))
        creation_date = _decode(info.get("/CreationDate"))
        modified_date = _decode(info.get("/ModDate"))
        raw = {k: _decode(v) for k, v in info.items()}
    except Exception as e:
        suspicions.append(f"pdf_metadata_error:{type(e).__name__}")

    suspicions.extend(_classify_producer(producer or creator, cfg))

    if creation_date and modified_date and creation_date != modified_date:
        suspicions.append("pdf_modified_after_creation")

    return MetadataReport(
        producer=producer,
        creator=creator,
        software=None,
        creation_date=creation_date,
        modified_date=modified_date,
        eof_count=eof_count,
        incremental_updates=incremental,
        has_exif=False,
        suspicions=suspicions,
        raw=raw,
    )


def _extract_image_metadata(image: Image.Image, cfg: Config) -> MetadataReport:
    suspicions: list[str] = []
    raw: dict = {}
    software = None
    creation = modified = None

    exif = None
    try:
        exif = image.getexif()
    except Exception:
        pass

    has_exif = bool(exif)

    if exif:
        for tag_id, value in exif.items():
            tag = ExifTags.TAGS.get(tag_id, str(tag_id))
            raw[tag] = _decode(value)
            if tag == "Software":
                software = _decode(value)
            elif tag == "DateTimeOriginal":
                creation = _decode(value)
            elif tag == "DateTime":
                modified = _decode(value)
    else:
        # No EXIF at all is itself a (weak) signal — most camera photos
        # carry EXIF; absence often means re-saved by an editor. The
        # "missing producer" check only makes sense once we *have* EXIF;
        # otherwise we'd double-count the absence as two separate flags.
        suspicions.append("no_exif")

    if has_exif:
        suspicions.extend(_classify_producer(software, cfg))

    return MetadataReport(
        producer=None,
        creator=None,
        software=software,
        creation_date=creation,
        modified_date=modified,
        eof_count=None,
        incremental_updates=None,
        has_exif=has_exif,
        suspicions=suspicions,
        raw=raw,
    )


def extract_metadata(document: "Document", cfg: Config | None = None) -> MetadataReport:
    cfg = cfg or Config()
    if document.file_type == "pdf" and document.pdf_raw:
        return _extract_pdf_metadata(document.pdf_raw, cfg)
    return _extract_image_metadata(document.image, cfg)
