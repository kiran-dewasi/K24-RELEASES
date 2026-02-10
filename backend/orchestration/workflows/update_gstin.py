from typing import Dict, Any
import re
import logging
from backend.orchestration.base_workflow import BaseWorkflow, WorkflowResult
from backend.tally_connector import TallyConnector
from backend.tally_live_update import dispatch_tally_update, TallyAPIError

logger = logging.getLogger(__name__)

class GSTINUpdateWorkflow(BaseWorkflow):
    """
    Workflow to update GSTIN for a party in Tally.
    """
    
    GSTIN_REGEX = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"

    def execute(self, party_name: str, new_gstin: str, company: str = "SHREE JI SALES", tally_url: str = "http://localhost:9000") -> WorkflowResult:
        """
        Execute the GSTIN update workflow.
        
        Args:
            party_name: Name of the party/ledger
            new_gstin: New GSTIN to set
            company: Tally company name
            tally_url: Tally API URL
            
        Returns:
            WorkflowResult
        """
        # 1. Validate GSTIN format
        if not re.match(self.GSTIN_REGEX, new_gstin):
            return WorkflowResult(
                status="failed",
                message=f"Invalid GSTIN format: {new_gstin}. Please provide a valid 15-character GSTIN."
            )
            
        try:
            # Skip party check (Tally EDU mode may restrict certain queries)
            # Just try to update directly - Tally will return error if party doesn't exist
            connector = TallyConnector(url=tally_url, company_name=company)
            ledger_name = party_name
                
            # 3. Update Tally
            logger.info(f"Attempting to update GSTIN for '{ledger_name}' to '{new_gstin}'")
            
            updates = {
                "GSTIN": new_gstin  # Correct field name from LEDGER_ALLOWED_FIELDS
            }
            
            response = dispatch_tally_update(
                entity_type="ledger",
                company_name=company,
                payload={
                    "ledger_name": ledger_name,  # Required parameter
                    "updates": updates
                },
                tally_url=tally_url
            )
            
            return WorkflowResult(
                status="success",
                message=f"Successfully updated GSTIN for '{ledger_name}' to '{new_gstin}'",
                data={"response": response.to_dict()}
            )
            
        except TallyAPIError as e:
            return WorkflowResult(
                status="failed",
                message=f"Tally API Error: {str(e)}",
                error=str(e)
            )
        except Exception as e:
            logger.exception("GSTIN update failed")
            return WorkflowResult(
                status="failed",
                message=f"An unexpected error occurred: {str(e)}",
                error=str(e)
            )

# Standalone function for backward compatibility/easier import if needed
def update_gstin_workflow(party_name: str, new_gstin: str, company: str = "SHREE JI SALES", tally_url: str = "http://localhost:9000") -> Dict[str, Any]:
    workflow = GSTINUpdateWorkflow()
    result = workflow.run(party_name=party_name, new_gstin=new_gstin, company=company, tally_url=tally_url)
    return result.dict()
