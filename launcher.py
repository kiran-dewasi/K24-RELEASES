import subprocess
import time
import socket
import sys
import os
import signal
import threading

def check_port(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0

def stream_reader(pipe, prefix):
    try:
        with pipe:
            for line in iter(pipe.readline, ''):
                print(f"[{prefix}] {line.rstrip()}")
    except ValueError:
        pass

processes = []

def start_service(name, command, cwd, port=None):
    if port and not check_port(port):
        print(f"⚠️  Port {port} is already in use. Attempting to start anyway...")
        # return None

    print(f"🚀 Starting {name}...")
    
    # Windows specific: explicit shell=True for npm/uvicorn usually helps resolve paths
    # But for cleaner process management, shell=False is better if exe path is known.
    # We'll use shell=True for convenience with 'npm' and 'uvicorn' commands.
    
    try:
        p = subprocess.Popen(
            command, 
            cwd=cwd, 
            shell=True,
            # stdout=subprocess.PIPE, 
            # stderr=subprocess.PIPE,
            # universal_newlines=True # Text mode
        )
        processes.append(p)
        
        # We are not piping output to keep console simple and interactive
        # If we pipe, we need threads to read them to avoid buffer deadlock
        return p
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def main():
    print("========================================")
    print("      K24 ULTIMATE LAUNCHER (v1)       ")
    print("========================================")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    backend_dir = root_dir # Backend runs from root usually for python module resolution

    # 1. Start Backend
    start_service(
        "K24 Backend", 
        "uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload", 
        cwd=backend_dir,
        port=8000
    )

    # 2. Start WhatsApp Listener
    # Check if node_modules exists?
    wa_dir = os.path.join(root_dir, "baileys-listener")
    start_service(
        "WhatsApp Engine",
        "node listener.js",
        cwd=wa_dir
    )

    # 3. Start Frontend
    start_service(
        "K24 Frontend",
        "npm run dev",
        cwd=frontend_dir,
        port=3000
    )

    # 4. Start Tally Agent (Worker)
    client_dir = os.path.join(root_dir, "clients")
    start_service(
        "Tally Agent Worker",
        "python tally_agent.py",
        cwd=client_dir
    )

    print("\n✅ All services initiated.")
    print("👉 Backend: http://localhost:8000/docs")
    print("👉 App:     http://localhost:3000")
    print("\n(Press Ctrl+C to stop all services)")

    try:
        while True:
            time.sleep(1)
            # Check if any process died unexpectedly?
            # for p in processes:
            #     if p.poll() is not None:
            #         print(f"⚠️ A service exited with code {p.returncode}")
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for p in processes:
            # Windows requires aggressive termination for shell=True trees
            # p.terminate() might only kill the shell, not the child
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
        print("Goodbye!")

if __name__ == "__main__":
    main()
