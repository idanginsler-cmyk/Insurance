from __future__ import annotations

from ..models import (
    DuplicateMatch, FraudScore, FraudSignal, MetadataReport, RiskLevel,
)


# Weights are tuned for a *low-recall, high-precision* scorer:
# we'd rather flag a real duplicate than scream wolf on a metadata quirk.
WEIGHTS = {
    "sha256_exact":         95.0,   # same file submitted twice
    "field_fingerprint":    80.0,   # same provider+date+amount+receipt#
    "phash_exact":          75.0,   # same image
    "embedding_cosine":     60.0,
    "phash_near":           45.0,
    "text_jaccard":         50.0,
    "pdf_incremental":      35.0,   # PDF saved with edits after creation
    "pdf_modified":         15.0,
    "suspect_producer":     30.0,
    "no_exif":               5.0,
    "missing_producer":      5.0,
    "unknown_producer":      3.0,
}


def _level_for(score: float) -> RiskLevel:
    if score >= 80: return RiskLevel.CRITICAL
    if score >= 55: return RiskLevel.HIGH
    if score >= 30: return RiskLevel.MEDIUM
    if score >= 10: return RiskLevel.LOW
    return RiskLevel.CLEAN


def score_document(
    duplicates: list[DuplicateMatch],
    metadata: MetadataReport,
) -> FraudScore:
    signals: list[FraudSignal] = []
    reasons: list[str] = []

    # --- Duplicate signals ------------------------------------------------
    # Take the strongest match per type; multiple weak matches don't pile up.
    seen_types: set[str] = set()
    for match in duplicates:
        if match.match_type in seen_types:
            continue
        seen_types.add(match.match_type)
        weight = WEIGHTS.get(match.match_type, 20.0)
        signals.append(FraudSignal(
            name=f"duplicate:{match.match_type}",
            weight=weight,
            triggered=True,
            detail=f"{match.note or match.match_type} (doc={match.document_id})",
        ))
        reasons.append(match.note or f"זוהה דמיון מסוג {match.match_type}")

    # --- Metadata signals -------------------------------------------------
    for s in metadata.suspicions:
        if s.startswith("pdf_incremental_updates"):
            signals.append(FraudSignal(name=s, weight=WEIGHTS["pdf_incremental"], triggered=True,
                                       detail="ה-PDF עבר עדכונים מצטברים אחרי היצירה."))
            reasons.append("מבנה PDF מצביע על עריכה אחרי הפקה ראשונית.")
        elif s == "pdf_modified_after_creation":
            signals.append(FraudSignal(name=s, weight=WEIGHTS["pdf_modified"], triggered=True,
                                       detail="ModDate שונה מ-CreationDate."))
            reasons.append("תאריך שינוי שונה מתאריך יצירה ב-PDF.")
        elif s.startswith("suspect_producer:"):
            signals.append(FraudSignal(name=s, weight=WEIGHTS["suspect_producer"], triggered=True,
                                       detail=f"Producer חשוד: {s.split(':',1)[1]}"))
            reasons.append(f"כלי הפקה חשוד ({s.split(':',1)[1]}).")
        elif s == "no_exif":
            signals.append(FraudSignal(name=s, weight=WEIGHTS["no_exif"], triggered=True,
                                       detail="לתמונה אין EXIF — ייתכן re-save."))
        elif s == "missing_producer_metadata":
            signals.append(FraudSignal(name=s, weight=WEIGHTS["missing_producer"], triggered=True,
                                       detail="ל-PDF אין שדה Producer."))
        elif s == "unknown_producer":
            signals.append(FraudSignal(name=s, weight=WEIGHTS["unknown_producer"], triggered=True,
                                       detail="Producer לא ברשימת הסורקים/יוצרים המאושרים."))
        else:
            signals.append(FraudSignal(name=s, weight=10.0, triggered=True, detail=s))

    # --- Aggregation ------------------------------------------------------
    # Use the *max* weight for duplicates (single strong evidence is enough)
    # and *sum* metadata weights, capped at 100.
    dup_weight = max((s.weight for s in signals if s.name.startswith("duplicate:")),
                     default=0.0)
    meta_weight = sum(s.weight for s in signals if not s.name.startswith("duplicate:"))
    score = min(100.0, dup_weight + meta_weight * 0.7)

    return FraudScore(
        score=round(score, 2),
        level=_level_for(score),
        reasons=reasons,
        signals=signals,
        duplicates=duplicates,
    )
