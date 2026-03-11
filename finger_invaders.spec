# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform
import importlib.util
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, collect_all

block_cipher = None

# Platform-specific Leap SDK paths (allow override via LEAP_SDK_PATH)
if platform.system() == "Windows":
    leap_sdk_path = os.environ.get("LEAP_SDK_PATH", "C:/Program Files/Ultraleap/LeapSDK")
    leapc_cffi_path = os.path.join(leap_sdk_path, "leapc_cffi")
    # Correctly define path to LeapC.dll
    leap_dll_path = os.path.join(leap_sdk_path, "lib", "x64")
    name = 'FingerInvaders'
    bundle_name = 'FingerInvaders'
    # Explicitly add the LeapC.dll to the binaries
    binaries = [(os.path.join(leap_dll_path, 'LeapC.dll'), '.')]
else:
    # macOS paths
    leap_sdk_path = os.environ.get(
        "LEAP_SDK_PATH",
        "/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK",
    )
    leapc_cffi_path = os.path.join(leap_sdk_path, "leapc_cffi")
    name = 'FingerInvaders'
    bundle_name = 'FingerInvaders.app'
    # macOS library is typically found via different mechanisms, but can be added if needed
    binaries = []

if not os.path.exists(leap_sdk_path):
    raise SystemExit(
        "Leap SDK not found. Set LEAP_SDK_PATH to the SDK root "
        "(e.g., C:/Program Files/Ultraleap/LeapSDK)."
    )

datas = [
    (leapc_cffi_path, 'leapc_cffi'),
]

# Add data folder if it exists
if os.path.exists('data'):
    datas.append(('data', 'data'))

# Ensure pygame's SDL binaries and data files are bundled
datas += collect_data_files('pygame')
binaries += collect_dynamic_libs('pygame')
hiddenimports = collect_submodules('pygame')

# Ensure Ultraleap Python bindings are bundled when installed via pip.
# Prefer collect_all to include package data, binaries, and hidden imports without importing the module.
try:
    leap_datas, leap_binaries, leap_hidden = collect_all('leap')
    datas += leap_datas
    binaries += leap_binaries
    hiddenimports += leap_hidden
except Exception:
    pass

try:
    cffi_datas, cffi_binaries, cffi_hidden = collect_all('leapc_cffi')
    datas += cffi_datas
    binaries += cffi_binaries
    hiddenimports += cffi_hidden
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[leap_sdk_path],
    # Use the platform-specific binaries list
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'leap',
        'OpenGL',
        'numpy',
        'OpenGL.GL',
        'OpenGL.GLU',
        'cffi',
        '_cffi_backend',
    ] + hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False for GUI app without console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=name,
)
app = BUNDLE(
    coll,
    name=bundle_name,
    icon=None, # Add icon path if available
    bundle_identifier='com.ultraleap.fingerinvaders',
)
