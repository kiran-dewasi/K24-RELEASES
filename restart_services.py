"""
Restart Services Script.
Kills process on Port 8000 and restarts Backend + Tally Agent.
"""
import subprocess
import os
import sys
import time

def kill_port(port):
    print(f"Checking Port {port}...")
    try:
        # Get PID
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode()
        lines = output.strip().split('\n')
        for line in lines:
            if "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                print(f"Killing PID {pid} on Port {port}...")
                subprocess.run(f"taskkill /PID {pid} /F", shell=True)
                return True
    except subprocess.CalledProcessError:
        print(f"Port {port} seems free.")
        return False
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

def start_services():
    # 1. Kill Backend
    kill_port(8000)
    time.sleep(2)
    
    # 2. Start Backend
    print("Starting Backend (uvicorn)...")
    backend = subprocess.Popen(
        ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=os.getcwd(),
        shell=True, # Need shell for uvicorn in path usually? Or direct.
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL
    )
    print(f"Backend started (PID {backend.pid})")
    time.sleep(5) # Wait for startup
    
    # 3. Start Agent
    print("Starting Tally Agent...")
    agent = subprocess.Popen(
        [sys.executable, "clients/tally_agent.py"],
        cwd=os.getcwd(),
        shell=True
    )
    print(f"Agent started (PID {agent.pid})")

if __name__ == "__main__":
    start_services()
