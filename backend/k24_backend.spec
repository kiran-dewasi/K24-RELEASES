
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ─────────────────────────────────────────────────────────────
# IMPORTANT: desktop_main.py lives inside backend/.
# PyInstaller's cwd is backend/, so pathex must point there
# explicitly so that all root-level local modules resolve.
# ─────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.abspath(
    os.path.join(SPECPATH)   # SPECPATH == directory containing this .spec file == backend/
)

# CRITICAL: insert BACKEND_DIR into sys.path NOW so collect_submodules()
# can actually find and walk services/, routers/, database/, etc.
# Without this, collect_submodules returns [] silently and the exe crashes
# with ModuleNotFoundError at runtime.
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ─────────────────────────────────────────────────────────────
# ROOT-LEVEL LOCAL MODULES  (files that live directly in
# backend/ and are imported without a package prefix, e.g.
#   from tally_connector import TallyConnector
#   from loader import LedgerLoader
#   from api import app
# )
# Every .py file at the root of backend/ that is imported
# must be listed here so PyInstaller bundles it.
# ─────────────────────────────────────────────────────────────
ROOT_LOCAL_MODULES = [
    'tally_connector',
    'tally_engine',
    'tally_reader',
    'tally_xml_builder',
    'tally_golden_xml',
    'tally_live_update',
    'tally_response_parser',
    'tally_search',
    'tally_preflight',
    'tally_diagnostics',
    'loader',
    'api',
    'auth',
    'crud',
    'logic',
    'agent',
    'agent_gemini',
    'agent_intent',
    'agent_orchestrator_v2',
    'agent_error_handler',
    'agent_errors',
    'agent_response',
    'agent_state',
    'agent_system',
    'agent_transaction',
    'agent_validator',
    'agent_intent_fixed',
    'audit_engine',
    'background_jobs',
    'context_manager',
    'dependencies',
    'entity_extractor',
    'graph',
    'intent_recognizer',
    'ledger_matcher',
    'memory',
    'orchestrator',
    'self_healing',
    'session_store',
    'sync_engine',
    'whatsapp_security',
    'xml_generator',
]

# ─────────────────────────────────────────────────────────────
# HIDDEN IMPORTS — third-party + sub-packages
# ─────────────────────────────────────────────────────────────
hidden_imports = []

# Root-level local modules (MUST come first)
hidden_imports += ROOT_LOCAL_MODULES

# uvicorn — PyInstaller misses many of these
hidden_imports += [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.config',
    'uvicorn.main',
]
hidden_imports += collect_submodules('uvicorn')

# FastAPI / Starlette
hidden_imports += [
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.middleware.base',
    'starlette.responses',
    'starlette.requests',
    'starlette.background',
    'starlette.staticfiles',
    'starlette.testclient',
    'anyio',
    'anyio._backends._asyncio',
]
hidden_imports += collect_submodules('fastapi')

# Pydantic
hidden_imports += [
    'pydantic',
    'pydantic.deprecated',
    'pydantic.v1',
]
hidden_imports += collect_submodules('pydantic')

# SQLAlchemy
hidden_imports += collect_submodules('sqlalchemy')

# Auth / crypto
hidden_imports += collect_submodules('jose')
hidden_imports += collect_submodules('bcrypt')
hidden_imports += ['passlib', 'passlib.handlers', 'passlib.handlers.bcrypt']
hidden_imports += collect_submodules('passlib')

# Standard library gaps
hidden_imports += [
    'sqlite3',
    'difflib',
    'xml.etree.ElementTree',
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'multiprocessing.freeze_support',
    '_multiprocessing',
]

# Data / ML
hidden_imports += [
    'pandas',
    'numpy',
    'openpyxl',
]

# Reporting
hidden_imports += [
    'reportlab',
]
hidden_imports += collect_submodules('reportlab')

# Supabase
hidden_imports += [
    'supabase',
    'gotrue',
    'postgrest',
    'realtime',
    'storage3',
    'httpx',
    'httpcore',
]
hidden_imports += collect_submodules('supabase')

# Requests / networking
hidden_imports += [
    'requests',
    'certifi',
    'charset_normalizer',
    'urllib3',
    'multipart',
]

# Google AI / LangChain
hidden_imports += collect_submodules('google.generativeai')
hidden_imports += collect_submodules('langchain')
hidden_imports += collect_submodules('langchain_core')
hidden_imports += collect_submodules('langchain_community')

# Misc
hidden_imports += ['tenacity', 'python_multipart']

# ─── Backend sub-packages ─────────────────────────────────────
# Since pathex points to BACKEND_DIR, these are importable as
# top-level names (e.g. `from routers.auth import router`)
# collect_submodules() now works because sys.path was patched above.
# Explicit lists below are a bulletproof belt-and-suspenders fallback —
# they guarantee every known module is included even if collect_submodules
# somehow returns [] (e.g. __init__.py missing, import error in module).

# services/ — explicit list
hidden_imports += [
    'services',
    'services.auto_executor',
    'services.bulk_processor',
    'services.canonical_export_engine',
    'services.cloud_backup',
    'services.confidence_scorer',
    'services.config_service',
    'services.export_service',
    'services.item_normalizer',
    'services.key_manager',
    'services.ledger_service',
    'services.license_service',
    'services.query_orchestrator',
    'services.supabase_service',
    'services.tally_sync_checkpoint',
    'services.tally_sync_service',
    'services.tenant_service',
    'services.whatsapp_poller',
]
hidden_imports += collect_submodules('services')

# routers/ — explicit list
hidden_imports += [
    'routers',
    'routers.admin',
    'routers.agent',
    'routers.auth',
    'routers.baileys',
    'routers.bills',
    'routers.compliance',
    'routers.contacts',
    'routers.customers',
    'routers.dashboard',
    'routers.data_utils',
    'routers.debug',
    'routers.devices',
    'routers.gst',
    'routers.inventory',
    'routers.items',
    'routers.ledgers',
    'routers.onboarding_utils',
    'routers.operations',
    'routers.query',
    'routers.reports',
    'routers.search',
    'routers.settings',
    'routers.setup',
    'routers.subscribe',
    'routers.sync',
    'routers.tenant_config',
    'routers.usage',
    'routers.vouchers',
    'routers.whatsapp',
    'routers.whatsapp_binding',
    'routers.whatsapp_cloud',
]
hidden_imports += collect_submodules('routers')

# database/ — explicit list
hidden_imports += [
    'database',
    'database.encryption',
    'database.migrations',
    'database.models',
    'database.repository',
    'database.supabase_client',
]
hidden_imports += collect_submodules('database')

hidden_imports += collect_submodules('compliance')
hidden_imports += collect_submodules('tools')
hidden_imports += collect_submodules('orchestration')
hidden_imports += collect_submodules('middleware')
hidden_imports += collect_submodules('ai_engine')
hidden_imports += collect_submodules('extraction')
hidden_imports += collect_submodules('classification')
hidden_imports += collect_submodules('gemini')
hidden_imports += collect_submodules('sync')
hidden_imports += collect_submodules('credit_engine')

# ─────────────────────────────────────────────────────────────
# DATA FILES to bundle inside the executable
# ─────────────────────────────────────────────────────────────
datas = [
    ('.env', '.'),                    # API keys / secrets
    ('config/cloud.json', 'config'),  # Cloud routing config
    ('loader.py', '.'),               # Explicit copy of loader (belt-and-suspenders)
]

# ─────────────────────────────────────────────────────────────
# ANALYSIS
# pathex MUST include BACKEND_DIR so all local imports resolve
# ─────────────────────────────────────────────────────────────
a = Analysis(
    ['desktop_main.py'],
    pathex=[BACKEND_DIR],
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
    console=True,               # ← MUST be True so crash output is visible
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
