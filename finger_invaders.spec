# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None
name = "FingerInvaders"
bundle_name = "FingerInvaders.app"
binaries = []
datas = []

if os.path.exists("data"):
    datas.append(("data", "data"))
if os.path.exists("models"):
    datas.append(("models", "models"))

datas += collect_data_files("pygame")
datas += collect_data_files("mediapipe")
binaries += collect_dynamic_libs("pygame")
binaries += collect_dynamic_libs("mediapipe")
hiddenimports = collect_submodules("pygame") + collect_submodules("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=["OpenGL", "numpy", "OpenGL.GL", "OpenGL.GLU"] + hiddenimports,
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
    console=True,
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
    icon=None,
    bundle_identifier="com.fingerinvaders.mediapipe",
)
