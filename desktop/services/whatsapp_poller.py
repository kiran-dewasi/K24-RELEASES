"""
WhatsApp Poller Service
Polls cloud API for WhatsApp messages and processes them
Pattern: Based on TallySyncService structure
"""

import asyncio
import time
import logging
import os
from typing import Dict, Optional, List
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class WhatsAppPoller:
    """
    Polls cloud API for WhatsApp messages every 30 seconds
    Processes jobs and reports completion back to cloud
    """
    
    def __init__(self, tenant_id: str, api_key: str):
        """
        Initialize WhatsApp poller
        
        Args:
            tenant_id: Tenant ID for this desktop instance
            api_key: API key for cloud authentication
        """
        self.tenant_id = tenant_id
        self.api_key = api_key
        self.is_running = False
        self.base_url = "https://api.k24.ai/api/whatsapp/cloud"
        
        # Create session with retry logic
        self.session = self._create_session()
        
        # Statistics
        self.stats = {
            "total_polls": 0,
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "last_error": None
        }
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic for 401/429"""
        session = requests.Session()
        
        # Retry strategy: 3 retries with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[401, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })
        
        return session
    
    async def poll_once(self) -> List[Dict]:
        """
        Poll cloud API once for pending jobs
        
        Returns:
            List of job dictionaries
        """
        try:
            url = f"{self.base_url}/jobs/{self.tenant_id}"
            
            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.session.get(url, timeout=10)
            )
            
            response.raise_for_status()
            data = response.json()
            jobs = data.get("jobs", [])
            
            self.stats["total_polls"] += 1
            logger.debug(f"Polled cloud API: {len(jobs)} jobs found")
            
            return jobs
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Authentication failed - invalid API key")
                self.stats["last_error"] = "Invalid API key"
            elif e.response.status_code == 429:
                logger.warning("Rate limited - backing off")
                self.stats["last_error"] = "Rate limited"
            else:
                logger.error(f"HTTP error: {e}")
                self.stats["last_error"] = str(e)
            return []
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            self.stats["last_error"] = "Connection error"
            return []
            
        except Exception as e:
            logger.error(f"Poll error: {e}")
            self.stats["last_error"] = str(e)
            return []
    
    async def process_job(self, job: Dict) -> None:
        """
        Process a single WhatsApp job
        
        Args:
            job: Job dictionary from cloud API
        """
        job_id = job.get('id') if isinstance(job, dict) else job
        message_text = job.get('message_text', '') if isinstance(job, dict) else ''
        
        try:
            logger.info(f"Processing job {job_id}: {message_text}")
            
            # TODO: Integrate with AI/Tally processing
            # For now, just print the message
            print(f"WhatsApp Message: {message_text}")
            
            # Mark job as complete
            await self._complete_job(job_id, status='delivered')
            
            self.stats["successful_jobs"] += 1
            self.stats["total_jobs"] += 1
            
        except Exception as e:
            logger.error(f"Job processing failed: {e}")
            
            # Mark job as failed
            await self._complete_job(
                job_id, 
                status='failed',
                error_message=str(e)
            )
            
            self.stats["failed_jobs"] += 1
            self.stats["total_jobs"] += 1
    
    async def _complete_job(
        self, 
        job_id: str, 
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Mark job as complete in cloud API
        
        Args:
            job_id: Job ID to complete
            status: 'delivered' or 'failed'
            error_message: Error message if status is 'failed'
        """
        try:
            url = f"{self.base_url}/jobs/{job_id}/complete"
            payload = {"status": status}
            
            if error_message:
                payload["error_message"] = error_message
            
            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.post(url, json=payload, timeout=10)
            )
            
            response.raise_for_status()
            logger.debug(f"Job {job_id} marked as {status}")
            
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
    
    async def start_polling(self) -> None:
        """
        Start polling loop - runs every 30 seconds forever
        """
        self.is_running = True
        logger.info(f"🔄 WhatsApp Poller started for tenant {self.tenant_id}")
        
        while self.is_running:
            try:
                # Poll for jobs
                jobs = await self.poll_once()
                
                # Process each job
                if jobs:
                    logger.info(f"📨 Processing {len(jobs)} WhatsApp jobs")
                    for job in jobs:
                        await self.process_job(job)
                
                # Wait 30 seconds before next poll
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Polling loop error: {e}")
                self.stats["last_error"] = str(e)
                # Wait 30s on error before retrying
                await asyncio.sleep(30)
    
    async def stop_polling(self) -> None:
        """Stop the polling loop"""
        self.is_running = False
        logger.info("🛑 WhatsApp Poller stopped")
    
    def get_stats(self) -> Dict:
        """Get polling statistics"""
        return {
            **self.stats,
            "is_running": self.is_running,
            "tenant_id": self.tenant_id,
            "success_rate": (
                self.stats["successful_jobs"] / self.stats["total_jobs"] * 100
                if self.stats["total_jobs"] > 0 else 0
            )
        }


# Global instance
_poller_instance: Optional[WhatsAppPoller] = None


def init_poller() -> WhatsAppPoller:
    """
    Initialize global poller from environment variables
    
    Returns:
        WhatsAppPoller instance
    """
    global _poller_instance
    
    tenant_id = os.getenv("TENANT_ID")
    api_key = os.getenv("DESKTOP_API_KEY")
    
    if not tenant_id:
        raise ValueError("TENANT_ID environment variable not set")
    if not api_key:
        raise ValueError("DESKTOP_API_KEY environment variable not set")
    
    _poller_instance = WhatsAppPoller(tenant_id, api_key)
    return _poller_instance


def get_poller() -> Optional[WhatsAppPoller]:
    """Get global poller instance"""
    return _poller_instance


# Standalone execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting WhatsApp Poller Service")
    print("Press Ctrl+C to stop")
    
    try:
        poller = init_poller()
        asyncio.run(poller.start_polling())
    except KeyboardInterrupt:
        print("\n🛑 Stopping poller...")
        if _poller_instance:
            asyncio.run(_poller_instance.stop_polling())
        print("✅ Poller stopped")
