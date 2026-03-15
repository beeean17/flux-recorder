from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image


IMAGE_OUTPUT_FORMATS: tuple[str, ...] = ("png", "jpg", "bmp", "ico")
IMAGE_INPUT_EXTENSIONS: tuple[str, ...] = ("png", "jpg", "jpeg", "bmp", "webp", "ico")
DEFAULT_IMAGE_SIZE_OPTIONS: tuple[tuple[str, tuple[int, int] | None], ...] = (
    ("Original size", None),
    ("1920 x 1080", (1920, 1080)),
    ("1280 x 720", (1280, 720)),
    ("1080 x 1080", (1080, 1080)),
    ("512 x 512", (512, 512)),
    ("256 x 256", (256, 256)),
    ("800 x 800", (800, 800)),
)


def convert_image(
    source: Path,
    output_path: Path,
    image_size: tuple[int, int] | None,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    if progress_callback is not None:
        progress_callback(10)
    try:
        image = Image.open(source)
    except OSError as exc:
        raise RuntimeError(f"Unable to open image source: {source}") from exc

    if progress_callback is not None:
        progress_callback(40)
    if image_size is not None:
        width, height = image_size
        if width <= 0 or height <= 0:
            raise RuntimeError("Image size must use positive width and height values.")
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    if progress_callback is not None:
        progress_callback(75)
    target_format = output_path.suffix.lower().removeprefix(".")
    image = _normalize_image_mode(image, target_format)
    save_kwargs = _image_save_kwargs(target_format)
    try:
        image.save(output_path, **save_kwargs)
    except OSError as exc:
        raise RuntimeError(f"Unable to save converted image to {output_path}") from exc
    if progress_callback is not None:
        progress_callback(100)
    return output_path


def image_size_option_for_label(label: str) -> tuple[int, int] | None:
    for option_label, option_size in DEFAULT_IMAGE_SIZE_OPTIONS:
        if option_label == label:
            return option_size
    return None


def _normalize_image_mode(image: Image.Image, target_format: str) -> Image.Image:
    if target_format == "jpg":
        return image.convert("RGB")
    if target_format == "ico":
        return image.convert("RGBA")
    if image.mode in ("RGBA", "RGB", "L"):
        return image
    return image.convert("RGBA")


def _image_save_kwargs(target_format: str) -> dict:
    if target_format == "jpg":
        return {"format": "JPEG", "quality": 95}
    if target_format == "png":
        return {"format": "PNG", "compress_level": 3}
    if target_format == "bmp":
        return {"format": "BMP"}
    if target_format == "ico":
        return {"format": "ICO"}
    raise RuntimeError(f"Unsupported image format: {target_format}")
