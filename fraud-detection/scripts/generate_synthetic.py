"""Generate a synthetic claim file for end-to-end testing.

Creates a small directory of receipt images simulating common fraud
scenarios:

  claim_001/
    receipt_genuine.png            real receipt, 600 ILS
    receipt_resubmitted.png        bit-identical re-submission
    receipt_amount_forged.png      same receipt but '600' edited to '1600'
    receipt_unrelated.png          different provider, different amount

Usage:
    python scripts/generate_synthetic.py [output_dir]
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int = 20):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_receipt(lines, *, width=600, height=800, seed=None) -> Image.Image:
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = _font(20)
    y = 20
    for line in lines:
        draw.text((20, y), line, fill="black", font=font)
        y += 30
    if seed is not None:
        rng = random.Random(seed)
        for _ in range(50):
            draw.point((rng.randint(0, width - 1), rng.randint(0, height - 1)),
                       fill="gray")
    return img


GENUINE = [
    'מרפאת ד"ר כהן',
    "רחוב הרצל 12, תל אביב",
    "תאריך: 15/03/2026",
    "מספר קבלה: 123456",
    "תרופה: אקמול",
    'סה"כ לתשלום: 600.00 ש"ח',
]

FORGED_AMOUNT = [
    'מרפאת ד"ר כהן',
    "רחוב הרצל 12, תל אביב",
    "תאריך: 15/03/2026",
    "מספר קבלה: 123456",
    "תרופה: אקמול",
    'סה"כ לתשלום: 1600.00 ש"ח',  # ← '1' prepended
]

UNRELATED = [
    'בית מרקחת סופר-פארם, סניף דיזנגוף',
    "רחוב דיזנגוף 50, תל אביב",
    "תאריך: 22/03/2026",
    "מספר קבלה: 987654",
    "מוצר: ויטמין D",
    'סה"כ: 89.90 ש"ח',
]


def main(out_dir: str = "data/samples/claim_001") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    render_receipt(GENUINE, seed=1).save(out / "receipt_genuine.png")
    render_receipt(GENUINE, seed=1).save(out / "receipt_resubmitted.png")  # identical
    render_receipt(FORGED_AMOUNT, seed=1).save(out / "receipt_amount_forged.png")
    render_receipt(UNRELATED, seed=42).save(out / "receipt_unrelated.png")

    print(f"4 synthetic receipts written to {out}")
    for p in sorted(out.glob("*.png")):
        print(f"  - {p.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/samples/claim_001")
