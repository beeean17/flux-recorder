from __future__ import annotations

from pathlib import Path
import shutil
import sys

import ffmpeg

SUPPORTED_FORMATS: tuple[str, ...] = ("mp4", "avi", "mov", "mkv")


def normalize_extension(extension: str) -> str:
    normalized = extension.lower().removeprefix(".")
    if normalized not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {extension}")
    return normalized


def build_output_path(input_path: Path | str, target_extension: str) -> Path:
    source = Path(input_path).expanduser().resolve()
    extension = normalize_extension(target_extension)
    suffix = source.suffix.lower().removeprefix(".")

    if suffix == extension:
        return source.with_name(f"{source.stem}_converted.{extension}")
    return source.with_suffix(f".{extension}")


def convert(input_path: Path | str, output_path: Path | str) -> Path:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_binary = resolve_ffmpeg_binary()

    try:
        (
            ffmpeg
            .input(str(source))
            .output(str(target))
            .overwrite_output()
            .run(cmd=str(ffmpeg_binary), quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else "ffmpeg failed."
        raise RuntimeError(stderr.strip() or "ffmpeg failed.") from exc

    return target


def resolve_ffmpeg_binary() -> Path | str:
    bundled_names = ("ffmpeg.exe", "ffmpeg") if sys.platform.startswith("win") else ("ffmpeg",)

    search_roots: list[Path] = [Path(sys.executable).resolve().parent]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_roots.insert(0, Path(meipass))

    for root in search_roots:
        for binary_name in bundled_names:
            candidate = root / binary_name
            if candidate.exists():
                return candidate

    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary

    raise RuntimeError("ffmpeg binary was not found.")
