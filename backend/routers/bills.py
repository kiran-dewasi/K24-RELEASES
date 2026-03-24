from fastapi import APIRouter, Depends
from dependencies import get_api_key
from tally_connector import TallyConnector
# Reuse global tally instance logic or new one
# Ideally we import 'tally' from api.py but that causes circular import.
# We'll instantiate a connector or use a service.
import os

router = APIRouter(prefix="/api/bills", tags=["bills"])

@router.get("/receivables", dependencies=[Depends(get_api_key)])
async def get_receivables():
    """
    Get Outstanding Receivables.
    """
    # For now, return mock or empty list if DB logic isn't ready
    # Or fetch from TallyConnector
    try:
        url = os.getenv("TALLY_URL", "http://localhost:9000")
        company = os.getenv("TALLY_COMPANY", "Krishasales")
        connector = TallyConnector(url=url, company_name=company)
        
        df = connector.fetch_outstanding_bills()
        if df.empty:
            return {"bills": []}
            
        return {"bills": df.to_dict(orient="records")}
    except Exception as e:
        return {"bills": [], "error": str(e)}

@router.get("/payables", dependencies=[Depends(get_api_key)])
async def get_payables():
    """
    Get Outstanding Payables.
    """
    return {"bills": []} # Implement similarly
