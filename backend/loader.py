import pandas as pd
from typing import Optional
from backend.tally_connector import TallyConnector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tally_import")

class LedgerLoader:
    """Class to load Tally ledger/voucher data from live Tally or fallback CSV/XLSX."""
    @staticmethod
    def load_csv(path: str, **kwargs) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(path, **kwargs)
            return df
        except Exception as e:
            logger.error(f"CSV load error: {e}")
            return None

    @staticmethod
    def load_xlsx(path: str, **kwargs) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_excel(path, **kwargs)
            return df
        except Exception as e:
            logger.error(f"XLSX load error: {e}")
            return None

    @staticmethod
    def load_tally_ledgers(company_name: str, tally_url: str = "http://localhost:9000", timeout: int = 15) -> Optional[pd.DataFrame]:
        try:
            tc = TallyConnector(url=tally_url, timeout=timeout, company_name=company_name)
            return tc.fetch_ledgers()
        except Exception as e:
            logger.error(f"Live Tally fetch_ledgers error: {e}")
            return None

    @staticmethod
    def load_tally_vouchers(company_name: str, voucher_type: Optional[str] = None, tally_url: str = "http://localhost:9000", timeout: int = 15) -> Optional[pd.DataFrame]:
        try:
            tc = TallyConnector(url=tally_url, timeout=timeout, company_name=company_name)
            return tc.fetch_vouchers(voucher_type=voucher_type)
        except Exception as e:
            logger.error(f"Live Tally fetch_vouchers error: {e}")
            return None
