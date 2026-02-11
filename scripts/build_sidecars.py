import subprocess
import os
import shutil
import sys

# Target Triple for Windows
target_triple = "x86_64-pc-windows-msvc"

def build_backend():
    print("Building Backend Sidecar...")
    
    # Absolute paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_path = os.path.join(base_dir, "frontend", "src-tauri", "binaries")
    work_path = os.path.join(base_dir, "build_temp")
    
    if not os.path.exists(dist_path):
        os.makedirs(dist_path)
    
    # Ensure backend script is visible
    script_path = os.path.join(base_dir, "backend", "desktop_main.py")

    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name", f"k24-backend-{target_triple}",
        "--distpath", dist_path,
        "--workpath", work_path,
        "--specpath", work_path,
        
        # Hidden Imports (Critical for FastAPI/Uvicorn)
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "engineio.async_drivers.asgi",
        "--hidden-import", "socketio",
        "--hidden-import", "sqlalchemy.sql.default_comparator",
        "--hidden-import", "sqlite3",
        "--hidden-import", "backend.database", # Package import
        
        # === NEW CRITICAL IMPORTS (Phase 2 Fix) ===
        
        # Pandas (CRITICAL)
        "--hidden-import", "pandas",
        "--hidden-import", "pandas._libs.tslibs.timedeltas",
        "--hidden-import", "pandas._libs.tslibs.np_datetime",
        "--hidden-import", "pandas._libs.tslibs.nattype",
        "--hidden-import", "pandas._libs.skiplist",
        "--hidden-import", "pandas._libs.hashtable",
        "--hidden-import", "pandas._libs.lib",
        
        # NumPy (Pandas dependency)
        "--hidden-import", "numpy",
        "--hidden-import", "numpy.core._dtype_ctypes",
        
        # Excel Support
        "--hidden-import", "openpyxl",
        "--hidden-import", "openpyxl.cell",
        "--hidden-import", "openpyxl.cell.cell",
        
        # PDF Generation
        "--hidden-import", "reportlab",
        "--hidden-import", "reportlab.pdfgen",
        "--hidden-import", "reportlab.pdfgen.canvas",
        "--hidden-import", "reportlab.lib.pagesizes",
        
        # FastAPI Explicit
        "--hidden-import", "fastapi",
        "--hidden-import", "fastapi.routing",
        "--hidden-import", "fastapi.responses",
        
        # Pydantic (FastAPI dependency)
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic.fields",
        "--hidden-import", "pydantic.deprecated.decorator",
        
        # Add backend routers explicitly
        "--hidden-import", "backend.routers.auth",
        "--hidden-import", "backend.routers.reports",
        "--hidden-import", "backend.services.supabase_service",
        "--hidden-import", "backend.tally_connector",
        "--hidden-import", "backend.middleware.desktop_security",
        "--hidden-import", "backend.routers.whatsapp_binding",
        "--hidden-import", "backend.routers.whatsapp",
        "--hidden-import", "backend.routers.baileys",
        "--hidden-import", "backend.routers.vouchers",
        "--hidden-import", "backend.routers.ledgers",
        "--hidden-import", "backend.routers.inventory",
        "--hidden-import", "backend.routers.items",
        "--hidden-import", "backend.routers.customers",
        "--hidden-import", "backend.routers.dashboard",
        "--hidden-import", "backend.routers.search",
        
        script_path
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print(f"Backend Sidecar Built: {dist_path}/k24-backend-{target_triple}.exe")

if __name__ == "__main__":
    build_backend()
