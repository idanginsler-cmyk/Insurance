"""Shared test fixtures.

Generates synthetic receipt-like images programmatically so the test
suite runs without any sample documents."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Optional

import pytest
from PIL import Image, ImageDraw, ImageFont


# Make `src` importable without `pip install -e`.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _font(size: int = 18) -> ImageFont.ImageFont:
    """Use the default PIL font — works without any system fonts.

    For real Hebrew rendering you'd want a TTF such as Arial/Open Sans
    Hebrew, but we don't need glyph fidelity for hash/regex tests.
    """
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_receipt(
    lines: list[str],
    *,
    width: int = 600,
    height: int = 800,
    bg: str = "white",
    fg: str = "black",
    seed: Optional[int] = None,
) -> Image.Image:
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    font = _font(20)
    y = 20
    for line in lines:
        draw.text((20, y), line, fill=fg, font=font)
        y += 30
    if seed is not None:
        # Add a deterministic pseudo-noise pixel so two "different" receipts
        # have measurably different perceptual hashes.
        import random
        rng = random.Random(seed)
        for _ in range(50):
            x = rng.randint(0, width - 1)
            yy = rng.randint(0, height - 1)
            draw.point((x, yy), fill="gray")
    return img


@pytest.fixture
def tmp_image(tmp_path):
    def _make(lines: list[str], name: str = "receipt.png", seed: int | None = None) -> Path:
        img = render_receipt(lines, seed=seed)
        path = tmp_path / name
        img.save(path)
        return path
    return _make


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "store.db"


@pytest.fixture
def receipt_lines_basic():
    return [
        "מרפאת ד\"ר כהן",
        "רחוב הרצל 12, תל אביב",
        "תאריך: 15/03/2026",
        "מספר קבלה: 123456",
        "תרופה: אקמול",
        "סה\"כ לתשלום: 600.00 ש\"ח",
    ]


@pytest.fixture
def receipt_lines_forged_amount():
    """Same receipt, but the '6' became '16' — classic '1' prepended forgery."""
    return [
        "מרפאת ד\"ר כהן",
        "רחוב הרצל 12, תל אביב",
        "תאריך: 15/03/2026",
        "מספר קבלה: 123456",
        "תרופה: אקמול",
        "סה\"כ לתשלום: 1600.00 ש\"ח",
    ]
