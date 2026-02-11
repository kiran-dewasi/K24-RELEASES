
import os
import shutil
import sys

def prepare_binaries():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(root_dir, 'frontend')
    tauri_dir = os.path.join(frontend_dir, 'src-tauri')
    binaries_dir = os.path.join(tauri_dir, 'binaries')
    
    os.makedirs(binaries_dir, exist_ok=True)
    
    target_triple = "x86_64-pc-windows-msvc"
    
    # 1. Backend - SKIPPED (Handled by build_sidecars.py)
    # backend_src = os.path.join(root_dir, 'backend', 'dist', 'k24-backend.exe')
    # backend_dest = os.path.join(binaries_dir, f'k24-backend-{target_triple}.exe')
    
    # if os.path.exists(backend_src):
    #     print(f"Copying Backend: {backend_src} -> {backend_dest}")
    #     shutil.copy2(backend_src, backend_dest)
    # else:
    #     print(f"WARNING: Backend binary not found at {backend_src}")

    # 2. Listener
    listener_src = os.path.join(root_dir, 'baileys-listener', 'k24-listener.exe')
    listener_dest = os.path.join(binaries_dir, f'k24-listener-{target_triple}.exe')
    
    if os.path.exists(listener_src):
        print(f"Copying Listener: {listener_src} -> {listener_dest}")
        shutil.copy2(listener_src, listener_dest)
    else:
        print(f"WARNING: Listener binary not found at {listener_src}")
        
    print("Done.")

if __name__ == "__main__":
    prepare_binaries()
