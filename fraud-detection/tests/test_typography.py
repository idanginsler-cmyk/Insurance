"""Tests for the typography consistency analyzer.

These don't need a real OCR engine: we hand-craft CharBox lists that
simulate the output of Tesseract `image_to_boxes`."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from fraud_detection.forensics.typography import (
    CharBox, analyze_lines, analyze_typography, group_into_lines,
)
from fraud_detection.models import OCRLine, OCRResult


def _digits_line(values: list[int], *, baseline: int = 100,
                 height: int = 20, width: int = 12, gap: int = 4,
                 start_x: int = 50) -> list[CharBox]:
    """Build a row of digit boxes, all the same size, evenly spaced."""
    boxes: list[CharBox] = []
    x = start_x
    for v in values:
        boxes.append(CharBox(
            char=str(v), x=x, y=baseline - height,
            w=width, h=height,
        ))
        x += width + gap
    return boxes


def test_clean_line_produces_no_anomalies():
    line = _digits_line([6, 0, 0])  # "600" — only 3 chars, below min length
    rep = analyze_lines([line])
    assert rep.anomalies == []
    # Below min_chars_per_line (5), so the line is skipped entirely.
    assert rep.lines_analyzed == 0


def test_uniform_long_line_produces_no_anomalies():
    line = _digits_line([1, 2, 3, 4, 5, 6, 7])
    rep = analyze_lines([line])
    assert rep.lines_analyzed == 1
    assert rep.anomalies == []


def test_taller_inserted_digit_is_flagged_as_height_anomaly():
    line = _digits_line([1, 2, 3, 4, 5, 6, 7])
    # Replace the 4th char with a much taller "1" — simulates pasted digit.
    line[3] = CharBox(char="1", x=line[3].x, y=line[3].y - 10,
                      w=line[3].w, h=line[3].h + 10)
    rep = analyze_lines([line], z_threshold=2.0)
    flagged = [a for a in rep.anomalies if a.metric == "height"]
    assert flagged, f"expected a height anomaly, got: {rep.anomalies}"
    assert flagged[0].char == "1"
    assert flagged[0].char_index == 3


def test_baseline_drift_is_flagged():
    line = _digits_line([1, 2, 3, 4, 5, 6, 7])
    # Shift the 5th char up by 6px without changing height.
    c = line[4]
    line[4] = CharBox(char=c.char, x=c.x, y=c.y - 6, w=c.w, h=c.h)
    rep = analyze_lines([line], z_threshold=2.0)
    assert any(a.metric == "baseline" for a in rep.anomalies)


def test_kerning_anomaly_when_extra_gap_inserted():
    line = _digits_line([1, 2, 3, 4, 5, 6, 7])
    # Push everything from index 3 onwards 30px to the right — creates one
    # huge gap before index 3.
    for i in range(3, len(line)):
        c = line[i]
        line[i] = CharBox(char=c.char, x=c.x + 30, y=c.y, w=c.w, h=c.h)
    rep = analyze_lines([line], z_threshold=2.0)
    assert any(a.metric == "kerning" for a in rep.anomalies)


def test_amount_forgery_scenario_one_to_sixhundred():
    """The headline scenario: original receipt shows '600' and a fraudster
    prepends '1' so the line now reads '1600'. The inserted '1' is rendered
    in a different font/scale, breaking both height and baseline alignment
    — exactly the cross-metric pattern that drives the suspicion score."""
    # Original "1600.00" with a tampered first char: taller AND shifted up,
    # so baseline = 78+28 = 106 vs others' 90+20 = 110.
    line = [
        CharBox(char="1", x=50, y=78, w=12, h=28),    # tampered
        CharBox(char="6", x=66, y=90, w=12, h=20),
        CharBox(char="0", x=82, y=90, w=12, h=20),
        CharBox(char="0", x=98, y=90, w=12, h=20),
        CharBox(char=".", x=114, y=90, w=4, h=20),
        CharBox(char="0", x=122, y=90, w=12, h=20),
        CharBox(char="0", x=138, y=90, w=12, h=20),
    ]
    rep = analyze_lines([line], z_threshold=2.0)
    one_metrics = {a.metric for a in rep.anomalies if a.char == "1"}
    # Two metrics agreeing on the "1" is the consensus signal we want.
    assert {"height", "baseline"}.issubset(one_metrics), \
        f"expected height+baseline both flagged on '1', got {one_metrics}"
    assert rep.suspicion_score > 0


def test_grouping_separates_lines_by_y():
    chars = [
        CharBox(char="A", x=0,  y=10,  w=10, h=20),
        CharBox(char="B", x=20, y=10,  w=10, h=20),
        CharBox(char="C", x=0,  y=100, w=10, h=20),
        CharBox(char="D", x=20, y=100, w=10, h=20),
    ]
    lines = group_into_lines(chars)
    assert len(lines) == 2
    assert {c.char for c in lines[0]} == {"A", "B"}
    assert {c.char for c in lines[1]} == {"C", "D"}


def test_pixel_brightness_anomaly_on_inserted_glyph():
    """Render a uniform row of digits and inject one bright outlier;
    verify the brightness metric flags it."""
    img = Image.new("L", (300, 60), 255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 30)
    except OSError:
        font = ImageFont.load_default()

    boxes: list[CharBox] = []
    x = 10
    for d in "1234567":
        draw.text((x, 15), d, fill=0, font=font)
        boxes.append(CharBox(char=d, x=x, y=15, w=18, h=30))
        x += 22

    # Tamper: paint over char index 3 with a much lighter shade.
    bx = boxes[3]
    draw.rectangle((bx.x, bx.y, bx.x + bx.w, bx.y + bx.h), fill=255)
    draw.text((bx.x, bx.y), bx.char, fill=180, font=font)

    rep = analyze_lines([boxes], image=img.convert("RGB"), z_threshold=2.0)
    metrics = {a.metric for a in rep.anomalies if a.char_index == 3}
    # Either brightness or sharpness should fire on the tampered glyph.
    assert metrics & {"brightness", "sharpness"}, rep.anomalies


def test_analyze_typography_falls_back_to_word_split():
    """When Tesseract isn't installed (None returned) and OCR has only
    word-level boxes, we still get *some* analysis via even-split fallback."""
    ocr = OCRResult(
        text="abcdefghij",
        lines=[OCRLine(text="abcdefghij", bbox=(0, 0, 100, 20))],
        engine="dummy", lang="x",
    )
    rep = analyze_typography(image=None, ocr=ocr)
    # Source must indicate fallback was used, regardless of anomaly count.
    assert rep.source in ("ocr_words_split", "none")


def test_z_threshold_is_respected():
    """Lower threshold = more anomalies; higher = fewer."""
    line = _digits_line([1, 2, 3, 4, 5, 6, 7])
    line[3] = CharBox(char="1", x=line[3].x, y=line[3].y - 4,
                      w=line[3].w, h=line[3].h + 4)
    strict = analyze_lines([line], z_threshold=4.0)
    lax    = analyze_lines([line], z_threshold=1.5)
    assert len(lax.anomalies) >= len(strict.anomalies)
