# -*- mode: python ; coding: utf-8 -*-
import os
import platform
from project_info import VERSION as version

# Set output name based on system type
system = platform.system().lower()
if system == "windows":
    os_type = "windows"
elif system == "linux":
    os_type = "linux"
else:  # Darwin
    os_type = "mac"

output_name = f"CursorFreeVIP_{version}_{os_type}"

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('locales', 'locales'),
        ('quit_cursor.py', '.'),
        ('utils.py', '.'),
        ('pyproject.toml', '.')  # Include pyproject.toml instead of .env
    ],
    hiddenimports=[
        'quit_cursor',
        'utils',
        'project_info'  # Add project_info to hiddenimports
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

target_arch = os.environ.get('TARGET_ARCH', None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=output_name,  # 使用动态生成的名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,  # 对非Mac平台无影响
    target_arch=target_arch,  # 仅在需要时通过环境变量指定
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)