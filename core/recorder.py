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

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(normalized_path), fourcc, fps, size)
        if not writer.isOpened():
            writer.release()
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
