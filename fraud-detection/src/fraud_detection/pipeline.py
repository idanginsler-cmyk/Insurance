"""End-to-end pipeline orchestration.

Loads a document → runs forensics + OCR + extraction → optionally compares
against the store → returns a FraudScore. This is the single entry point
the CLI and API both call."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config
from .duplicates.matcher import DuplicateMatcher
from .duplicates.store import DocumentStore
from .extraction.fields import extract_receipt_fields
from .forensics.metadata import extract_metadata
from .forensics.perceptual_hash import compute_hashes
from .ingestion.loader import load_document
from .models import DocumentRecord, FraudScore, OCRResult, ReceiptFields
from .scoring.ensemble import score_document


def _empty_ocr() -> OCRResult:
    return OCRResult(text="", lines=[], engine="none", lang="")


def _run_ocr(image, cfg: Config) -> OCRResult:
    """Best-effort OCR; returns empty result if no engine is installed
    so the rest of the pipeline (hashes, metadata) still runs."""
    try:
        from .ocr.factory import get_engine
        engine = get_engine(cfg.ocr_engine)
        return engine.run(image, lang=cfg.ocr_lang)
    except Exception as e:
        # Hot path must not crash on missing OCR — log via a stub field.
        return OCRResult(text="", lines=[], engine=f"unavailable:{type(e).__name__}", lang="")


def analyze(
    file_path: str | Path,
    store: DocumentStore,
    *,
    claim_id: str | None = None,
    document_id: str | None = None,
    persist: bool = False,
    cfg: Config | None = None,
) -> tuple[DocumentRecord, FraudScore, OCRResult]:
    """Analyze a single document.

    Returns (record, score, ocr).
    If persist=True, the record is added to the store *after* duplicate
    detection (so it doesn't match itself).
    """
    cfg = cfg or Config.from_env()

    document = load_document(file_path)
    hashes = compute_hashes(document.image)
    metadata = extract_metadata(document, cfg=cfg)
    ocr = _run_ocr(document.image, cfg)
    fields: ReceiptFields = extract_receipt_fields(ocr)

    record = DocumentRecord(
        document_id=document_id or str(uuid.uuid4()),
        claim_id=claim_id,
        file_path=str(document.file_path),
        file_type=document.file_type,
        sha256=document.sha256,
        hashes=hashes,
        fields=fields,
        metadata=metadata,
        ingested_at=datetime.utcnow(),
    )

    matcher = DuplicateMatcher(store, cfg)
    duplicates = matcher.find(record, claim_id=claim_id)

    score = score_document(duplicates, metadata)

    if persist:
        store.add(record)

    return record, score, ocr
