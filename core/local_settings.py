from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    language: str = "en"
    webcam_output_directory: Path | None = None
    screen_output_directory: Path | None = None
    converter_output_directory: Path | None = None
    converter_source_directory: Path | None = None
    converter_video_source: Path | None = None
    converter_image_source: Path | None = None


def load_app_settings() -> AppSettings:
    settings_path = _settings_path()
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return AppSettings()

    return AppSettings(
        language=_normalize_language(payload.get("language")),
        webcam_output_directory=_optional_path(payload.get("webcam_output_directory")),
        screen_output_directory=_optional_path(payload.get("screen_output_directory")),
        converter_output_directory=_optional_path(payload.get("converter_output_directory")),
        converter_source_directory=_optional_path(payload.get("converter_source_directory")),
        converter_video_source=_optional_path(payload.get("converter_video_source")),
        converter_image_source=_optional_path(payload.get("converter_image_source")),
    )


def save_app_settings(settings: AppSettings) -> None:
    settings_path = _settings_path()
    payload = {
        "language": _normalize_language(settings.language),
        "webcam_output_directory": _string_path(settings.webcam_output_directory),
        "screen_output_directory": _string_path(settings.screen_output_directory),
        "converter_output_directory": _string_path(settings.converter_output_directory),
        "converter_source_directory": _string_path(settings.converter_source_directory),
        "converter_video_source": _string_path(settings.converter_video_source),
        "converter_image_source": _string_path(settings.converter_image_source),
    }
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except OSError:
        return


def _settings_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return project_root / ".flux-recorder" / "settings.json"


def _normalize_language(value: object) -> str:
    if value in ("en", "ko"):
        return str(value)
    return "en"


def _optional_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()


def _string_path(value: Path | None) -> str | None:
    if value is None:
        return None
    return str(value)
