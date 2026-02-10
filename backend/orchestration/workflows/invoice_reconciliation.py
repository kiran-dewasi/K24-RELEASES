"""
Invoice Reconciliation Workflow
Autonomous workflow to detect and fix invoice discrepancies
"""
from typing import Dict, Any, List
import pandas as pd
import logging
import os
from backend.orchestration.base_workflow import BaseWorkflow, WorkflowResult
from backend.tally_connector import TallyConnector
from backend.tally_live_update import dispatch_tally_update, TallyAPIError

logger = logging.getLogger(__name__)

class InvoiceReconciliationWorkflow(BaseWorkflow):
    """
    Workflow to reconcile invoices by detecting and fixing discrepancies.
    """

    def execute(self, party_name: str, company: str = "SHREE JI SALES", tally_url: str = "http://localhost:9000", auto_approve: bool = False) -> WorkflowResult:
        """
        Execute reconciliation workflow.
        """
        logger.info(f"Starting reconciliation for '{party_name}'...")
        
        # Step 1: Fetch data
        ledger_data = self.fetch_ledger_entries(party_name, company, tally_url)
        logger.info(f"Found {len(ledger_data)} ledger entries")
        
        if ledger_data.empty:
            return WorkflowResult(
                status="no_data",
                message=f"No ledger entries found for '{party_name}'"
            )
        
        # Step 2: Detect issues
        discrepancies = self.detect_discrepancies(ledger_data)
        total_issues = sum(len(v) for v in discrepancies.values())
        logger.info(f"Detected {total_issues} potential issues")
        
        # Step 3: Generate fixes
        suggested_fixes = self.generate_fixes(discrepancies)
        logger.info(f"Generated {len(suggested_fixes)} suggested fixes")
        
        # Step 4: Return results (approval/application)
        if total_issues == 0:
            return WorkflowResult(
                status="clean",
                message="No issues detected - ledger is clean!",
                data={"entries_analyzed": len(ledger_data)}
            )
        
        if not auto_approve:
            return WorkflowResult(
                status="pending_approval",
                message=f"Found {total_issues} issues. Please review.",
                data={
                    "party": party_name,
                    "issues_found": total_issues,
                    "fixes_suggested": len(suggested_fixes),
                    "discrepancies": discrepancies,
                    "fixes": suggested_fixes,
                    "entries_analyzed": len(ledger_data)
                }
            )
        
        # Step 5: Auto-approve
        logger.info("Auto-approval enabled - applying fixes...")
        tally_live_enabled = os.getenv("TALLY_LIVE_UPDATE_ENABLED", "false").lower() == "true"
        
        application_result = self.apply_fixes_to_tally(
            fixes=suggested_fixes,
            company=company,
            tally_url=tally_url,
            enabled=tally_live_enabled
        )
        
        return WorkflowResult(
            status="complete",
            message=f"Applied {application_result.get('applied', 0)} fixes.",
            data={
                "party": party_name,
                "issues_found": total_issues,
                "fixes_applied": application_result.get("applied", 0),
                "fixes_failed": application_result.get("failed", 0),
                "fixes_skipped": application_result.get("skipped", 0),
                "application_details": application_result
            }
        )

    def fetch_ledger_entries(self, party_name: str, company: str, tally_url: str) -> pd.DataFrame:
        try:
            connector = TallyConnector(url=tally_url, company_name=company)
            df = connector.fetch_ledgers_full(company)
            
            if 'NAME' in df.columns:
                return df[df['NAME'].str.contains(party_name, case=False, na=False)]
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching ledger entries: {e}")
            raise

    def detect_discrepancies(self, df: pd.DataFrame) -> Dict[str, List[Dict]]:
        discrepancies = {
            "duplicates": [],
            "missing_gstin": [],
            "missing_parent": [],
            "invalid_data": []
        }
        
        if df.empty: return discrepancies
        
        if 'NAME' in df.columns:
            duplicates = df[df.duplicated(subset=['NAME'], keep=False)]
            if not duplicates.empty:
                discrepancies["duplicates"] = duplicates.to_dict('records')
        
        if 'GSTIN' in df.columns:
            missing_gstin = df[df['GSTIN'].isna() | (df['GSTIN'] == '')]
            if not missing_gstin.empty:
                discrepancies["missing_gstin"] = missing_gstin.to_dict('records')
        
        if 'PARENT' in df.columns:
            missing_parent = df[df['PARENT'].isna() | (df['PARENT'] == '')]
            if not missing_parent.empty:
                discrepancies["missing_parent"] = missing_parent.to_dict('records')
        
        return discrepancies

    def generate_fixes(self, discrepancies: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        fixes = []
        
        for entry in discrepancies.get("missing_gstin", []):
            fixes.append({
                "type": "update",
                "ledger_id": entry.get('ID'),
                "ledger_name": entry.get('NAME'),
                "field": "GSTIN",
                "current_value": entry.get('GSTIN', ''),
                "suggested_value": "PENDING_VERIFICATION",
                "reason": "Missing GSTIN",
                "priority": "high"
            })
        
        for entry in discrepancies.get("missing_parent", []):
            fixes.append({
                "type": "update",
                "ledger_id": entry.get('ID'),
                "ledger_name": entry.get('NAME'),
                "field": "PARENT",
                "current_value": entry.get('PARENT', ''),
                "suggested_value": "Sundry Debtors",
                "reason": "Missing parent group",
                "priority": "high"
            })
            
        return fixes

    def apply_fixes_to_tally(self, fixes: List[Dict[str, Any]], company: str, tally_url: str, enabled: bool = True) -> Dict[str, Any]:
        if not enabled:
            return {"dry_run": True, "applied": 0, "failed": 0, "skipped": len(fixes)}
        
        results = {"applied": [], "failed": [], "skipped": []}
        
        for fix in fixes:
            if fix.get("type") != "update":
                results["skipped"].append(fix)
                continue
            
            try:
                updates = {fix["field"]: fix["suggested_value"]}
                if fix["field"] == "PARENT":
                    updates["NAME"] = fix["ledger_name"]
                
                response = dispatch_tally_update(
                    entity_type="ledger",
                    company_name=company,
                    payload={"action": "alter", "name": fix["ledger_name"], "updates": updates},
                    tally_url=tally_url
                )
                results["applied"].append({"ledger": fix["ledger_name"], "response": response})
            except Exception as e:
                results["failed"].append({"ledger": fix["ledger_name"], "error": str(e)})
                
        return results

# Wrapper for backward compatibility
def reconcile_invoices_workflow(party_name: str, company: str = "SHREE JI SALES", tally_url: str = "http://localhost:9000", auto_approve: bool = False) -> Dict[str, Any]:
    workflow = InvoiceReconciliationWorkflow()
    result = workflow.run(party_name=party_name, company=company, tally_url=tally_url, auto_approve=auto_approve)
    
    # Convert WorkflowResult back to dict format expected by API
    response = result.dict()
    # Flatten data into top level for API compatibility if needed, or just return data
    if result.data:
        response.update(result.data)
    
    return response
