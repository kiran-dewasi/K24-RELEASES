"""
Desktop Application Main Entry Point
Starts the backend and WhatsApp poller
"""

import asyncio
import logging
import sys

from desktop.services import init_poller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main application entry point"""
    logger.info("🚀 K24 Desktop Application Starting...")
    
    try:
        # Initialize and start WhatsApp poller
        poller = init_poller()
        logger.info("✅ WhatsApp Poller initialized")
        
        # Start polling (runs forever)
        await poller.start_polling()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
