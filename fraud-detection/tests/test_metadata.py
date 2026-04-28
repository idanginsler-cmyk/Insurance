from PIL import Image

from fraud_detection.config import Config
from fraud_detection.forensics.metadata import extract_metadata
from fraud_detection.ingestion.loader import Document


def _doc(image: Image.Image) -> Document:
    import io, hashlib
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    data = buf.getvalue()
    return Document(
        file_path=None,  # type: ignore[arg-type]
        file_bytes=data,
        file_type="image",
        sha256=hashlib.sha256(data).hexdigest(),
        image=image,
    )


def test_image_without_exif_is_flagged():
    img = Image.new("RGB", (50, 50), "white")
    rep = extract_metadata(_doc(img), Config())
    assert rep.has_exif is False
    assert "no_exif" in rep.suspicions


def test_image_with_unknown_software_is_flagged_unknown():
    img = Image.new("RGB", (50, 50), "white")
    exif = img.getexif()
    exif[305] = "RandomEditor 1.0"  # 305 = Software
    img.info["exif"] = exif.tobytes()
    rep = extract_metadata(_doc(img), Config())
    # Either unknown_producer or has the software but isn't whitelisted.
    assert any("unknown_producer" in s or "suspect_producer" in s for s in rep.suspicions)
