from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import sleep

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.camera import CameraCapture, CameraError, bgr_to_rgb
from core.recorder import Recorder


class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    camera_error = pyqtSignal(str)
    recording_changed = pyqtSignal(bool, str)

    def __init__(self, device_index: int = 0) -> None:
        super().__init__()
        self._camera = CameraCapture(device_index=device_index)
        self._recorder = Recorder()
        self._running = False
        self._lock = Lock()
        self._pending_recording_path: Path | None = None

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recorder.is_recording or self._pending_recording_path is not None

    def start_recording(self, output_path: Path) -> None:
        with self._lock:
            self._pending_recording_path = output_path.expanduser()

    def stop_recording(self) -> Path | None:
        with self._lock:
            self._pending_recording_path = None
            saved_path = self._recorder.stop()

        if saved_path is not None:
            self.recording_changed.emit(False, f"Saved recording to {saved_path}")
        else:
            self.recording_changed.emit(False, "Recording stopped.")
        return saved_path

    def stop(self) -> None:
        self._running = False
        self.wait()

    def run(self) -> None:
        try:
            self._camera.open()
        except CameraError as exc:
            self.camera_error.emit(str(exc))
            return

        self._running = True
        try:
            while self._running:
                try:
                    camera_frame = self._camera.read()
                except CameraError as exc:
                    self.camera_error.emit(str(exc))
                    break

                self._start_recorder_if_needed(camera_frame.fps, camera_frame.size)
                if self._recorder.is_recording:
                    self._recorder.write(camera_frame.frame_bgr)

                self.frame_ready.emit(bgr_to_rgb(camera_frame.frame_bgr))
                sleep(0.001)
        finally:
            saved_path = self._recorder.stop()
            if saved_path is not None:
                self.recording_changed.emit(False, f"Saved recording to {saved_path}")
            self._camera.release()

    def _start_recorder_if_needed(self, fps: float, size: tuple[int, int]) -> None:
        with self._lock:
            if self._pending_recording_path is None or self._recorder.is_recording:
                return

            output_path = self._pending_recording_path
            self._pending_recording_path = None

        try:
            self._recorder.start(output_path=output_path, fps=fps, size=size)
        except RuntimeError as exc:
            self.camera_error.emit(str(exc))
            return

        self.recording_changed.emit(True, f"Recording to {output_path}")
