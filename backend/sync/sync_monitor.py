"""
Sync Monitor - Monitors Tally connection and sync status

This module provides functions to:
1. Check if Tally is reachable
2. Get the last successful sync time
3. Report the overall system health
"""

import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class SyncMonitor:
    def __init__(self, tally_url: str = "http://localhost:9000"):
        self.tally_url = tally_url
        self._last_sync_time: Optional[datetime] = None
        self._last_sync_status: str = "unknown"
        self._last_error: Optional[str] = None

    def check_tally_connection(self) -> bool:
        """
        Ping Tally to verify connectivity.
        Returns True if Tally is reachable, False otherwise.
        """
        try:
            # Tally usually responds to a simple GET on root or a known endpoint
            # We'll use a short timeout to avoid blocking
            response = requests.get(self.tally_url, timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def update_sync_status(self, status: str, error: Optional[str] = None):
        """Update the status of the last sync attempt"""
        self._last_sync_status = status
        if status == "success":
            self._last_sync_time = datetime.now()
            self._last_error = None
        else:
            self._last_error = error

    def get_health_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive health report of the sync system
        """
        tally_connected = self.check_tally_connection()
        
        return {
            "tally_connected": tally_connected,
            "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
            "last_sync_status": self._last_sync_status,
            "last_error": self._last_error,
            "overall_health": "healthy" if tally_connected and self._last_sync_status != "failed" else "degraded"
        }

# Global instance
# In a real app, this URL might come from env vars
monitor = SyncMonitor()
