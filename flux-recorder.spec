# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


# PyInstaller exposes SPECPATH as the directory containing this spec file.
project_root = Path(SPECPATH).resolve()
assets_dir = project_root / "assets"

datas = []
if assets_dir.exists():
    datas.append((str(assets_dir), "assets"))

windows_icon = assets_dir / "app.ico"
mac_icon = assets_dir / "app.icns"
bundle_identifier = os.environ.get("FLUX_RECORDER_BUNDLE_ID", "com.yoon.fluxrecorder")
mac_info_plist = {
    "CFBundleDisplayName": "flux-recorder",
    "CFBundleName": "flux-recorder",
    "CFBundleIdentifier": bundle_identifier,
    "NSCameraUsageDescription": "flux-recorder needs camera access for webcam preview and recording.",
    "NSMicrophoneUsageDescription": "flux-recorder needs microphone access for audio capture.",
}

exe_icon = None
bundle_icon = None
if sys.platform == "win32" and windows_icon.exists():
    exe_icon = str(windows_icon)
elif sys.platform == "darwin" and mac_icon.exists():
    exe_icon = str(mac_icon)
    bundle_icon = str(mac_icon)


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if sys.platform == "win32":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="flux-recorder",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=exe_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="flux-recorder",
    )
elif sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="flux-recorder",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=exe_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="flux-recorder",
    )
    app = BUNDLE(
        coll,
        name="flux-recorder.app",
        icon=bundle_icon,
        bundle_identifier=bundle_identifier,
        info_plist=mac_info_plist,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="flux-recorder",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=exe_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="flux-recorder",
    )
