from backend.ledger_matcher import LedgerMatcher, LedgerMatcherConfig

def test_matcher():
    ledgers = [
        "Drishti Enterprises",
        "Shree Traders",
        "Prince Traders",
        "Apple Inc"
    ]
    
    config = LedgerMatcherConfig(
        auto_match_threshold=0.85,
        confirm_threshold=0.75,
        core_similarity_threshold=0.80
    )
    
    matcher = LedgerMatcher(ledgers, config)
    
    queries = [
        "prince enterprises", # Should NOT auto-match Drishti Enterprises
        "Prince Traders",     # Exact match
        "Shre Traders",       # Typo, should auto-match Shree Traders if core similarity is high
        "Apple Corp",         # Should be no match or needs confirm
    ]
    
    for q in queries:
        res = matcher.match(q)
        print(f"Query: '{q}' -> Status: {res.status}, Matched: {res.matched_name}, Score: {res.score}")

if __name__ == "__main__":
    test_matcher()
