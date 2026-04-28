"""End-to-end demo of typography-only detection.

Renders a clean receipt and a tampered version where '600' was edited
to '1600' by pasting in a '1' from a different font/size — the kind of
manual edit that has no companion document to compare against.

Runs the full fraud-detection pipeline (with no prior store entries)
and prints the resulting score & anomalies.

Usage:
    PYTHONPATH=src python scripts/demo_typography.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Make `src` importable.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fraud_detection.duplicates.store import DocumentStore
from fraud_detection.pipeline import analyze


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.truetype("DejaVuSans.ttf", size)


def render_clean(path: Path) -> None:
    img = Image.new("RGB", (700, 400), "white")
    d = ImageDraw.Draw(img)
    f_body = _font(28)
    f_amount = _font(40)
    d.text((30, 30),  "Dr. Cohen Clinic", fill="black", font=f_body)
    d.text((30, 80),  "Date: 15/03/2026", fill="black", font=f_body)
    d.text((30, 130), "Receipt #: 123456", fill="black", font=f_body)
    d.text((30, 180), "Item: Acamol", fill="black", font=f_body)
    d.text((30, 240), "TOTAL: 600.00", fill="black", font=f_amount)
    img.save(path)


def render_forged(path: Path) -> None:
    """Same receipt, but a '1' has been pasted in front of '600' — using
    a slightly larger font and a small upward offset, mimicking what a
    fraudster does in MS Paint or Photoshop."""
    img = Image.new("RGB", (700, 400), "white")
    d = ImageDraw.Draw(img)
    f_body = _font(28)
    f_amount = _font(40)
    f_tampered = _font(48)   # ← deliberately bigger
    d.text((30, 30),  "Dr. Cohen Clinic", fill="black", font=f_body)
    d.text((30, 80),  "Date: 15/03/2026", fill="black", font=f_body)
    d.text((30, 130), "Receipt #: 123456", fill="black", font=f_body)
    d.text((30, 180), "Item: Acamol", fill="black", font=f_body)
    # "TOTAL: " in original size
    d.text((30, 240), "TOTAL: ", fill="black", font=f_amount)
    # The pasted '1' — different font size + 4px upward shift.
    d.text((180, 236), "1", fill="black", font=f_tampered)
    # The original "600.00" rendered after the inserted '1'.
    d.text((215, 240), "600.00", fill="black", font=f_amount)
    img.save(path)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean.png"
        forged = Path(tmp) / "forged.png"
        render_clean(clean)
        render_forged(forged)

        # Use a fresh empty store so duplicate signals can't fire.
        store = DocumentStore(Path(tmp) / "store.db")
        try:
            print("=" * 70)
            print("CLEAN receipt:")
            print("=" * 70)
            rec, score, ocr = analyze(clean, store, claim_id="demo")
            _print(rec, score)

            print()
            print("=" * 70)
            print("FORGED receipt (1 prepended to 600 → 1600, larger font):")
            print("=" * 70)
            rec, score, ocr = analyze(forged, store, claim_id="demo")
            _print(rec, score)
        finally:
            store.close()


def _print(record, score):
    print(f"  score: {score.score}    level: {score.level.value.upper()}")
    print(f"  ocr engine: {record.fields.raw_text[:50]!r}...")
    if record.typography:
        t = record.typography
        print(f"  typography: source={t.source}  "
              f"chars={t.chars_analyzed}  lines={t.lines_analyzed}  "
              f"anomalies={len(t.anomalies)}  suspicion={t.suspicion_score:.2f}")
        for a in sorted(t.anomalies, key=lambda x: abs(x.z_score), reverse=True)[:5]:
            print(f"    - {a.metric:10s}  '{a.char}'  "
                  f"line={a.line_index} idx={a.char_index}  "
                  f"z={a.z_score:+.2f}  {a.detail}")
    if score.reasons:
        print("  reasons:")
        for r in score.reasons:
            print(f"    • {r}")


if __name__ == "__main__":
    main()
