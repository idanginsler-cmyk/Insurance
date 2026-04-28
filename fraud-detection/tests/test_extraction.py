from fraud_detection.extraction.fields import (
    extract_receipt_fields, fingerprint_similarity, text_fingerprint,
)
from fraud_detection.models import OCRLine, OCRResult, ReceiptFields


def _ocr(text: str) -> OCRResult:
    return OCRResult(
        text=text,
        lines=[OCRLine(text=l, bbox=(0, i * 30, 100, (i + 1) * 30))
               for i, l in enumerate(text.splitlines())],
        engine="test",
        lang="heb",
    )


def test_extract_amount_with_hebrew_keyword():
    ocr = _ocr("מרפאת כהן\nתאריך: 15/03/2026\nסה\"כ לתשלום: 600.00 ש\"ח")
    f = extract_receipt_fields(ocr)
    assert f.amount == 600.00
    assert f.currency == "ILS"


def test_extract_amount_picks_largest_when_no_keyword():
    ocr = _ocr("פריט A 100\nפריט B 250\nפריט C 1600")
    f = extract_receipt_fields(ocr)
    assert f.amount == 1600.0


def test_extract_date_dayfirst():
    ocr = _ocr("תאריך: 15/03/2026")
    f = extract_receipt_fields(ocr)
    # Israeli DD/MM/YYYY -> ISO YYYY-MM-DD
    assert f.issue_date == "2026-03-15"


def test_extract_receipt_number():
    ocr = _ocr("מספר קבלה: 123456")
    f = extract_receipt_fields(ocr)
    assert f.receipt_number == "123456"


def test_extract_provider_from_top_line():
    ocr = _ocr("מרפאת ד\"ר כהן\nתאריך: 15/03/2026\nסה\"כ: 600 ש\"ח")
    f = extract_receipt_fields(ocr)
    assert "כהן" in (f.provider or "")


def test_text_fingerprint_changes_with_amount():
    a = ReceiptFields(provider="כהן", issue_date="2026-03-15", amount=600.0,
                      receipt_number="123456", raw_text="x")
    b = ReceiptFields(provider="כהן", issue_date="2026-03-15", amount=1600.0,
                      receipt_number="123456", raw_text="x")
    assert text_fingerprint(a) != text_fingerprint(b)


def test_fingerprint_similarity_high_for_identical_text():
    text = "מרפאת ד\"ר כהן תאריך 15 03 2026 קבלה 123456 אקמול 600 ש\"ח"
    a = ReceiptFields(raw_text=text)
    b = ReceiptFields(raw_text=text)
    assert fingerprint_similarity(a, b) == 1.0


def test_fingerprint_similarity_low_for_unrelated_text():
    a = ReceiptFields(raw_text="קבלה ראשונה אקמול")
    b = ReceiptFields(raw_text="invoice from a totally unrelated provider")
    assert fingerprint_similarity(a, b) < 0.3
