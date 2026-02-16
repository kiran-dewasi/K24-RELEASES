#!/usr/bin/env python3
"""
Simple WhatsApp Poller for Smoke Test
Polls Supabase whatsapp_message_queue and processes jobs

Usage:
    python run_whatsapp_poller.py --tenant-id K24-abc123
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional

try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase library not installed. Run: pip install supabase")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleSuapbasePoller:
    """Simple poller that watches Supabase whatsapp_message_queue"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.is_running = False
        
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
            sys.exit(1)
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info(f"✓ Connected to Supabase")
    
    async def poll_once(self):
        """Poll for pending jobs in the queue"""
        try:
            result = self.supabase.table("whatsapp_message_queue")\
                .select("*")\
                .eq("tenant_id", self.tenant_id)\
                .eq("status", "pending")\
                .order("created_at")\
                .limit(10)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Poll error: {e}")
            return []
    
    async def process_job(self, job: dict):
        """Process a single job"""
        job_id = job.get("id")
        message_text = job.get("message_text", "")
        
        try:
            logger.info(f"📨 Processing job {job_id}")
            logger.info(f"   Message: {message_text}")
            
            # Update to processing
            self.supabase.table("whatsapp_message_queue")\
                .update({
                    "status": "processing",
                    "processing_started_at": datetime.utcnow().isoformat()
                })\
                .eq("id", job_id)\
                .execute()
            
            # Simulate processing
            await asyncio.sleep(2)
            
            # Mark as processed
            self.supabase.table("whatsapp_message_queue")\
                .update({
                    "status": "processed",
                    "processed_at": datetime.utcnow().isoformat()
                })\
                .eq("id", job_id)\
                .execute()
            
            logger.info(f"✅ Job {job_id} completed")
            
        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {e}")
            
            # Mark as failed
            try:
                self.supabase.table("whatsapp_message_queue")\
                    .update({
                        "status": "failed",
                        "error_message": str(e),
                        "processed_at": datetime.utcnow().isoformat()
                    })\
                    .eq("id", job_id)\
                    .execute()
            except:
                pass
    
    async def start(self):
        """Start polling loop"""
        self.is_running = True
        logger.info(f"🔄 Poller started for tenant {self.tenant_id}")
        logger.info(f"   Polling every 5 seconds. Press Ctrl+C to stop.")
        
        poll_count = 0
        
        while self.is_running:
            try:
                poll_count += 1
                jobs = await self.poll_once()
                
                if jobs:
                    logger.info(f"[Poll #{poll_count}] Found {len(jobs)} pending jobs")
                    for job in jobs:
                        await self.process_job(job)
                else:
                    logger.debug(f"[Poll #{poll_count}] No pending jobs")
                
                # Wait 5 seconds before next poll
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop polling"""
        self.is_running = False
        logger.info("🛑 Poller stopped")


async def main():
    parser = argparse.ArgumentParser(
        description="Simple WhatsApp Queue Poller for Smoke Testing"
    )
    
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant ID to process jobs for"
    )
    
    args = parser.parse_args()
    
    poller = SimpleSuapbasePoller(tenant_id=args.tenant_id)
    
    try:
        await poller.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        await poller.stop()


if __name__ == "__main__":
    asyncio.run(main())
