"""
Tally Background Sync Service
Real-time sync between Tally and SQLite Shadow DB
Runs every 5 seconds when active, 5 minutes when idle
"""

import asyncio
import time
import logging
import sys
from typing import Dict, Optional
from datetime import datetime

# Fix for Windows Console Unicode Error (CP1252 vs emojis)
if sys.platform.startswith("win"):
    # Reconfigure stdout/stderr to use utf-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older python versions or weird environments
        pass

from sync_engine import sync_engine
from tally_connector import TallyConnector
from database import SessionLocal
from services.tally_sync_checkpoint import checkpoint
from services.cloud_backup import backup_service

logger = logging.getLogger(__name__)


class TallySyncService:
    """
    Real-time background sync between Tally and SQLite
    Runs every 5 seconds when active, 5 minutes when idle
    """
    
    def __init__(self, interval_active: int = 300, interval_idle: int = 600):
        # interval_active: 5 min — Tally HTTP server cannot handle sub-minute polling
        #                          (returns empty 716-byte response under rapid fire)
        # interval_idle:  10 min — when no user interaction for 5+ min
        self.interval_active = interval_active
        self.interval_idle = interval_idle
        self.is_running = False
        self.last_activity = time.time()
        self.connector = TallyConnector()
        self.last_sync_time = None
        # Set last_backup to NOW so we don't immediately attempt a cloud backup
        # on every backend restart. First backup fires 6 hours after startup.
        self.last_backup = time.time()
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_error": None
        }
    
    def mark_activity(self):
        """Mark user activity to switch to active sync mode"""
        self.last_activity = time.time()
    
    async def start(self):
        """Start the sync loop"""
        self.is_running = True
        logger.info("🔄 Tally Sync Service Started")
        
        while self.is_running:
            try:
                # Check if user is active (based on last UI interaction)
                is_active = (time.time() - self.last_activity) < 300  # 5 min
                interval = self.interval_active if is_active else self.interval_idle
                
                mode = "ACTIVE" if is_active else "IDLE"
                logger.info(f"🔄 Sync Mode: {mode} (interval: {interval}s)")
                
                # Run sync
                await self.sync_all()
                
                # Check for backup (every 6 hours = 21600 seconds)
                if (time.time() - self.last_backup) > 21600:
                    logger.info("☁️ Starting Cloud Backup...")
                    success = await self.run_in_thread(backup_service.create_backup)
                    if success:
                        self.last_backup = time.time()
                
                # Wait before next cycle
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                self.sync_stats["last_error"] = str(e)
                await asyncio.sleep(30)  # Wait 30s on error
    
    async def stop(self):
        """Stop the sync service"""
        self.is_running = False
        logger.info("🛑 Tally Sync Service Stopped")
    
    async def sync_all(self, mode: str = "incremental"):
        """
        Sync all data types from Tally.

        Args:
            mode: "incremental" (default, last 24h) or "full" (all data)

        Returns None and logs a warning (without counting as failure) when no
        valid tenant is found in the local users table — this happens before
        the user logs in for the first time on this device.
        """
        start = time.time()

        # Pre-flight: verify a valid tenant exists before wasting cycles
        # (and before potentially writing "default"-tagged rows to the DB).
        try:
            from database import SessionLocal as _SL
            _db = _SL()
            try:
                sync_engine._get_tenant_id(_db)
            finally:
                _db.close()
        except ValueError as no_tenant_err:
            logger.warning(
                f"⏭️  Tally sync skipped — {no_tenant_err}. "
                "Sync will resume automatically after the user logs in."
            )
            return None

        self.sync_stats["total_syncs"] += 1

        try:
            # Use transactional sync with auto-rollback
            # We use "system" as user_id for the single-user desktop app
            with checkpoint.transaction("system", mode):
                if mode == "full":
                    # Full comprehensive sync
                    result = await self.run_in_thread(
                        sync_engine.full_comprehensive_sync,
                        include_movements=False
                    )
                else:
                    # Incremental sync — run SEQUENTIALLY, not in parallel.
                    # Tally has a single-connection HTTP server (pool_maxsize=1).
                    # Parallel requests overflow the pool: extras are discarded
                    # and Tally returns empty 716-byte responses for all of them.
                    ledger_result  = await self.sync_ledgers()
                    voucher_result = await self.sync_vouchers_incremental()
                    stock_result   = await self.sync_stock_items()
                    bill_result    = await self.sync_bills()

                    result = {
                        "ledgers":     ledger_result,
                        "vouchers":    voucher_result,
                        "stock_items": stock_result,
                        "bills":       bill_result,
                    }

            elapsed = time.time() - start
            self.last_sync_time = datetime.now()
            self.sync_stats["successful_syncs"] += 1

            logger.info(f"✅ Sync complete in {elapsed:.1f}s: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            self.sync_stats["failed_syncs"] += 1
            self.sync_stats["last_error"] = str(e)
            raise

    
    async def sync_ledgers(self) -> Dict:
        """Pull all ledgers from Tally and update SQLite"""
        try:
            # Run in thread to avoid blocking
            result = await self.run_in_thread(sync_engine.pull_ledgers)
            logger.debug(f"📊 Ledgers synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Ledger sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def sync_ledgers_complete(self) -> Dict:
        """Pull complete ledger details (with contact info)"""
        try:
            result = await self.run_in_thread(sync_engine.sync_ledgers_complete)
            logger.debug(f"📊 Complete ledgers synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Complete ledger sync failed: {e}")
            return {"synced": 0, "enriched": 0, "errors": 1}
    
    async def sync_vouchers_incremental(self) -> Dict:
        """Pull vouchers from last 24 hours"""
        try:
            result = await self.run_in_thread(sync_engine.incremental_sync, since_hours=24)
            logger.debug(f"📋 Vouchers synced (24h): {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Voucher sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def sync_stock_items(self) -> Dict:
        """Pull all stock items from Tally"""
        try:
            result = await self.run_in_thread(sync_engine.pull_stock_items)
            logger.debug(f"📦 Stock items synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Stock item sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def sync_stock_items_complete(self) -> Dict:
        """Pull complete stock items (with HSN, GST)"""
        try:
            result = await self.run_in_thread(sync_engine.sync_stock_items_complete)
            logger.debug(f"📦 Complete stock items synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Complete stock item sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def sync_bills(self) -> Dict:
        """Pull outstanding bills (receivables/payables)"""
        try:
            result = await self.run_in_thread(sync_engine.sync_bills)
            logger.debug(f"💰 Bills synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Bills sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def sync_stock_movements(self, item_name: Optional[str] = None) -> Dict:
        """Pull stock movements"""
        try:
            result = await self.run_in_thread(
                sync_engine.sync_stock_movements, 
                item_name=item_name
            )
            logger.debug(f"📊 Stock movements synced: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Stock movement sync failed: {e}")
            return {"synced": 0, "errors": 1}
    
    async def run_in_thread(self, func, *args, **kwargs):
        """
        Run a blocking function in a thread pool to avoid blocking the event loop
        """
        import functools
        loop = asyncio.get_event_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial_func)
    
    async def health_check(self) -> Dict:
        """
        Check if Tally is reachable and return sync service status
        """
        try:
            # Try to ping Tally
            test_result = await self.run_in_thread(
                self.connector.send_request,
                '<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>Company Info</REPORTNAME></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>'
            )
            
            tally_online = bool(test_result)
            
        except Exception as e:
            tally_online = False
            logger.warning(f"Tally health check failed: {e}")
        
        return {
            "service_running": self.is_running,
            "tally_online": tally_online,
            "last_sync": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "stats": self.sync_stats,
            "mode": "ACTIVE" if (time.time() - self.last_activity) < 300 else "IDLE"
        }
    
    def get_stats(self) -> Dict:
        """Get sync statistics"""
        return {
            **self.sync_stats,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "is_running": self.is_running,
            "success_rate": (
                self.sync_stats["successful_syncs"] / self.sync_stats["total_syncs"] * 100
                if self.sync_stats["total_syncs"] > 0 else 0
            )
        }


# Global singleton instance
tally_sync_service = TallySyncService()


# Convenience functions
async def start_sync_service():
    """Start the background sync service"""
    await tally_sync_service.start()


async def stop_sync_service():
    """Stop the background sync service"""
    await tally_sync_service.stop()


async def sync_now(mode: str = "incremental"):
    """
    Trigger an immediate sync
    
    Args:
        mode: "incremental" or "full"
    """
    return await tally_sync_service.sync_all(mode=mode)


async def get_sync_status():
    """Get current sync service status"""
    return await tally_sync_service.health_check()


# For running as standalone service
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Tally Background Sync Service")
    print("Press Ctrl+C to stop")
    
    try:
        asyncio.run(start_sync_service())
    except KeyboardInterrupt:
        print("\n🛑 Stopping sync service...")
        asyncio.run(stop_sync_service())
        print("✅ Service stopped")
