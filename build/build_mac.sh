#!/usr/bin/env bash

pyinstaller --onefile --windowed \
  --name flux-recorder \
  --add-binary "/usr/local/bin/ffmpeg:." \
  main.py
