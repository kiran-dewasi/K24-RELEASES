
from backend.services.query_orchestrator import QueryOrchestrator, ParsedQuery, QueryIntent, INTENT_PATTERNS
import re

def test():
    queries = [
        "give me sales excel",
        "send me pdf",
        "get excel",
        "export sales to excel",
        "Top 5 customers",
        "Outstanding from Vinayak",
        "Stock of Tomato",
        "January sales summary",
        "Show invoice 123"
    ]
    
    for q in queries:
        matched = False
        text = q.lower().strip()
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    print(f"[MATCH] '{q}' matches {intent}")
                    matched = True
                    break
            if matched: break
        
        if not matched:
            print(f"[NO MATCH] '{q}'")

if __name__ == "__main__":
    test()
