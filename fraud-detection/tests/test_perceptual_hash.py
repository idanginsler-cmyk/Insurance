from fraud_detection.forensics.perceptual_hash import compute_hashes, hamming_distance
from .conftest import render_receipt


def test_identical_images_have_zero_distance():
    img = render_receipt(["מרפאת ד\"ר כהן", "סה\"כ: 600 ש\"ח"], seed=1)
    h1 = compute_hashes(img)
    h2 = compute_hashes(img.copy())
    assert hamming_distance(h1.phash, h2.phash) == 0
    assert hamming_distance(h1.dhash, h2.dhash) == 0


def test_different_images_have_nonzero_distance():
    a = render_receipt(["receipt A"], seed=1)
    b = render_receipt(["receipt B totally different content"], seed=42)
    h_a = compute_hashes(a)
    h_b = compute_hashes(b)
    assert hamming_distance(h_a.phash, h_b.phash) > 0


def test_hash_format_is_hex_string():
    img = render_receipt(["x"], seed=1)
    h = compute_hashes(img)
    assert isinstance(h.phash, str)
    assert all(c in "0123456789abcdef" for c in h.phash)
    assert len(h.phash) == 16  # 64-bit hex
