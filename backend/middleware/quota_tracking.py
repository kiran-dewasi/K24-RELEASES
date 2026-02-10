import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Quota Limits (requests per day)
TIERS = {
    "free": 50,
    "paid": 1000,
    "enterprise": float('inf')
}

class QuotaTracker:
    """
    Tracks daily usage quotas per user.
    Resets at midnight UTC.
    """
    
    def __init__(self):
        # In-memory store: {user_id: {"date": "YYYY-MM-DD", "count": 0}}
        self._usage_store: Dict[str, Dict] = defaultdict(lambda: {"date": "", "count": 0})

    def _get_today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def check_and_increment(self, user_id: str, tier: str = "free") -> Tuple[bool, int, int]:
        """
        Check if user has quota and increment usage.
        Returns: (allowed, remaining, limit)
        """
        today = self._get_today_str()
        user_data = self._usage_store[user_id]
        
        # Reset if new day
        if user_data["date"] != today:
            user_data["date"] = today
            user_data["count"] = 0
            
        current_usage = user_data["count"]
        limit = TIERS.get(tier, TIERS["free"])
        
        if current_usage >= limit:
            return False, 0, limit
            
        # Increment
        user_data["count"] += 1
        remaining = limit - user_data["count"]
        
        return True, remaining, limit

# Global instance
quota_tracker = QuotaTracker()
