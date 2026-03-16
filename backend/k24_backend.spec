
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect hidden imports
hidden_imports = []
# Critical uvicorn imports that PyInstaller often misses
hidden_imports += [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # FastAPI / Starlette
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    # App modules
    'difflib',
    'sqlite3',
    'xml.etree.ElementTree',
    # Data
    'pandas',
    'langchain',
    'langchain_core',
    'langchain_community',
    # Supabase
    'supabase',
    'gotrue',
    'postgrest',
    'realtime',
    'storage3',
    # Pydantic
    'pydantic',
    'pydantic.deprecated',
    'pydantic.v1',
    # Email / reporting
    'reportlab',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
]
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
hidden_imports += collect_submodules('backend.middleware')
hidden_imports += collect_submodules('backend.ai_engine')
hidden_imports += collect_submodules('backend.extraction')
hidden_imports += collect_submodules('backend.classification')
hidden_imports += collect_submodules('backend.gemini')

# Data files to bundle
datas = [
    ('.env', '.'),
    ('config/cloud.json', 'config'),  # Bundle config file
]

a = Analysis(
    ['desktop_main.py'],  # Correct entry point for desktop backend
    pathex=[],
    binaries=[],
    datas=datas, 
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'notebook',
        'IPython',
        'pytest',
        'tkinter',
        '_tkinter',
    ],
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
