from __future__ import annotations

from pathlib import Path
from typing import Callable

import cv2


VIDEO_OUTPUT_FORMATS: tuple[str, ...] = ("mp4", "avi")
VIDEO_INPUT_EXTENSIONS: tuple[str, ...] = ("mp4", "avi", "mov", "mkv", "m4v", "wmv", "webm")


def convert_video(
    source: Path,
    output_path: Path,
    target_format: str,
    progress_callback: Callable[[int], None] | None = None,
) -> Path:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Unable to open video source: {source}")

    ok, first_frame = capture.read()
    if not ok or first_frame is None:
        capture.release()
        raise RuntimeError("Unable to read frames from the selected video.")

    height, width = first_frame.shape[:2]
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if fps <= 1.0 or fps > 240.0:
        fps = 30.0
    total_frames = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    last_progress = -1

    def emit_progress(frame_index: int) -> None:
        nonlocal last_progress
        if progress_callback is None:
            return
        if total_frames > 0:
            progress = max(0, min(100, int((frame_index / total_frames) * 100)))
        else:
            progress = min(95, 5 + frame_index // 30)
        if progress != last_progress:
            progress_callback(progress)
            last_progress = progress

    writer = _open_video_writer(output_path, target_format, fps, (width, height))
    try:
        if progress_callback is not None:
            progress_callback(0)
        writer.write(first_frame)
        written_frames = 1
        emit_progress(written_frames)
        while True:
            ok, frame_bgr = capture.read()
            if not ok or frame_bgr is None:
                break
            if frame_bgr.shape[1] != width or frame_bgr.shape[0] != height:
                frame_bgr = cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_AREA)
            writer.write(frame_bgr)
            written_frames += 1
            emit_progress(written_frames)
    finally:
        capture.release()
        writer.release()

    if progress_callback is not None:
        progress_callback(100)
    return output_path


def _open_video_writer(
    output_path: Path,
    target_format: str,
    fps: float,
    size: tuple[int, int],
):
    for fourcc_code in _video_fourcc_candidates(target_format):
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*fourcc_code), fps, size)
        if writer.isOpened():
            return writer
        writer.release()

    raise RuntimeError(f"Unable to open a {target_format.upper()} video writer for {output_path.name}.")


def _video_fourcc_candidates(target_format: str) -> tuple[str, ...]:
    if target_format == "mp4":
        return ("mp4v", "avc1")
    return ("XVID", "MJPG")
