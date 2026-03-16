@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "PYINSTALLER_CONFIG_DIR=%PROJECT_ROOT%\.pyinstaller"

if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
  "%PROJECT_ROOT%\.venv\Scripts\python.exe" -m PyInstaller --version >nul 2>&1
  if errorlevel 1 (
    set "PYTHON_EXE=python"
  )
)

pushd "%PROJECT_ROOT%"
if not exist "%PYINSTALLER_CONFIG_DIR%" mkdir "%PYINSTALLER_CONFIG_DIR%"
set "PYINSTALLER_CONFIG_DIR=%PYINSTALLER_CONFIG_DIR%"
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean flux-recorder.spec
if errorlevel 1 (
  popd
  exit /b %errorlevel%
)
popd
