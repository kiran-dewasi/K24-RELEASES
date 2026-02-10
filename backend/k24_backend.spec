
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect hidden imports
hidden_imports = []
hidden_imports += collect_submodules('uvicorn')
hidden_imports += collect_submodules('fastapi')
hidden_imports += collect_submodules('sqlalchemy')
hidden_imports += collect_submodules('pydantic')
hidden_imports += collect_submodules('reportlab')
hidden_imports += collect_submodules('jose')
hidden_imports += collect_submodules('bcrypt')
hidden_imports += ["python-multipart", "pandas", "tenacity", "requests"]
hidden_imports += collect_submodules('google.generativeai')
hidden_imports += collect_submodules('backend.routers')
hidden_imports += collect_submodules('backend.services')
hidden_imports += collect_submodules('backend.database')
hidden_imports += collect_submodules('backend.compliance')
hidden_imports += collect_submodules('backend.tools')
hidden_imports += collect_submodules('backend.orchestration')

a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=[],
    datas=[], 
    hiddenimports=hidden_imports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='k24-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
