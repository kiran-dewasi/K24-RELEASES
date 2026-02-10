"""
K24 Intent Classification Package
==================================
Comprehensive intent classification system with 68 intents.
"""

from backend.classification.intents import Intent, IntentCategory, INTENT_TO_CATEGORY
from backend.classification.intent_classifier import classify_intent, IntentClassifier
from backend.classification.intent_patterns import pattern_match_intent

__all__ = [
    "Intent",
    "IntentCategory",
    "INTENT_TO_CATEGORY",
    "classify_intent",
    "IntentClassifier",
    "pattern_match_intent",
]
