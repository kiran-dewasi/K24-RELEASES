import sys
import argparse
import os
import time
from pathlib import Path

# === CRITICAL: Parse args and set env vars FIRST ===
def parse_args():
    parser = argparse.ArgumentParser(description='K24 Backend Desktop Mode')
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--token', type=str, required=True)
    parser.add_argument('--desktop-mode', type=str, default='false')  # Only true in packaged Tauri builds
    return parser.parse_args()

# Set environment for PyInstaller
if getattr(sys, 'frozen', False):
    os.environ["IS_DESKTOP"] = "true"
    # Ensure current directory is in path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
else:
    # Manual Fallback if run from root directory
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file if it exists (for GOOGLE_API_KEY)
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    print(f"[DEBUG] Loading .env from {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Check if GOOGLE_API_KEY is set
google_key = os.environ.get('GOOGLE_API_KEY', '')
if google_key:
    # Mask key for logging
    masked_key = f"{google_key[:5]}...{google_key[-4:]}" if len(google_key) > 10 else "***"
    print(f"[DEBUG] GOOGLE_API_KEY loaded from environment (length: {len(google_key)})")
else:
    print("[WARNING] GOOGLE_API_KEY not set - AI features will fail when used")

import multiprocessing
import logging

# === LOGGING SETUP (File + Console) ===
def setup_logging():
    # Create log directory
    if sys.platform == "win32":
        log_dir = Path.home() / "AppData" / "Roaming" / "k24" / "logs"
    else:
        log_dir = Path.home() / ".k24" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),  # Append mode
            logging.StreamHandler(sys.stdout)  # Also print to console
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("K24 BACKEND STARTING")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Working Directory: {Path.cwd()}")
    logger.info(f"Log File: {log_file}")
    logger.info("="*60)
    
    return logger

if __name__ == "__main__":
    # Required for PyInstaller on Windows
    multiprocessing.freeze_support() 
    
    # Force UTF-8 for Windows Console
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    try:
        # Parse args first to get configuration
        args = parse_args()
        
        # Set Env vars BEFORE importing app
        os.environ['DESKTOP_MODE'] = args.desktop_mode
        os.environ['DESKTOP_TOKEN'] = args.token
        
        # DEBUG mode MUST be set explicitly via environment variables or .env file
        # We do NOT auto-enable DEBUG for non-frozen builds to prevent accidental
        # dev mode bypass in production scenarios
        # For local development: add DEBUG=true to backend/.env file
        
        # Setup logging
        logger = setup_logging()
        
        logger.info(f"Arguments received: port={args.port}, desktop_mode={args.desktop_mode}")
        logger.info(f"Token: {args.token[:8]}...")
        
        print(f"[INFO] Starting K24 Backend Sidecar on 127.0.0.1:{args.port}...")
        logger.info(f"Starting uvicorn on 127.0.0.1:{args.port}")
        
        # NOW import the FastAPI app (after env vars are set)
        import uvicorn
        from backend.api import app
        
        # Run Uvicorn usage
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info", loop="asyncio")
        
    except Exception as e:
        if 'logger' in locals():
            logger.critical("FATAL ERROR DURING STARTUP", exc_info=True)
            logger.critical(f"Error: {str(e)}")
        else:
            print(f"FATAL ERROR (Pre-Logging): {e}")
            import traceback
            traceback.print_exc()
            
        # Keep process alive for 30 seconds so Rust can read the error
        time.sleep(30)
        sys.exit(1)
