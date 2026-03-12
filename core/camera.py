from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

DEFAULT_CAMERA_FPS = 30.0
COMMON_CAMERA_FPS = (15.0, 23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)


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
            return DEFAULT_CAMERA_FPS

        fps = float(self._capture.get(cv2.CAP_PROP_FPS))
        return self._normalize_fps(fps)

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _normalize_fps(self, fps: float) -> float:
        if fps <= 0 or fps > 120:
            return DEFAULT_CAMERA_FPS

        nearest_common_fps = min(COMMON_CAMERA_FPS, key=lambda candidate: abs(candidate - fps))
        if abs(nearest_common_fps - fps) / nearest_common_fps <= 0.12:
            return nearest_common_fps

        return round(fps, 2)


def bgr_to_rgb(frame_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
