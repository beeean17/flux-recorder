from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class Recorder:
    def __init__(self) -> None:
        self._writer: cv2.VideoWriter | None = None
        self._output_path: Path | None = None

    @property
    def is_recording(self) -> bool:
        return self._writer is not None and self._writer.isOpened()

    @property
    def output_path(self) -> Path | None:
        return self._output_path

    def start(self, output_path: Path | str, fps: float, size: tuple[int, int]) -> None:
        normalized_path = Path(output_path).expanduser()
        normalized_path.parent.mkdir(parents=True, exist_ok=True)

        writer = self._open_writer(normalized_path, fps, size)
        if writer is None:
            raise RuntimeError(f"Unable to open video writer for {normalized_path}.")

        self.stop()
        self._writer = writer
        self._output_path = normalized_path

    def write(self, frame_bgr: np.ndarray) -> None:
        if self._writer is not None and self._writer.isOpened():
            self._writer.write(frame_bgr)

    def stop(self) -> Path | None:
        output_path = self._output_path
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self._output_path = None
        return output_path

    def _open_writer(self, output_path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
        suffix = output_path.suffix.lower()
        fourcc_candidates = self._fourcc_candidates(suffix)

        for fourcc_code in fourcc_candidates:
            writer = cv2.VideoWriter(
                str(output_path),
                cv2.VideoWriter_fourcc(*fourcc_code),
                fps,
                size,
            )
            if writer.isOpened():
                return writer
            writer.release()

        return None

    def _fourcc_candidates(self, suffix: str) -> tuple[str, ...]:
        if suffix == ".mp4":
            return ("mp4v", "avc1", "H264")
        if suffix == ".avi":
            return ("XVID", "MJPG")
        return ("mp4v", "XVID", "MJPG")
