from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.image_converter import IMAGE_INPUT_EXTENSIONS, IMAGE_OUTPUT_FORMATS, convert_image
from core.video_converter import VIDEO_INPUT_EXTENSIONS, VIDEO_OUTPUT_FORMATS, convert_video


SUPPORTED_FORMATS: tuple[str, ...] = VIDEO_OUTPUT_FORMATS + IMAGE_OUTPUT_FORMATS
ImageCropRect = tuple[int, int, int, int]


@dataclass(slots=True, frozen=True)
class ConversionRequest:
    mode: str
    source_path: Path
    output_directory: Path
    target_format: str
    image_size: tuple[int, int] | None = None
    image_crop: ImageCropRect | None = None


def convert(
    request: ConversionRequest,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    mode = request.mode.lower().strip()
    source = Path(request.source_path).expanduser().resolve()
    output_directory = Path(request.output_directory).expanduser().resolve()

    if not source.exists():
        raise RuntimeError(f"Source file was not found: {source}")

    if mode == "video":
        target_format = _normalize_extension(request.target_format, VIDEO_OUTPUT_FORMATS)
        output_path = build_output_path(source, target_format, output_directory)
        return convert_video(source, output_path, target_format, progress_callback=progress_callback)

    if mode == "image":
        target_format = _normalize_extension(request.target_format, IMAGE_OUTPUT_FORMATS)
        output_path = build_output_path(source, target_format, output_directory)
        return convert_image(
            source,
            output_path,
            request.image_size,
            request.image_crop,
            progress_callback=progress_callback,
        )

    raise RuntimeError(f"Unsupported conversion mode: {request.mode}")


def build_output_path(
    input_path: Path | str,
    target_extension: str,
    output_directory: Path | str | None = None,
) -> Path:
    source = Path(input_path).expanduser().resolve()
    output_root = source.parent if output_directory is None else Path(output_directory).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    extension = target_extension.lower().removeprefix(".")
    suffix = source.suffix.lower().removeprefix(".")
    filename = f"{source.stem}_converted.{extension}" if suffix == extension else f"{source.stem}.{extension}"
    return output_root / filename


def source_mode_for_path(path: Path | str) -> str | None:
    suffix = Path(path).suffix.lower().removeprefix(".")
    if suffix in VIDEO_INPUT_EXTENSIONS:
        return "video"
    if suffix in IMAGE_INPUT_EXTENSIONS:
        return "image"
    return None


def is_video_path(path: Path | str) -> bool:
    return source_mode_for_path(path) == "video"


def is_image_path(path: Path | str) -> bool:
    return source_mode_for_path(path) == "image"


def _normalize_extension(extension: str, supported_formats: tuple[str, ...]) -> str:
    normalized = extension.lower().removeprefix(".")
    if normalized not in supported_formats:
        raise ValueError(f"Unsupported format: {extension}")
    return normalized
