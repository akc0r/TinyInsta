"""Image processing — thumbnail + display variants (Pillow)."""

from __future__ import annotations

import io

import storage
from PIL import Image, ImageOps

# Longest-edge caps for each variant (px).
SIZES = {"thumb": 320, "display": 1080}
JPEG_QUALITY = 85


def _resize_jpeg(img: Image.Image, max_edge: int) -> bytes:
    out = img.copy()
    out.thumbnail((max_edge, max_edge))  # keeps aspect ratio, never upscales
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def process(original_url: str) -> dict[str, str]:
    object_key = storage.key_from_url(original_url)
    img = Image.open(io.BytesIO(storage.download(object_key)))
    img = ImageOps.exif_transpose(img)  # honour camera orientation
    if img.mode != "RGB":
        img = img.convert("RGB")  # flatten alpha / palette for JPEG

    variants: dict[str, str] = {}
    for name, max_edge in SIZES.items():
        data = _resize_jpeg(img, max_edge)
        variants[name] = storage.upload(
            f"{object_key}/{name}.jpg", data, "image/jpeg"
        )
    return variants
