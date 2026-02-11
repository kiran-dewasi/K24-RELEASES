"""
K24 Tally Sync Coverage Test
============================
Tests what IS and IS NOT being synced with Tally.

Run: python test_sync_coverage.py
Requires: Tally running on port 9000
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(name, status, count=None, error=None):
    if status == "pass":
        icon = "[OK]"
        msg = f"{count} records" if count else "OK"
    elif status == "fail":
        icon = "[X]"
        msg = f"NOT IMPLEMENTED"
    elif status == "error":
        icon = "[!]"
        msg = f"ERROR: {error}"
    elif status == "partial":
        icon = "[~]"
        msg = f"{count} records (partial)"
    else:
        icon = "[?]"
        msg = "Unknown"
    
    print(f"  {icon} {name.ljust(35)} {msg}")

def test_tally_connection():
    """Test basic Tally connectivity"""
    print_header("PHASE 1: CONNECTION TEST")
    
    try:
        import requests
        response = requests.get("http://localhost:9000", timeout=5)
        if response.status_code == 200:
            print_result("Tally Connection", "pass")
            return True
        else:
            print_result("Tally Connection", "error", error=f"HTTP {response.status_code}")
            return False
    except Exception as e:
        print_result("Tally Connection", "error", error=str(e))
        return False

def test_pull_from_tally():
    """Test all PULL operations"""
    print_header("PHASE 2: PULL FROM TALLY")
    
    results = {}
    
    # Test TallyConnector
    try:
        from backend.tally_connector import TallyConnector
        connector = TallyConnector()
        
        # Ledgers
        try:
            df = connector.fetch_ledgers()
            results["Ledgers (basic)"] = ("pass", len(df))
        except Exception as e:
            results["Ledgers (basic)"] = ("error", str(e))
        
        # Ledgers Full
        try:
            df = connector.fetch_ledgers_full()
            results["Ledgers (full)"] = ("pass", len(df))
        except Exception as e:
            results["Ledgers (full)"] = ("error", str(e))
        
        # Stock Items
        try:
            df = connector.fetch_stock_items()
            results["Stock Items"] = ("pass", len(df))
        except Exception as e:
            results["Stock Items"] = ("error", str(e))
        
        # Vouchers
        try:
            today = datetime.now()
            fy_start = datetime(today.year if today.month >= 4 else today.year - 1, 4, 1)
            df = connector.fetch_vouchers(
                from_date=fy_start.strftime("%Y%m%d"),
                to_date=today.strftime("%Y%m%d")
            )
            results["Vouchers"] = ("pass", len(df))
        except Exception as e:
            results["Vouchers"] = ("error", str(e))
        
        # Outstanding Bills
        try:
            df = connector.fetch_outstanding_bills()
            results["Outstanding Bills"] = ("pass", len(df))
        except Exception as e:
            results["Outstanding Bills"] = ("error", str(e))
        
    except ImportError as e:
        results["TallyConnector Import"] = ("error", str(e))
    
    # Test TallyReader
    try:
        from backend.tally_reader import TallyReader
        reader = TallyReader()
        
        # Receivables
        try:
            data = reader.get_receivables()
            results["Receivables (Debtors)"] = ("pass", len(data))
        except Exception as e:
            results["Receivables (Debtors)"] = ("error", str(e))
        
        # Payables
        try:
            data = reader.get_payables()
            results["Payables (Creditors)"] = ("pass", len(data))
        except Exception as e:
            results["Payables (Creditors)"] = ("error", str(e))
        
        # Cash/Bank
        try:
            balance = reader.get_cash_bank_balance()
            results["Cash & Bank Balance"] = ("pass", f"Rs.{balance:,.2f}")
        except Exception as e:
            results["Cash & Bank Balance"] = ("error", str(e))
        
        # Godowns
        try:
            data = reader.get_godowns()
            results["Godowns"] = ("pass", len(data))
        except Exception as e:
            results["Godowns"] = ("error", str(e))
        
        # Stock Summary
        try:
            data = reader.get_stock_summary()
            results["Stock Summary"] = ("pass", len(data))
        except Exception as e:
            results["Stock Summary"] = ("error", str(e))
        
        # Transactions
        try:
            today = datetime.now()
            fy_start = datetime(today.year if today.month >= 4 else today.year - 1, 4, 1)
            data = reader.get_transactions(
                fy_start.strftime("%Y%m%d"),
                today.strftime("%Y%m%d")
            )
            results["Transactions (Full)"] = ("pass", len(data))
        except Exception as e:
            results["Transactions (Full)"] = ("error", str(e))
        
        # Tax Summary
        try:
            today = datetime.now()
            start = (today - timedelta(days=30)).strftime("%Y%m%d")
            end = today.strftime("%Y%m%d")
            data = reader.get_tax_summary(start, end)
            results["Tax Summary (GST)"] = ("pass", "calculated")
        except Exception as e:
            results["Tax Summary (GST)"] = ("error", str(e))
        
    except ImportError as e:
        results["TallyReader Import"] = ("error", str(e))
    
    # Print results
    for name, (status, detail) in results.items():
        if status == "pass":
            print_result(name, "pass", count=detail)
        elif status == "error":
            print_result(name, "error", error=detail)
    
    return results

def test_missing_pull():
    """Test what's NOT implemented for pull"""
    print_header("PHASE 3: MISSING PULL FUNCTIONS")
    
    missing = [
        ("fetch_cost_centers()", "Cost Center tracking"),
        ("fetch_cost_categories()", "Cost allocation"),
        ("fetch_currencies()", "Multi-currency support"),
        ("fetch_units_of_measure()", "Stock unit validation"),
        ("fetch_opening_balances()", "FY start balances"),
        ("fetch_stock_groups()", "Item categorization"),
        ("fetch_voucher_types()", "Custom voucher types"),
        ("fetch_batch_details()", "Batch tracking"),
        ("fetch_budgets()", "Budgeting feature"),
    ]
    
    for func, purpose in missing:
        print_result(func, "fail")
    
    return len(missing)

def test_push_to_tally():
    """Test PUSH capabilities (without actually pushing)"""
    print_header("PHASE 4: PUSH TO TALLY (Capability Check)")
    
    results = {}
    
    # Check TallyConnector push methods
    try:
        from backend.tally_connector import TallyConnector
        connector = TallyConnector()
        
        # Check if methods exist
        methods = [
            ("create_ledger_if_missing", "Create Ledger"),
            ("create_voucher", "Create Voucher (Legacy)"),
            ("delete_voucher", "Delete Voucher"),
            ("push_xml", "Push Raw XML"),
        ]
        
        for method, name in methods:
            if hasattr(connector, method):
                results[name] = ("pass", "Available")
            else:
                results[name] = ("fail", "Not found")
    
    except ImportError as e:
        results["TallyConnector"] = ("error", str(e))
    
    # Check tally_live_update
    try:
        from backend.tally_live_update import (
            create_ledger_safely,
            create_voucher_safely,
            post_to_tally
        )
        results["Create Ledger (Safe)"] = ("pass", "Available")
        results["Create Voucher (Safe)"] = ("pass", "Available")
        results["Post to Tally (Generic)"] = ("pass", "Available")
    except ImportError as e:
        results["tally_live_update"] = ("error", str(e))
    
    # Check TallyEngine
    try:
        from backend.tally_engine import TallyEngine
        engine = TallyEngine()
        
        methods = [
            ("ensure_ledger_exists", "Ensure Ledger"),
            ("ensure_stock_item", "Ensure Stock Item"),
            ("process_voucher", "Process Voucher"),
            ("process_sales_request", "Sales Voucher"),
            ("process_purchase_request", "Purchase Voucher"),
            ("process_financial_voucher", "Financial Voucher"),
        ]
        
        for method, name in methods:
            if hasattr(engine, method):
                results[name] = ("pass", "Available")
            else:
                results[name] = ("fail", "Not found")
    
    except ImportError as e:
        results["TallyEngine"] = ("error", str(e))
    
    # Print results
    for name, (status, detail) in results.items():
        if status == "pass":
            print_result(name, "pass", count=detail)
        elif status == "error":
            print_result(name, "error", error=detail)
        else:
            print_result(name, "fail")
    
    return results

def test_missing_push():
    """Test what's NOT implemented for push"""
    print_header("PHASE 5: MISSING PUSH FUNCTIONS")
    
    missing = [
        ("update_ledger()", "Edit party details"),
        ("update_voucher()", "Modify entries"),
        ("create_stock_group()", "Organize inventory"),
        ("create_godown()", "Add warehouses"),
        ("create_cost_center()", "Project tracking"),
        ("create_stock_adjustment()", "Physical stock"),
        ("create_journal_voucher()", "Accounting entries"),
        ("create_debit_note()", "Sales returns"),
        ("create_credit_note()", "Purchase returns"),
    ]
    
    for func, purpose in missing:
        print_result(func, "fail")
    
    return len(missing)

def test_sync_engine():
    """Test sync engine completeness"""
    print_header("PHASE 6: SYNC ENGINE STATUS")
    
    results = {}
    
    try:
        from backend.sync_engine import SyncEngine
        engine = SyncEngine()
        
        # Check what's implemented
        if hasattr(engine, 'push_voucher_safe'):
            results["push_voucher_safe()"] = ("pass", "Implemented")
        else:
            results["push_voucher_safe()"] = ("fail", None)
        
        # Check what's placeholder
        if hasattr(engine, 'sync_now'):
            # Check if it's just a placeholder
            import inspect
            source = inspect.getsource(engine.sync_now)
            if "TODO" in source or "placeholder" in source.lower():
                results["sync_now()"] = ("partial", "Placeholder only")
            else:
                results["sync_now()"] = ("pass", "Implemented")
        else:
            results["sync_now()"] = ("fail", None)
        
        # Missing methods
        missing = [
            "pull_ledgers",
            "pull_vouchers", 
            "pull_stock_items",
            "incremental_sync",
            "full_sync",
            "replay_offline_queue",
        ]
        
        for method in missing:
            if hasattr(engine, method):
                results[method + "()"] = ("pass", "Implemented")
            else:
                results[method + "()"] = ("fail", None)
    
    except ImportError as e:
        results["SyncEngine Import"] = ("error", str(e))
    
    # Print results
    for name, (status, detail) in results.items():
        if status == "pass":
            print_result(name, "pass", count=detail)
        elif status == "partial":
            print_result(name, "partial", count=detail)
        elif status == "error":
            print_result(name, "error", error=detail)
        else:
            print_result(name, "fail")
    
    return results

def calculate_summary(pull_results, pull_missing, push_results, sync_results):
    """Calculate overall coverage"""
    print_header("FINAL SUMMARY")
    
    # Count results
    pull_pass = sum(1 for r in pull_results.values() if r[0] == "pass")
    pull_total = pull_pass + pull_missing
    
    push_pass = sum(1 for r in push_results.values() if r[0] == "pass")
    push_missing_count = 9  # From test_missing_push
    push_total = push_pass + push_missing_count
    
    sync_pass = sum(1 for r in sync_results.values() if r[0] == "pass")
    sync_total = len(sync_results)
    
    overall_pass = pull_pass + push_pass + sync_pass
    overall_total = pull_total + push_total + sync_total
    
    print(f"""
  +-------------------+-----------+---------+---------+
  |                  SYNC COVERAGE REPORT             |
  +-------------------+-----------+---------+---------+
  | Category          | Implemented | Missing | Coverage |
  +-------------------+-----------+---------+---------+
  | Pull (Tally->K24) | {pull_pass:^11} | {pull_missing:^7} | {pull_pass/pull_total*100:>6.1f}%  |
  | Push (K24->Tally) | {push_pass:^11} | {push_missing_count:^7} | {push_pass/push_total*100:>6.1f}%  |
  | Sync Engine       | {sync_pass:^11} | {sync_total-sync_pass:^7} | {sync_pass/sync_total*100:>6.1f}%  |
  +-------------------+-----------+---------+---------+
  | TOTAL             | {overall_pass:^11} | {overall_total-overall_pass:^7} | {overall_pass/overall_total*100:>6.1f}%  |
  +-------------------+-----------+---------+---------+
""")
    
    # Recommendations
    print("  🎯 TOP PRIORITIES:")
    print("     1. Implement sync_now() full sync")
    print("     2. Add Units of Measure pull")
    print("     3. Implement update_ledger() and update_voucher()")
    print("     4. Add Stock Adjustments push")
    print("")

def main():
    print("""
+======================================================================+
|           K24 TALLY SYNC COVERAGE TEST                               |
|           Testing what IS and IS NOT being synced                    |
+======================================================================+
    """)
    
    # Phase 1: Connection
    if not test_tally_connection():
        print("\n❌ Cannot continue without Tally connection!")
        print("   Please ensure Tally is running on http://localhost:9000")
        sys.exit(1)
    
    # Phase 2: Pull
    pull_results = test_pull_from_tally()
    
    # Phase 3: Missing Pull
    pull_missing = test_missing_pull()
    
    # Phase 4: Push
    push_results = test_push_to_tally()
    
    # Phase 5: Missing Push
    test_missing_push()
    
    # Phase 6: Sync Engine
    sync_results = test_sync_engine()
    
    # Summary
    calculate_summary(pull_results, pull_missing, push_results, sync_results)
    
    print("📋 Full report: TALLY_SYNC_AUDIT.md")

if __name__ == "__main__":
    main()
