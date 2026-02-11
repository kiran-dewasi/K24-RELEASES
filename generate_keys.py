import os
import subprocess
import sys
from pathlib import Path

def generate_keys():
    # 1. Ensure directory exists
    tauri_dir = Path.home() / ".tauri"
    tauri_dir.mkdir(exist_ok=True)
    
    key_path = tauri_dir / "k24.key"
    
    print(f"Generating keys to {key_path}...")
    
    # 2. Run Tauri command
    # We use 'npx tauri' assuming we are in frontend dir with tauri-cli installed
    cmd = ["cmd", "/c", "npx", "tauri", "signer", "generate", "-w", str(key_path)]
    
    # Needs to run in frontend dir
    cwd = Path(r"c:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\frontend")
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        # Save Public Key to file for easy reading
        pub_key_path = tauri_dir / "k24.pub"
        with open(pub_key_path, "w") as f:
            f.write(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print("Error generating keys:")
        print(e.stdout)
        print(e.stderr)

if __name__ == "__main__":
    generate_keys()
