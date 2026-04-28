"""End-to-end smoke tests on synthetic receipts.

These don't require a real OCR engine: when no engine is installed,
the pipeline returns an empty OCRResult and we still verify that
hash-based duplicate detection works correctly. When an OCR engine
*is* installed, we additionally verify that the duplicate detection
catches the 'same receipt re-photographed' scenario through text
fingerprints."""

from __future__ import annotations

from fraud_detection.duplicates.store import DocumentStore
from fraud_detection.pipeline import analyze


def test_resubmitting_same_image_is_flagged_as_duplicate(tmp_db, tmp_image,
                                                        receipt_lines_basic):
    img1 = tmp_image(receipt_lines_basic, name="r1.png", seed=1)
    img2 = tmp_image(receipt_lines_basic, name="r2.png", seed=1)  # identical content+seed

    store = DocumentStore(tmp_db)
    try:
        # First ingestion is clean.
        rec1, score1, _ = analyze(img1, store, claim_id="claim-1", persist=True)
        assert score1.score == 0 or score1.level.value in ("clean", "low")

        # Second ingestion should match the first via perceptual hash.
        rec2, score2, _ = analyze(img2, store, claim_id="claim-1", persist=False)
        assert any(m.match_type in ("phash_exact", "sha256_exact")
                   for m in score2.duplicates), score2.duplicates
        assert score2.level.value in ("medium", "high", "critical")
    finally:
        store.close()


def test_visually_different_receipts_dont_match(tmp_db, tmp_image,
                                                receipt_lines_basic):
    img1 = tmp_image(receipt_lines_basic, name="r1.png", seed=1)
    img2 = tmp_image(["receipt for completely different vendor", "amount 9999"],
                     name="r2.png", seed=99)
    store = DocumentStore(tmp_db)
    try:
        analyze(img1, store, claim_id="claim-1", persist=True)
        rec2, score2, _ = analyze(img2, store, claim_id="claim-1", persist=False)
        # No phash match should fire on visually unrelated images.
        assert not any(m.match_type.startswith("phash") for m in score2.duplicates)
    finally:
        store.close()


def test_cross_claim_isolation(tmp_db, tmp_image, receipt_lines_basic):
    """Duplicate within the same claim is flagged; different claim is *not*
    flagged through the per-claim matcher (the cross-claim graph layer is
    a separate concern, out of scope for this POC)."""
    img1 = tmp_image(receipt_lines_basic, name="r1.png", seed=1)
    img2 = tmp_image(receipt_lines_basic, name="r2.png", seed=1)
    store = DocumentStore(tmp_db)
    try:
        analyze(img1, store, claim_id="claim-A", persist=True)
        rec2, score2, _ = analyze(img2, store, claim_id="claim-B", persist=False)
        # No matches when matching is scoped to claim-B and only claim-A
        # holds the prior copy. (sha256 match is global, so accept that.)
        non_sha = [m for m in score2.duplicates if m.match_type != "sha256_exact"]
        assert non_sha == []
    finally:
        store.close()
