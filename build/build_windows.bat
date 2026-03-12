pyinstaller --onefile --windowed ^
  --name flux-recorder ^
  --add-binary "ffmpeg.exe;." ^
  main.py
