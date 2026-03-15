# flux-recorder

Desktop media toolkit built with `PyQt6` and `OpenCV`.

It currently includes:
- Webcam recording
- Screen recording
- Image and video conversion

## Requirements

- Python 3.11+
- Windows recommended for the current screen capture workflow

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Package With PyInstaller

Build on each target OS separately.

- Windows build on Windows
- macOS build on macOS

Install PyInstaller first:

```bash
pip install pyinstaller
```

Windows:

```bash
build\build_windows.bat
```

macOS:

```bash
bash build/build_mac.sh
```

Output is created in `dist/flux-recorder/`.

Notes:

- The project uses `flux-recorder.spec` for packaging.
- `assets/` is bundled automatically.
- Windows app icon uses `assets/app.ico`.
- macOS app icon uses `assets/app.icns` if you add one. If no `.icns` file is present, the app still builds without a custom macOS icon.

## Core Stack

- `PyQt6` for the desktop UI
- `OpenCV` for webcam capture, video writing, and core media handling
- `NumPy` for frame data handling
- `Pillow` for some image format conversion tasks

## Window Capture Notes

`Window` capture is not equally reliable for every kind of app.

- Normal desktop windows such as File Explorer, Notepad, and many standard app windows usually work well.
- Hardware-accelerated windows such as Chrome, games, and some media players may show a black frame, a frozen old frame, or stale content.
- This happens because many GPU-rendered windows do not expose their latest real-time contents correctly through traditional `HWND` capture paths such as `grabWindow` or `PrintWindow`.

## Recommended Workarounds

- For Chrome, try disabling hardware acceleration if `Window` capture appears black.
- For games or GPU-heavy apps, prefer `Full Screen` or `Custom` capture instead of `Window` capture.
- If strict per-window capture is required for games or accelerated apps, a different Windows-specific capture backend such as `Windows Graphics Capture` is needed.

## Current Limitations

- Screen recording currently uses `OpenCV` for video output and does not fully support audio recording in the current path.
- `Window` capture does not support resizing the selected window while recording.
- Some accelerated windows may still fail even when selected correctly.
