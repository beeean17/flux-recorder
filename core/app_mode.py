from __future__ import annotations

from typing import Literal

AppMode = Literal["dashboard", "webcam", "screen", "convert"]

DASHBOARD_MODE: AppMode = "dashboard"
WEBCAM_MODE: AppMode = "webcam"
SCREEN_MODE: AppMode = "screen"
CONVERT_MODE: AppMode = "convert"
