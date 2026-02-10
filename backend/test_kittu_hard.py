import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.orchestrator import K24Orchestrator
from backend.intent_recognizer import IntentType

# Mock Tally Connector to avoid needing live Tally
class MockTallyConnector:
    def fetch_ledgers(self, company):
        return []

async def run_stress_test():
    print("🔥 STARTING KITTU HARD STRESS TEST 🔥")
    print("=======================================")
    
    # Initialize Orchestrator
    # Note: We need a real API key for Gemini, assuming it's in env or we mock the recognizer too.
    # For this test, we'll assume the environment has the key or we'll mock the intent recognizer if needed.
    # But to test "hard", we should try to use the real recognizer if possible.
    api_key = os.getenv("GOOGLE_API_KEY", "test-key") 
    orchestrator = K24Orchestrator(api_key=api_key)
    
    # Mock the Tally connector to prevent connection errors
    orchestrator.tally = MockTallyConnector()

    scenarios = [
        {
            "name": "1. Navigation - Balance Sheet",
            "input": "Show me the balance sheet",
            "context": {},
            "expected_type": "navigation",
            "expected_path": "/reports/balance-sheet"
        },
        {
            "name": "2. Navigation - Cash Book",
            "input": "Open cash book",
            "context": {},
            "expected_type": "navigation",
            "expected_path": "/reports/cash-book"
        },
        {
            "name": "3. Transaction - Complete Sale",
            "input": "Create a sale to Sharma Traders for 5000 rupees",
            "context": {},
            "expected_type": "draft_voucher",
            "check_data": lambda d: d['party_name'] == 'Sharma Traders' and d['total_amount'] == 5000
        },
        {
            "name": "4. Transaction - Missing Party",
            "input": "Create a sale for 5000",
            "context": {},
            "expected_type": "clarification", # Should ask for party
            "check_data": lambda d: d.get('missing_slot') == 'party'
        },
        {
            "name": "5. Context Awareness - Cash Query",
            "input": "What is the balance?",
            "context": {"page": "cash-book", "ledger": "Cash"},
            # Currently, the orchestrator might just see "balance" and route to balance sheet OR generic query.
            # Let's see what it does. This detects if our context logic is working or needs work.
            "expected_type": ["navigation", "text"] 
        },
        {
            "name": "6. Unknown Intent / Gibberish",
            "input": "The quick brown fox jumps over the lazy dog",
            "context": {},
            "expected_type": "text" # Should fallback gracefully
        }
    ]

    passed = 0
    failed = 0

    for scenario in scenarios:
        print(f"\nTesting: {scenario['name']}")
        print(f"Input: '{scenario['input']}'")
        if scenario['context']:
            print(f"Context: {scenario['context']}")

        try:
            # We need to simulate the API calling process_message
            # We can't easily inject client_context into process_message directly without modifying it 
            # because process_message reads from ContextManager.
            # So for this test, we'll manually update the context manager first.
            
            user_id = "test_user"
            if scenario['context']:
                orchestrator.context_manager.update_context(user_id, scenario['context'])

            response = await orchestrator.process_message(user_id, scenario['input'])
            
            print(f"Result Type: {response['type']}")
            if response.get('data'):
                print(f"Data: {response['data']}")
            
            # Validation
            is_pass = False
            if isinstance(scenario['expected_type'], list):
                if response['type'] in scenario['expected_type']:
                    is_pass = True
            elif response['type'] == scenario['expected_type']:
                is_pass = True
                
            if is_pass:
                # Extra checks
                if 'expected_path' in scenario:
                    if response['data'].get('path') == scenario['expected_path']:
                        print("✅ Path Match")
                    else:
                        print(f"❌ Path Mismatch: Got {response['data'].get('path')}")
                        is_pass = False
                
                if 'check_data' in scenario:
                    if scenario['check_data'](response['data']):
                         print("✅ Data Validation Passed")
                    else:
                         print("❌ Data Validation Failed")
                         is_pass = False

            if is_pass:
                print("✅ PASSED")
                passed += 1
            else:
                print(f"❌ FAILED. Expected {scenario['expected_type']}, got {response['type']}")
                failed += 1

        except Exception as e:
            print(f"❌ CRASHED: {e}")
            failed += 1

    print("\n=======================================")
    print(f"SUMMARY: {passed} Passed, {failed} Failed")
    print("=======================================")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
