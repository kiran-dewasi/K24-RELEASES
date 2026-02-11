import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestration.workflows.invoice_reconciliation import reconcile_invoices_workflow
import json

def test_reconciliation():
    print("Testing Invoice Reconciliation Workflow (Refactored)...")
    
    # Test with a dummy party
    result = reconcile_invoices_workflow(
        party_name="Test Party",
        company="SHREE JI SALES",
        tally_url="http://localhost:9000",
        auto_approve=False
    )
    
    print("\nWorkflow Result:")
    print(json.dumps(result, indent=2))
    
    # Check if result has expected keys
    assert "status" in result
    assert "message" in result
    
    print("\n✅ Test Passed!")

if __name__ == "__main__":
    test_reconciliation()
