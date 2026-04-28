"""Heuristic field extraction for Hebrew insurance-claim receipts.

Designed for *receipts* and *invoices* in Hebrew. Real production code
would use a layout-aware model (LayoutLMv3, Donut) fine-tuned on labeled
receipts. For a POC, regex + keyword anchors get us 80% of the way.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from dateutil import parser as date_parser

from ..models import OCRResult, ReceiptFields


# Hebrew anchor keywords for amount fields.
AMOUNT_KEYWORDS = [
    "סה\"כ", "סה״כ", "סה'כ", "סהכ",
    "סך הכל", "סך-הכל", "סך הכול",
    "לתשלום", "סכום לתשלום", "סך לתשלום",
    "total", "amount due", "grand total",
]

RECEIPT_NUM_KEYWORDS = [
    "מספר קבלה", "מס קבלה", "מס' קבלה", "מס׳ קבלה",
    "חשבונית מס", "מספר חשבונית", "מס חשבונית",
    "אסמכתא", "מס' אסמכתא", "מס׳ אסמכתא",
    "receipt no", "receipt number", "invoice no", "invoice number", "ref",
]

DATE_KEYWORDS = [
    "תאריך", "תאריך הנפקה", "תאריך קבלה", "תאריך חשבונית", "תאריך תשלום",
    "date", "issue date",
]

CURRENCY_PATTERNS = [
    (r"₪|ש\"ח|ש״ח|שח|nis|ils", "ILS"),
    (r"\$|usd|us\$|dollar", "USD"),
    (r"€|eur|euro", "EUR"),
]


# --- helpers ---------------------------------------------------------

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def _normalize(text: str) -> str:
    """Normalize Unicode (NFKC) — folds Hebrew presentation forms,
    geresh/gershayim variants, etc."""
    return unicodedata.normalize("NFKC", text).strip()


def _clean_amount(num_text: str) -> float | None:
    s = num_text.replace(",", "").replace(" ", "")
    s = s.replace("‏", "").replace("‎", "")  # RLM/LRM
    try:
        return float(s)
    except ValueError:
        return None


def _line_score(line: str, keywords: Iterable[str]) -> int:
    low = line.lower()
    return sum(1 for kw in keywords if kw.lower() in low)


# --- amount ----------------------------------------------------------

# Captures an Israeli-style number with optional thousands separators
# and 0–2 decimal places. Examples: 600, 1,600, 1600.00, 1,600.50
# Order matters: we try the comma-separated form first (otherwise the
# bare \d+ alt would happily eat "1,600" as just "1").
NUMBER_RE = re.compile(
    r"\d{1,3}(?:[,  ]\d{3})+(?:\.\d{1,2})?"   # 1,600 / 1 600 / 1,600.50
    r"|\d+(?:\.\d{1,2})?"                            # 1600 / 600.00
)


def _extract_amount(text: str) -> tuple[float | None, str | None]:
    text = _normalize(text)
    lines = [l for l in text.splitlines() if l.strip()]

    # Pass 1: lines that contain an amount keyword — best signal.
    candidates: list[tuple[int, float, str]] = []
    for line in lines:
        kw_score = _line_score(line, AMOUNT_KEYWORDS)
        if kw_score == 0:
            continue
        for m in NUMBER_RE.finditer(line):
            val = _clean_amount(m.group())
            if val is None or val < 1:
                continue
            candidates.append((kw_score, val, line))

    currency = None
    low = text.lower()
    for pat, code in CURRENCY_PATTERNS:
        if re.search(pat, low, flags=re.IGNORECASE):
            currency = code
            break

    if candidates:
        # Highest keyword score, then largest value (totals are usually bigger).
        candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return candidates[0][1], currency

    # Pass 2: just take the largest plausible number in the document.
    nums = [_clean_amount(m.group()) for m in NUMBER_RE.finditer(text)]
    nums = [n for n in nums if n is not None and 1 <= n < 1_000_000]
    if nums:
        return max(nums), currency

    return None, currency


# --- date ------------------------------------------------------------

DATE_PATTERNS = [
    r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b",     # DD/MM/YYYY (Israeli)
    r"\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b",       # YYYY-MM-DD (ISO)
]


def _extract_date(text: str) -> str | None:
    text = _normalize(text)
    lines = text.splitlines()

    # Prefer dates on lines that mention a date keyword.
    keyword_lines = [l for l in lines if _line_score(l, DATE_KEYWORDS) > 0]
    search_order = keyword_lines + [l for l in lines if l not in keyword_lines]

    for line in search_order:
        for pat in DATE_PATTERNS:
            m = re.search(pat, line)
            if not m:
                continue
            try:
                # dayfirst=True for Israeli DD/MM/YYYY format.
                dt = date_parser.parse(m.group(), dayfirst=True, fuzzy=False)
                # Sanity: receipts are usually within +/- 30 years of today.
                if 1990 <= dt.year <= 2100:
                    return dt.date().isoformat()
            except (ValueError, OverflowError):
                continue
    return None


# --- receipt number --------------------------------------------------

RECEIPT_NUM_RE = re.compile(r"[0-9]{4,}")


def _extract_receipt_number(text: str) -> str | None:
    text = _normalize(text)
    for line in text.splitlines():
        if _line_score(line, RECEIPT_NUM_KEYWORDS) > 0:
            m = RECEIPT_NUM_RE.search(line)
            if m:
                return m.group()
    return None


# --- provider --------------------------------------------------------

def _extract_provider(ocr: OCRResult) -> str | None:
    """Best-guess provider name: the topmost non-trivial line of the receipt
    (often the business name in the header)."""
    lines = [l for l in ocr.lines if l.text and l.bbox is not None]
    if not lines:
        # Fallback: first non-empty line of plain text.
        for line in ocr.text.splitlines():
            line = line.strip()
            if len(line) >= 3:
                return _normalize(line)
        return None

    # Sort by y-coordinate (top first), filter out very short lines.
    lines = sorted(lines, key=lambda l: (l.bbox or (0, 0, 0, 0))[1])
    for l in lines:
        text = _normalize(l.text)
        if len(text) >= 3 and not NUMBER_RE.fullmatch(text):
            return text
    return None


# --- public API ------------------------------------------------------

def extract_receipt_fields(ocr: OCRResult) -> ReceiptFields:
    text = ocr.text
    amount, currency = _extract_amount(text)
    return ReceiptFields(
        provider=_extract_provider(ocr),
        issue_date=_extract_date(text),
        amount=amount,
        currency=currency,
        receipt_number=_extract_receipt_number(text),
        raw_text=text,
    )


# --- text fingerprint for duplicate detection ------------------------

def text_fingerprint(fields: ReceiptFields) -> str:
    """Canonical short signature: provider|date|amount|receipt_number.
    Used as an exact-match key in the duplicate store. Returns an empty
    string when fewer than two fields are populated (so we don't match
    two empty fingerprints to each other)."""
    parts = [
        _NON_WORD.sub("", (fields.provider or "").lower()),
        fields.issue_date or "",
        f"{fields.amount:.2f}" if fields.amount is not None else "",
        fields.receipt_number or "",
    ]
    if sum(1 for p in parts if p) < 2:
        return ""
    return "|".join(parts)


def _tokenize(text: str) -> set[str]:
    text = _normalize(text).lower()
    return {t for t in _NON_WORD.split(text) if len(t) >= 2}


def fingerprint_similarity(a: ReceiptFields, b: ReceiptFields) -> float:
    """Jaccard similarity over normalized tokens of the raw OCR text.
    Survives re-photograph of the same receipt where pixel hashes won't."""
    ta, tb = _tokenize(a.raw_text), _tokenize(b.raw_text)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
