#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_EXE="${PROJECT_ROOT}/.venv/bin/python"
PYINSTALLER_CONFIG_DIR="${PROJECT_ROOT}/.pyinstaller"

if [[ ! -x "${PYTHON_EXE}" ]]; then
  PYTHON_EXE="python3"
elif ! "${PYTHON_EXE}" -m PyInstaller --version >/dev/null 2>&1; then
  PYTHON_EXE="python3"
fi

cd "${PROJECT_ROOT}"
mkdir -p "${PYINSTALLER_CONFIG_DIR}"
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR}" "${PYTHON_EXE}" -m PyInstaller --noconfirm --clean flux-recorder.spec
