from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


class CameraError(RuntimeError):
    """카메라 초기화 또는 프레임 읽기 오류."""


@dataclass(slots=True)
class CameraFrame:
    frame_bgr: np.ndarray
    fps: float
    size: tuple[int, int]


class CameraCapture:
    def __init__(self, device_index: int = 0) -> None:
        self._device_index = device_index
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._capture = cv2.VideoCapture(self._device_index)
        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            raise CameraError(f"Unable to open camera device {self._device_index}.")

    def is_opened(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    def read(self) -> CameraFrame:
        if self._capture is None:
            raise CameraError("Camera device is not opened.")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise CameraError("Failed to read a frame from the camera.")

        height, width = frame.shape[:2]
        return CameraFrame(
            frame_bgr=frame,
            fps=self.fps,
            size=(width, height),
        )

    @property
    def fps(self) -> float:
        if self._capture is None:
            return 30.0

        fps = float(self._capture.get(cv2.CAP_PROP_FPS))
        return fps if fps > 0 else 30.0

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


def bgr_to_rgb(frame_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
