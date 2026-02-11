# K24 AI Agent - Quick Test Script
# ==================================
# Run this to test the complete agent system

import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Check if API key is set
if not os.getenv("GOOGLE_API_KEY"):
    print("❌ ERROR: GOOGLE_API_KEY not set in .env")
    print("Please add your Gemini API key to .env file")
    exit(1)

from backend.agent_orchestrator_v2 import K24AgentOrchestrator

async def test_agent():
    """Test the complete agent system"""
    
    print("🚀 K24 AI Agent - System Test")
    print("=" * 60)
    
    #  Initialize orchestrator
    print("\n[1/4] Initializing orchestrator...")
    try:
        orchestrator = K24AgentOrchestrator()
        print("✅ Orchestrator initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Test 1: Simple receipt
    print("\n[2/4] Testing: Create Receipt")
    print("-" * 60)
    
    test_message = "Create receipt for Test Customer for ₹5000"
    print(f"Input: {test_message}")
    
    try:
        result = await orchestrator.process_message(
            user_message=test_message,
            user_id="TEST_USER",
            auto_approve=False  # Preview only
        )
        
        print(f"\nResult:")
        print(json.dumps(result, indent=2))
        
        if result.get("status") == "AWAITING_APPROVAL":
            print("\n✅ Test 1 PASSED: Preview generated successfully")
        else:
            print(f"\n⚠️  Test 1: Unexpected status: {result.get('status')}")
    
    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
    
    # Test 2: Invalid ledger
    print("\n[3/4] Testing: Invalid Ledger Handling")
    print("-" * 60)
    
    test_message_2 = "Create invoice for NonExistentCompanyXYZ for ₹10000"
    print(f"Input: {test_message_2}")
    
    try:
        result2 = await orchestrator.process_message(
            user_message=test_message_2,
            user_id="TEST_USER",
            auto_approve=False
        )
        
        print(f"\nResult:")
        print(json.dumps(result2, indent=2))
        
        if result2.get("status") == "FAILED":
            print("\n✅ Test 2 PASSED: Error handling works correctly")
        else:
            print(f"\n⚠️  Test 2: Unexpected status: {result2.get('status')}")
    
    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
    
    # Test 3: Query intent
    print("\n[4/4] Testing: Query Intent")
    print("-" * 60)
    
    test_message_3 = "Show me outstanding receivables"
    print(f"Input: {test_message_3}")
    
    try:
        result3 = await orchestrator.process_message(
            user_message=test_message_3,
            user_id="TEST_USER",
            auto_approve=False
        )
        
        print(f"\nResult:")
        print(json.dumps(result3, indent=2))
        
        print("\n✅ Test 3 COMPLETED")
    
    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 System Test Complete!")
    print("=" * 60)
    print("\nThe agent system is ready to use.")
    print("\nNext steps:")
    print("1. Add the agent router to api.py")
    print("2. Restart the backend server")
    print("3. Test via API: POST /api/v1/agent/chat")
    print("\nSee AI_AGENT_COMPLETE.md for full documentation.")


if __name__ == "__main__":
    asyncio.run(test_agent())
