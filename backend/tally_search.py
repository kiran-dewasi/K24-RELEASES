import logging
import difflib
import time
from typing import List, Optional, Tuple, Dict
from tally_reader import TallyReader

logger = logging.getLogger("TallySearch")

class TallySearch:
    """
    Intelligent Tally Search Engine.
    Features:
    - Fuzzy Matching (difflib)
    - Caching (TTL)
    - Consolidated Ledger/Item Lookups
    """
    
    _ledger_cache: List[str] = []
    _ledger_cache_time: float = 0.0
    _item_cache: List[str] = []
    _item_cache_time: float = 0.0
    
    CACHE_DURATION = 300 # 5 Minutes

    def __init__(self, tally_url: str = "http://localhost:9000"):
        self.reader = TallyReader(tally_url=tally_url)

    def _refresh_ledgers_if_needed(self):
        now = time.time()
        if not self._ledger_cache or (now - self._ledger_cache_time > self.CACHE_DURATION):
            logger.info("ðŸ”„ Refreshing Ledger Cache from Tally...")
            try:
                self._ledger_cache = self.reader.get_all_ledgers()
                self._ledger_cache_time = now
                logger.info(f"âœ… Cached {len(self._ledger_cache)} Ledgers.")
            except Exception as e:
                logger.error(f"âŒ Failed to refresh ledger cache: {e}")
    
    def _refresh_items_if_needed(self):
        now = time.time()
        if not self._item_cache or (now - self._item_cache_time > self.CACHE_DURATION):
            logger.info("ðŸ”„ Refreshing Stock Item Cache from Tally...")
            try:
                self._item_cache = self.reader.get_all_stock_items()
                self._item_cache_time = now
                logger.info(f"âœ… Cached {len(self._item_cache)} Items.")
            except Exception as e:
                logger.error(f"âŒ Failed to refresh item cache: {e}")

    def smart_ledger_search(self, query: str, threshold: float = 0.6) -> str:
        """
        Finds the best matching existing ledger. 
        Returns the EXISTING Tally Name if score > threshold, else returns 'query' (to be created).
        """
        self._refresh_ledgers_if_needed()
        
        if not self._ledger_cache:
            logger.warning("DEBUG: Ledger Cache is empty! Finding match is impossible. Returning query for creation.")
            return query

        query_norm = query.strip().lower()
        
        # 1. Exact Match Check
        for name in self._ledger_cache:
            if name.lower() == query_norm:
                logger.info(f"ðŸŽ¯ Exact Match Found: '{name}'")
                return name
        
        # 2. Substring Match (Strong Signal)
        # If user types "Prince Ent" and we have "Prince Enterprises"
        for name in self._ledger_cache:
            name_norm = name.lower()
            if name_norm.startswith(query_norm) or query_norm.startswith(name_norm):
                logger.info(f"ðŸ§  Smart Prefix Match: '{query}' -> '{name}'")
                return name
        
        # 3. Fuzzy Match
        matches = difflib.get_close_matches(query, self._ledger_cache, n=1, cutoff=threshold)
        if matches:
            best_match = matches[0]
            logger.info(f"ðŸ§  Smart Fuzzy Match: User said '{query}', Tally has '{best_match}' (Score > {threshold})")
            return best_match
            
        logger.info(f"ðŸ†• No match found for '{query}'. Will Create New.")
        return query

    def smart_item_search(self, query: str, threshold: float = 0.6) -> str:
        """
        Smart search for Stock Items.
        """
        self._refresh_items_if_needed()
        
        if not self._item_cache:
            return query
            
        query_norm = query.strip().lower()
        
        # 1. Exact
        for name in self._item_cache:
            if name.lower() == query_norm:
                return name

        # 2. Prefix
        for name in self._item_cache:
            name_norm = name.lower()
            if name_norm.startswith(query_norm) or query_norm.startswith(name_norm):
                logger.info(f"ðŸ§  Smart Item Prefix: '{query}' -> '{name}'")
                return name
                
        # 3. Fuzzy
        matches = difflib.get_close_matches(query, self._item_cache, n=1, cutoff=threshold)
        if matches:
            best_match = matches[0]
            logger.info(f"ðŸ§  Smart Item Fuzzy: '{query}' -> '{best_match}'")
            return best_match
            
        return query # Return original to trigger creation

    def check_existence(self, name: str, type_: str = "ledger") -> bool:
        """Simple boolean check against cache"""
        if type_ == "ledger":
            self._refresh_ledgers_if_needed()
            return name in self._ledger_cache # Case sensitive technically, but cache has Tally Exact Names
        else:
            self._refresh_items_if_needed()
            return name in self._item_cache

