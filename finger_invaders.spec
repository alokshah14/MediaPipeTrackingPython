# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import platform

block_cipher = None

# Platform-specific Leap SDK paths
if platform.system() == "Windows":
    leap_sdk_path = "C:/Program Files/Ultraleap/LeapSDK"
    leapc_cffi_path = os.path.join(leap_sdk_path, "leapc_cffi")
    name = 'FingerInvaders'
    bundle_name = 'FingerInvaders'
else:
    # macOS paths
    leap_sdk_path = "/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK"
    leapc_cffi_path = os.path.join(leap_sdk_path, "leapc_cffi")
    name = 'FingerInvaders'
    bundle_name = 'FingerInvaders.app'

datas = [
    (leapc_cffi_path, 'leapc_cffi'),
]

# Add data folder if it exists
if os.path.exists('data'):
    datas.append(('data', 'data'))

a = Analysis(
    ['main.py'],
    pathex=[leap_sdk_path],
    binaries=[],
    datas=datas,
    hiddenimports=['leap', 'pygame', 'OpenGL', 'numpy', 'OpenGL.GL', 'OpenGL.GLU', 'cffi', '_cffi_backend'],
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
