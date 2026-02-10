#!/usr/bin/env python3
"""
K24 Backend Entry Point

This script is the main entry point for the K24 backend when running as a desktop app.
It handles command-line arguments for desktop mode configuration.

Usage:
    python run_backend.py                           # Development mode (port 8000)
    python run_backend.py --port 9123 --token abc   # Desktop mode with custom port
    python run_backend.py --desktop-mode true --port 9123 --token abc123

Arguments:
    --port          Port to run the server on (default: 8000)
    --token         Desktop session token for security validation
    --desktop-mode  Enable desktop security mode (validates X-Desktop-Token)
    --host          Host to bind to (default: 127.0.0.1)
"""

import argparse
import os
import sys
import logging

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("k24_backend")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="K24 Backend Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port to run the server on (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("DESKTOP_TOKEN", ""),
        help="Desktop session token for security validation"
    )
    
    parser.add_argument(
        "--desktop-mode",
        type=str,
        default=os.getenv("DESKTOP_MODE", "false"),
        help="Enable desktop security mode (true/false)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    return parser.parse_args()


def configure_environment(args):
    """Set environment variables based on arguments"""
    
    # Desktop mode configuration
    is_desktop = args.desktop_mode.lower() == "true"
    
    if is_desktop:
        os.environ["DESKTOP_MODE"] = "true"
        os.environ["DESKTOP_TOKEN"] = args.token
        logger.info(f"🔒 Desktop mode enabled on port {args.port}")
        
        if not args.token:
            logger.warning("⚠️  No desktop token provided - security compromised!")
    else:
        os.environ["DESKTOP_MODE"] = "false"
        logger.info(f"🔓 Development mode on port {args.port}")
    
    # Set port in environment for other modules
    os.environ["K24_PORT"] = str(args.port)


def run_server(args):
    """Start the uvicorn server"""
    import uvicorn
    
    logger.info(f"Starting K24 Backend on {args.host}:{args.port}")
    
    uvicorn.run(
        "backend.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


def main():
    """Main entry point"""
    args = parse_args()
    
    # Configure environment before importing app
    configure_environment(args)
    
    try:
        run_server(args)
    except KeyboardInterrupt:
        logger.info("Shutting down K24 Backend...")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
