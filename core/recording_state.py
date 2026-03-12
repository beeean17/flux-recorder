from __future__ import annotations

from typing import Literal

RecordingState = Literal["idle", "starting", "recording", "paused"]

IDLE: RecordingState = "idle"
STARTING: RecordingState = "starting"
RECORDING: RecordingState = "recording"
PAUSED: RecordingState = "paused"
