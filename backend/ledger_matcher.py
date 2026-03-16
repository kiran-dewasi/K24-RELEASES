import re
import math
from dataclasses import dataclass
from typing import Optional, List, Set, Literal
import difflib
import logging

logger = logging.getLogger("LedgerMatcher")

MatchStatus = Literal["exact", "auto_fuzzy", "needs_confirmation", "no_match"]

@dataclass
class MatchResult:
    status: MatchStatus
    matched_name: Optional[str]
    score: Optional[float]
    original_query: str

class LedgerMatcherConfig:
    def __init__(
        self,
        auto_match_threshold: float = 0.90,
        confirm_threshold: float = 0.80,
        core_similarity_threshold: float = 0.85,
        common_suffixes: Optional[Set[str]] = None
    ):
        self.auto_match_threshold = auto_match_threshold
        self.confirm_threshold = confirm_threshold
        self.core_similarity_threshold = core_similarity_threshold
        
        if common_suffixes is None:
            self.common_suffixes = {
                "enterprises", "enterprise", "traders", "trader", 
                "ltd", "pvt ltd", "private limited", "and co", 
                "co.", "company", "corp", "corporation", "inc", "llc", "bros"
            }
        else:
            self.common_suffixes = common_suffixes

class LedgerMatcher:
    def __init__(self, ledger_names: List[str], config: Optional[LedgerMatcherConfig] = None):
        self.config = config or LedgerMatcherConfig()
        
        # Build normalized index: normalized_name -> original_name
        self.by_normalized_name = {}
        for name in ledger_names:
            norm = self._normalize(name)
            # In case of duplicates mapping to same normalized string, we keep the first one 
            # or could use a list, but usually Tally names are unique.
            if norm not in self.by_normalized_name:
                self.by_normalized_name[norm] = name

    def _normalize(self, text: str) -> str:
        """Casefold, strip whitespace, and collapse multiple spaces."""
        text = text.casefold()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _strip_common_suffixes(self, text: str) -> str:
        """Removes common business suffixes to extract the 'core' name."""
        words = text.split()
        if not words:
            return text
            
        # Compile a regex to strip suffixes at the end of the string
        # Sort suffixes by length descending to match longest first
        sorted_suffixes = sorted(list(self.config.common_suffixes), key=len, reverse=True)
        
        escaped_suffixes = [re.escape(s) for s in sorted_suffixes]
        pattern = r'\b(?:' + '|'.join(escaped_suffixes) + r')\b'
        
        # Remove suffixes, but only if they are at the end (or we can just remove them entirely)
        # It's safer to remove them from anywhere to get the pure core name
        core_text = re.sub(pattern, '', text).strip()
        core_text = re.sub(r'\s+', ' ', core_text).strip()
        
        # If removing suffixes leaves us with empty string (e.g. they named the ledger "Enterprises"),
        # just return the original text so we have something to match.
        return core_text if core_text else text

    def match(self, query_name: str) -> MatchResult:
        normalized_query = self._normalize(query_name)
        
        # 1. Exact Match
        if normalized_query in self.by_normalized_name:
            original = self.by_normalized_name[normalized_query]
            logger.info(f"LedgerMatch [Exact]: '{query_name}' -> '{original}'")
            return MatchResult(
                status="exact",
                matched_name=original,
                score=1.0,
                original_query=query_name
            )
            
        # 2. Fuzzy Matching
        best_match = None
        best_score = 0.0
        best_candidate_original = None
        
        query_core = self._strip_common_suffixes(normalized_query)
        
        for norm_candidate, original_candidate in self.by_normalized_name.items():
            # Full similarity
            full_sim = difflib.SequenceMatcher(None, normalized_query, norm_candidate).ratio()
            
            if full_sim > best_score:
                best_score = full_sim
                best_match = norm_candidate
                best_candidate_original = original_candidate
                
        if best_match is None or best_score < self.config.confirm_threshold:
            logger.info(f"LedgerMatch [No Match]: '{query_name}'. Best was '{best_candidate_original}' (score: {best_score:.3f})")
            return MatchResult(
                status="no_match",
                matched_name=None,
                score=best_score if best_candidate_original else 0.0,
                original_query=query_name
            )
            
        # We have a candidate with score >= confirm_threshold
        # Calculate core similarity 
        candidate_core = self._strip_common_suffixes(best_match)
        core_sim = difflib.SequenceMatcher(None, query_core, candidate_core).ratio()
        
        logger.debug(f"Fuzzy candidate: '{best_candidate_original}'. Full score: {best_score:.3f}, Core score: {core_sim:.3f}")
        
        if best_score >= self.config.auto_match_threshold and core_sim >= self.config.core_similarity_threshold:
            logger.info(f"LedgerMatch [Auto-Fuzzy]: '{query_name}' -> '{best_candidate_original}' (Full: {best_score:.3f}, Core: {core_sim:.3f})")
            return MatchResult(
                status="auto_fuzzy",
                matched_name=best_candidate_original,
                score=best_score,
                original_query=query_name
            )
        else:
            logger.info(f"LedgerMatch [Needs Confirmation]: '{query_name}' -> '{best_candidate_original}' (Full: {best_score:.3f}, Core: {core_sim:.3f})")
            return MatchResult(
                status="needs_confirmation",
                matched_name=best_candidate_original,
                score=best_score,
                original_query=query_name
            )
