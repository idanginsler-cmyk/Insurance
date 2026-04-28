from __future__ import annotations

from typing import Optional

import numpy as np

from ..config import Config
from ..extraction.fields import fingerprint_similarity, text_fingerprint
from ..forensics.perceptual_hash import hamming_distance
from ..models import DocumentRecord, DuplicateMatch
from .store import DocumentStore


class DuplicateMatcher:
    """Finds duplicates of a candidate document against the store.

    Strategy (cheap → expensive):
      1. SHA-256 exact match (free, instant).
      2. Perceptual hashes (fast, robust to mild edits).
      3. Field-level fingerprint (provider, date, amount, receipt#).
      4. OCR-text Jaccard (survives re-photograph).
      5. Optional: CLIP embedding cosine (heavy).
    """

    def __init__(self, store: DocumentStore, cfg: Config | None = None) -> None:
        self.store = store
        self.cfg = cfg or Config()

    def find(
        self,
        candidate: DocumentRecord,
        claim_id: str | None = None,
        candidate_embedding: Optional[np.ndarray] = None,
    ) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        scope_claim = claim_id or candidate.claim_id

        # --- 1. SHA exact ------------------------------------------------
        for rec in self.store.by_sha256(candidate.sha256):
            if rec.document_id == candidate.document_id:
                continue
            matches.append(DuplicateMatch(
                document_id=rec.document_id,
                claim_id=rec.claim_id,
                match_type="sha256_exact",
                similarity=1.0,
                distance=0,
                matched_at=rec.ingested_at,
                note="ביט-לביט זהה — אותו קובץ הוגש פעמיים.",
            ))

        # Iterate the (scoped) corpus once for the remaining checks.
        cand_fp = text_fingerprint(candidate.fields)

        for rec in self.store.iter_records(
            claim_id=scope_claim, exclude_id=candidate.document_id
        ):
            # --- 2. Perceptual hashes -----------------------------------
            # Require *both* phash and dhash to agree — using max(...) cuts
            # false positives sharply on documents with similar layout but
            # different content (only one of the hashes happens to align).
            d_phash = hamming_distance(candidate.hashes.phash, rec.hashes.phash)
            d_dhash = hamming_distance(candidate.hashes.dhash, rec.hashes.dhash)
            d_agree = max(d_phash, d_dhash)

            if d_agree <= self.cfg.phash_exact_threshold:
                matches.append(DuplicateMatch(
                    document_id=rec.document_id, claim_id=rec.claim_id,
                    match_type="phash_exact",
                    similarity=1.0 - d_agree / 64.0,
                    distance=d_agree,
                    matched_at=rec.ingested_at,
                    note=f"phash={d_phash} dhash={d_dhash} — כמעט בוודאות אותה תמונה.",
                ))
            elif d_agree <= self.cfg.phash_near_threshold:
                matches.append(DuplicateMatch(
                    document_id=rec.document_id, claim_id=rec.claim_id,
                    match_type="phash_near",
                    similarity=1.0 - d_agree / 64.0,
                    distance=d_agree,
                    matched_at=rec.ingested_at,
                    note=f"phash={d_phash} dhash={d_dhash} — תמונה חזותית דומה.",
                ))

            # --- 3. Field fingerprint ----------------------------------
            rec_fp = text_fingerprint(rec.fields)
            if cand_fp and cand_fp == rec_fp:
                matches.append(DuplicateMatch(
                    document_id=rec.document_id, claim_id=rec.claim_id,
                    match_type="field_fingerprint",
                    similarity=1.0,
                    matched_at=rec.ingested_at,
                    note="ספק+תאריך+סכום+מס׳ קבלה זהים — חשד הגשה כפולה.",
                ))

            # --- 4. OCR-text Jaccard -----------------------------------
            sim = fingerprint_similarity(candidate.fields, rec.fields)
            if sim >= self.cfg.text_fingerprint_threshold:
                matches.append(DuplicateMatch(
                    document_id=rec.document_id, claim_id=rec.claim_id,
                    match_type="text_jaccard",
                    similarity=sim,
                    matched_at=rec.ingested_at,
                    note=f"דמיון טקסט {sim:.0%} — סביר שאותו מסמך צולם מחדש.",
                ))

            # --- 5. Embedding cosine (optional) ------------------------
            if candidate_embedding is not None:
                rec_emb = self.store.get_embedding(rec.document_id)
                if rec_emb is not None and rec_emb.size:
                    cos = float(np.dot(candidate_embedding, rec_emb))
                    if cos >= self.cfg.embedding_threshold:
                        matches.append(DuplicateMatch(
                            document_id=rec.document_id, claim_id=rec.claim_id,
                            match_type="embedding_cosine",
                            similarity=cos,
                            matched_at=rec.ingested_at,
                            note=f"CLIP cosine={cos:.3f} — דמיון סמנטי גבוה.",
                        ))

        return _dedupe_matches(matches)


def _dedupe_matches(matches: list[DuplicateMatch]) -> list[DuplicateMatch]:
    """Keep the strongest match per (target_document_id) but preserve order."""
    best: dict[str, DuplicateMatch] = {}
    for m in matches:
        prev = best.get(m.document_id)
        if prev is None or m.similarity > prev.similarity:
            best[m.document_id] = m
    return sorted(best.values(), key=lambda m: m.similarity, reverse=True)
