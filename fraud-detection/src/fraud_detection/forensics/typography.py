"""Single-document forgery detection via typography consistency.

Idea: when a fraudster prepends "1" to "600" with an editor, the inserted
glyph almost always breaks one or more local consistencies on its line:

  * **Height** — the new char's bbox height differs from neighbors.
  * **Baseline** — the new char sits slightly above or below the line baseline.
  * **Kerning** — the gap to neighboring chars differs from the line's mean.
  * **Sharpness** (pixel-level) — a pasted glyph often has different
    Laplacian variance (over- or under-sharpened relative to its line).
  * **Brightness** (pixel-level) — re-rasterized chars typically have
    different mean intensity than chars from the original scan.

For each metric, we compute per-line μ/σ across all chars on the line and
flag any char whose z-score exceeds a configurable threshold. Multiple
metrics can flag the same char; we count distinct anomalies and produce
a normalized 0..1 suspicion score.

The pixel-level checks use only NumPy + PIL — no GPU, no model.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np
from PIL import Image

from ..models import OCRLine, OCRResult, TypographyAnomaly, TypographyReport


# --- char-level box representation -------------------------------------

@dataclass
class CharBox:
    char: str
    x: int
    y: int     # top-left y
    w: int
    h: int

    @property
    def x_end(self) -> int:
        return self.x + self.w

    @property
    def baseline(self) -> int:    # bottom-y in image-coords
        return self.y + self.h


# --- Tesseract char-level extractor ------------------------------------

def chars_from_tesseract(image: Image.Image, lang: str = "heb+eng") -> list[CharBox] | None:
    """Run Tesseract `image_to_boxes` for true character-level boxes.

    Tesseract returns boxes in image coordinates with origin at
    *bottom-left*, so we flip y. Returns None if Tesseract isn't installed."""
    try:
        import pytesseract
        boxes = pytesseract.image_to_boxes(image, lang=lang)
    except Exception:
        return None

    H = image.height
    out: list[CharBox] = []
    for line in boxes.strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        ch, x1, y1, x2, y2 = parts[0], *map(int, parts[1:5])
        # Flip y: Tesseract uses bottom-origin; we use top-origin.
        top = H - max(y1, y2)
        bot = H - min(y1, y2)
        out.append(CharBox(char=ch, x=min(x1, x2), y=top,
                           w=abs(x2 - x1), h=abs(bot - top)))
    return out


# --- fallback: split word boxes into pseudo-character boxes ------------

def chars_from_word_boxes(ocr: OCRResult) -> list[CharBox]:
    """Approximate per-character boxes by evenly splitting each word's
    bbox by the number of characters. Works as a fallback when only
    word-level OCR is available (e.g. EasyOCR)."""
    out: list[CharBox] = []
    for line in ocr.lines:
        if not line.bbox or not line.text:
            continue
        x0, y0, x1, y1 = line.bbox
        text = line.text
        n = len(text)
        if n == 0:
            continue
        char_w = max(1, (x1 - x0) // n)
        for i, ch in enumerate(text):
            out.append(CharBox(
                char=ch, x=x0 + i * char_w, y=y0,
                w=char_w, h=y1 - y0,
            ))
    return out


# --- line grouping -----------------------------------------------------

def group_into_lines(
    chars: Iterable[CharBox],
    *,
    line_tolerance: float = 0.6,
) -> list[list[CharBox]]:
    """Cluster char boxes into lines by overlapping y-ranges.

    Two chars belong to the same line if their vertical overlap exceeds
    `line_tolerance` of the smaller char's height."""
    chars = sorted(chars, key=lambda c: (c.y, c.x))
    lines: list[list[CharBox]] = []
    for c in chars:
        placed = False
        for line in lines:
            ref = line[0]
            overlap = min(c.baseline, ref.baseline) - max(c.y, ref.y)
            min_h = min(c.h, ref.h)
            if min_h > 0 and overlap >= line_tolerance * min_h:
                line.append(c)
                placed = True
                break
        if not placed:
            lines.append([c])
    for line in lines:
        line.sort(key=lambda c: c.x)
    return lines


# --- pixel-level metrics ----------------------------------------------

_LAPLACIAN_KERNEL = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)


def _laplacian_variance(arr: np.ndarray) -> float:
    """Variance of Laplacian — standard "is this image sharp?" metric."""
    if arr.size == 0:
        return 0.0
    pad = np.pad(arr, 1, mode="edge")
    lap = (
        pad[0:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, 0:-2] + pad[1:-1, 2:]
        - 4.0 * pad[1:-1, 1:-1]
    )
    return float(lap.var())


def _crop_grayscale(image: Image.Image, c: CharBox, pad: int = 1) -> np.ndarray:
    x0 = max(0, c.x - pad); y0 = max(0, c.y - pad)
    x1 = min(image.width,  c.x_end + pad); y1 = min(image.height, c.baseline + pad)
    if x1 <= x0 or y1 <= y0:
        return np.empty((0, 0), dtype=np.float32)
    crop = image.crop((x0, y0, x1, y1)).convert("L")
    return np.asarray(crop, dtype=np.float32)


# --- main analyzer ----------------------------------------------------

def _safe_stdev(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) >= 2 else 0.0


def _is_digit(char: str) -> bool:
    return bool(char) and char.isdigit()


def _is_alphanumeric(char: str) -> bool:
    return bool(char) and char.isalnum()


_REFERENCE_PREDICATES = {
    "digits":       _is_digit,
    "alphanumeric": _is_alphanumeric,
    "all":          lambda c: bool(c) and not c.isspace(),
}


def _zscore(value: float, mu: float, sd: float) -> float | None:
    if sd <= 0:
        return None
    return (value - mu) / sd


def analyze_lines(
    lines: list[list[CharBox]],
    image: Optional[Image.Image] = None,
    *,
    z_threshold: float = 2.0,
    min_chars_per_line: int = 4,
    reference_chars: str = "digits",
) -> TypographyReport:
    """Per-line z-score outlier analysis.

    The headline use case is "an extra digit was prepended to an amount"
    — so by default only **digits** participate in (and are scored
    against) the line statistics. Letters' ascenders/descenders and
    punctuation create noise we don't care about.

    ``reference_chars``:
      * ``"digits"`` (default) — focused on amount/date/receipt# lines.
      * ``"alphanumeric"`` — letters + digits, useful when also looking
        for tampered words (e.g. an added "שבר" on a medical report).
      * ``"all"`` — every non-whitespace char (most noisy, debug only).
    """
    is_ref = _REFERENCE_PREDICATES[reference_chars]

    anomalies: list[TypographyAnomaly] = []
    chars_analyzed = 0
    lines_analyzed = 0
    suspicious_chars = 0

    for line_idx, line_chars in enumerate(lines):
        ref_chars = [c for c in line_chars if is_ref(c.char)]
        if len(ref_chars) < min_chars_per_line:
            continue
        lines_analyzed += 1
        chars_analyzed += len(line_chars)

        heights = [float(c.h) for c in ref_chars]
        baselines = [float(c.baseline) for c in ref_chars]
        # Kerning needs adjacent reference chars; build pairs from the
        # full line but use only adjacent alphanumeric ones for stats.
        ref_set_ids = {id(c) for c in ref_chars}
        gap_pairs: list[tuple[int, float]] = []  # (right_index_in_line, gap)
        for i in range(1, len(line_chars)):
            if id(line_chars[i - 1]) in ref_set_ids and id(line_chars[i]) in ref_set_ids:
                gap_pairs.append((i, float(line_chars[i].x - line_chars[i - 1].x_end)))
        gaps_only = [g for _, g in gap_pairs]

        h_mu, h_sd = statistics.mean(heights), _safe_stdev(heights)
        b_mu, b_sd = statistics.mean(baselines), _safe_stdev(baselines)
        g_mu, g_sd = (
            (statistics.mean(gaps_only), _safe_stdev(gaps_only))
            if gaps_only else (0.0, 0.0)
        )

        # Pixel-level metrics over *all* chars on the line (so we can
        # later score punctuation if needed) — but stats only on refs.
        sharpness: list[float] = []
        brightness: list[float] = []
        if image is not None:
            for c in line_chars:
                arr = _crop_grayscale(image, c)
                if arr.size:
                    sharpness.append(_laplacian_variance(arr))
                    brightness.append(float(arr.mean()))
                else:
                    sharpness.append(0.0)
                    brightness.append(0.0)
            ref_sharp  = [sharpness[i]  for i, c in enumerate(line_chars)
                          if id(c) in ref_set_ids]
            ref_bright = [brightness[i] for i, c in enumerate(line_chars)
                          if id(c) in ref_set_ids]
            s_mu, s_sd  = statistics.mean(ref_sharp),  _safe_stdev(ref_sharp)
            br_mu, br_sd = statistics.mean(ref_bright), _safe_stdev(ref_bright)
        else:
            s_mu = s_sd = br_mu = br_sd = 0.0

        # Map of right-index -> kerning for fast lookup.
        gap_z_by_right_idx: dict[int, tuple[float, float]] = {}
        for right_idx, g in gap_pairs:
            z = _zscore(g, g_mu, g_sd)
            if z is not None:
                gap_z_by_right_idx[right_idx] = (g, z)

        # Collect all metrics per char first; promote to anomalies only
        # after the consensus rule.
        per_char: list[list[TypographyAnomaly]] = [[] for _ in line_chars]

        for i, c in enumerate(line_chars):
            if not is_ref(c.char):
                continue
            bbox = (c.x, c.y, c.x_end, c.baseline)

            if h_sd > 0.5:
                z = _zscore(float(c.h), h_mu, h_sd)
                if z is not None and abs(z) >= z_threshold:
                    per_char[i].append(TypographyAnomaly(
                        char=c.char, line_index=line_idx, char_index=i,
                        bbox=bbox, metric="height", z_score=z,
                        detail=f"גובה {c.h}px (μ={h_mu:.1f}, σ={h_sd:.1f})",
                    ))

            if b_sd > 0.5:
                z = _zscore(float(c.baseline), b_mu, b_sd)
                if z is not None and abs(z) >= z_threshold:
                    per_char[i].append(TypographyAnomaly(
                        char=c.char, line_index=line_idx, char_index=i,
                        bbox=bbox, metric="baseline", z_score=z,
                        detail=f"baseline {c.baseline}px (μ={b_mu:.1f}, σ={b_sd:.1f})",
                    ))

            if i in gap_z_by_right_idx and g_sd > 1.0:
                gap, z = gap_z_by_right_idx[i]
                if abs(z) >= z_threshold:
                    per_char[i].append(TypographyAnomaly(
                        char=c.char, line_index=line_idx, char_index=i,
                        bbox=bbox, metric="kerning", z_score=z,
                        detail=f"מרווח {gap:.0f}px (μ={g_mu:.1f}, σ={g_sd:.1f})",
                    ))

            if image is not None and s_sd > 0.5:
                z = _zscore(sharpness[i], s_mu, s_sd)
                if z is not None and abs(z) >= z_threshold:
                    per_char[i].append(TypographyAnomaly(
                        char=c.char, line_index=line_idx, char_index=i,
                        bbox=bbox, metric="sharpness", z_score=z,
                        detail=f"חדות (Laplacian var) {sharpness[i]:.1f} (μ={s_mu:.1f})",
                    ))

            if image is not None and br_sd > 0.5:
                z = _zscore(brightness[i], br_mu, br_sd)
                if z is not None and abs(z) >= z_threshold:
                    per_char[i].append(TypographyAnomaly(
                        char=c.char, line_index=line_idx, char_index=i,
                        bbox=bbox, metric="brightness", z_score=z,
                        detail=f"בהירות {brightness[i]:.1f} (μ={br_mu:.1f})",
                    ))

        # Verbose list: keep every metric that fires (for the adjuster's
        # audit trail). Suspicion *score* only counts chars where ≥2
        # metrics agree — that's the signature of a glyph that came
        # from outside the original render (different font/size = breaks
        # height + baseline + sharpness + brightness simultaneously).
        for char_anoms in per_char:
            if char_anoms:
                anomalies.extend(char_anoms)
                if len(char_anoms) >= 2:
                    suspicious_chars += 1

    suspicion_score = min(1.0, suspicious_chars / 2.0)

    return TypographyReport(
        lines_analyzed=lines_analyzed,
        chars_analyzed=chars_analyzed,
        anomalies=anomalies,
        suspicion_score=round(suspicion_score, 3),
    )


# --- public entry point ----------------------------------------------

def analyze_typography(
    image: Optional[Image.Image],
    ocr: Optional[OCRResult] = None,
    *,
    z_threshold: float = 2.0,
) -> TypographyReport:
    """Run the typography consistency check against an image + OCR result.

    Strategy:
      1. Try Tesseract char-level boxes (most accurate).
      2. Fall back to splitting OCR word boxes evenly.
      3. If neither is available, return an empty (clean) report.
    """
    chars: list[CharBox] | None = None
    source = "none"

    if image is not None:
        chars = chars_from_tesseract(image)
        if chars:
            source = "tesseract_chars"

    if not chars and ocr and ocr.lines:
        chars = chars_from_word_boxes(ocr)
        if chars:
            source = "ocr_words_split"

    if not chars:
        return TypographyReport(source="none")

    lines = group_into_lines(chars)
    report = analyze_lines(lines, image=image, z_threshold=z_threshold)
    report.source = source
    return report
