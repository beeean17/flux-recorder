from __future__ import annotations

from collections import deque
from pathlib import Path
from threading import Lock
from time import perf_counter, sleep

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.camera import CameraCapture, CameraError, bgr_to_rgb
from core.recorder import Recorder
from core.recording_state import IDLE, PAUSED, RECORDING, STARTING, RecordingState

FRAME_INTERVAL_WINDOW = 120
MIN_RECORDING_FPS = 5.0
MAX_RECORDING_FPS = 60.0


class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    camera_error = pyqtSignal(str)
    recording_changed = pyqtSignal(str, str)

    def __init__(self, device_index: int = 0) -> None:
        super().__init__()
        self._camera = CameraCapture(device_index=device_index)
        self._recorder = Recorder()
        self._running = False
        self._lock = Lock()
        self._pending_recording_path: Path | None = None
        self._is_paused = False
        self._frame_intervals: deque[float] = deque(maxlen=FRAME_INTERVAL_WINDOW)
        self._last_frame_timestamp: float | None = None

    @property
    def recording_state(self) -> RecordingState:
        with self._lock:
            if self._pending_recording_path is not None:
                return STARTING
            if not self._recorder.is_recording:
                return IDLE
            if self._is_paused:
                return PAUSED
            return RECORDING

    @property
    def is_recording(self) -> bool:
        return self.recording_state != IDLE

    def start_recording(self, output_path: Path) -> None:
        with self._lock:
            if self._pending_recording_path is not None or self._recorder.is_recording:
                return
            self._pending_recording_path = output_path.expanduser()
            self._is_paused = False

        self.recording_changed.emit(STARTING, f"Preparing recording: {output_path.name}")

    def pause_recording(self) -> None:
        with self._lock:
            if not self._recorder.is_recording or self._is_paused:
                return
            self._is_paused = True
            output_path = self._recorder.output_path

        message = f"Recording paused: {output_path}" if output_path is not None else "Recording paused."
        self.recording_changed.emit(PAUSED, message)

    def resume_recording(self) -> None:
        with self._lock:
            if not self._recorder.is_recording or not self._is_paused:
                return
            self._is_paused = False
            output_path = self._recorder.output_path

        message = f"Recording to {output_path}" if output_path is not None else "Recording resumed."
        self.recording_changed.emit(RECORDING, message)

    def stop_recording(self) -> Path | None:
        with self._lock:
            was_starting = self._pending_recording_path is not None
            self._pending_recording_path = None
            self._is_paused = False
            saved_path = self._recorder.stop()

        if saved_path is not None:
            self.recording_changed.emit(IDLE, f"Saved recording to {saved_path}")
        elif was_starting:
            self.recording_changed.emit(IDLE, "Recording cancelled.")
        else:
            self.recording_changed.emit(IDLE, "Recording stopped.")
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

                timestamp = perf_counter()
                self._observe_frame_timestamp(timestamp)

                self._start_recorder_if_needed(camera_frame.fps, camera_frame.size)
                if self.recording_state == RECORDING:
                    self._recorder.write(camera_frame.frame_bgr)

                self.frame_ready.emit(bgr_to_rgb(camera_frame.frame_bgr))
                sleep(0.001)
        finally:
            saved_path = self._recorder.stop()
            if saved_path is not None:
                self.recording_changed.emit(IDLE, f"Saved recording to {saved_path}")
            self._camera.release()

    def _start_recorder_if_needed(self, fps: float, size: tuple[int, int]) -> None:
        with self._lock:
            if self._pending_recording_path is None or self._recorder.is_recording:
                return

            output_path = self._pending_recording_path
            self._pending_recording_path = None

        recording_fps = self._estimated_capture_fps(fps)

        try:
            self._recorder.start(output_path=output_path, fps=recording_fps, size=size)
        except RuntimeError as exc:
            self.camera_error.emit(str(exc))
            return

        self.recording_changed.emit(RECORDING, f"Recording to {output_path}")

    def _observe_frame_timestamp(self, timestamp: float) -> None:
        if self._last_frame_timestamp is not None:
            interval = timestamp - self._last_frame_timestamp
            if interval > 0:
                self._frame_intervals.append(interval)
        self._last_frame_timestamp = timestamp

    def _estimated_capture_fps(self, fallback_fps: float) -> float:
        if not self._frame_intervals:
            return fallback_fps

        sorted_intervals = sorted(self._frame_intervals)
        trim = max(1, len(sorted_intervals) // 10) if len(sorted_intervals) >= 10 else 0
        stable_intervals = sorted_intervals[trim:-trim] if trim else sorted_intervals
        average_interval = sum(stable_intervals) / len(stable_intervals)
        if average_interval <= 0:
            return fallback_fps

        measured_fps = 1.0 / average_interval
        return max(MIN_RECORDING_FPS, min(MAX_RECORDING_FPS, round(measured_fps, 2)))
