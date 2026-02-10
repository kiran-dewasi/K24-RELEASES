import pandas as pd
from typing import Any, Dict, Optional
import pickle
import os
from backend.tally_connector import TallyConnector
from xml.sax.saxutils import escape
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tally_import")

class LedgerCRUD:
    """
    Modular CRUD operations for Tally Ledger DataFrame.
    Designed for extensibility, logging, agent integration, persistence, and live Tally sync.
    If tally_connector is passed, all writes will also be pushed to Tally live.
    """

    def __init__(self, df: pd.DataFrame, id_col: str = "ID", tally_connector: TallyConnector = None, company_name: Optional[str] = None):
        self.df = df
        self.id_col = id_col
        self.tally_connector = tally_connector
        self.company_name = company_name

    def update_entry(self, entry_id: Any, updates: Dict[str, Any]) -> None:
        """
        Update specified columns for entry matching entry_id.
        Raises ValueError if not found. If tally_connector set, pushes update to Tally live.
        """
        idx = self.df[self.df[self.id_col] == entry_id].index
        if idx.empty:
            raise ValueError(f"No entry found for {self.id_col}={entry_id}")
        for col, val in updates.items():
            if col in self.df.columns:
                self.df.at[idx[0], col] = val
            else:
                raise KeyError(f"Column '{col}' not in DataFrame")
        if self.tally_connector and self.company_name:
            try:
                voucher_xml = self._entry_to_voucher_xml(self.df.loc[idx[0]])
                self.tally_connector.push_voucher(self.company_name, voucher_xml)
            except Exception as ex:
                logger.error(f"Failed to push update to Tally: {ex}")
        # Additional: log update here for audit/history

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """
        Add a new row to ledger. Entry must contain all required fields. Push to Tally if enabled.
        """
        missing_cols = set(self.df.columns) - set(entry.keys())
        if missing_cols:
            raise ValueError(f"Missing columns: {missing_cols}")
        self.df = pd.concat([self.df, pd.DataFrame([entry])], ignore_index=True)
        if self.tally_connector and self.company_name:
            try:
                voucher_xml = self._entry_to_voucher_xml(entry)
                self.tally_connector.push_voucher(self.company_name, voucher_xml)
            except Exception as ex:
                logger.error(f"Failed to push add to Tally: {ex}")

    def delete_entry(self, entry_id: Any) -> None:
        """
        Delete entry with matching ID. Push delete as Tally voucher if enabled (if business logic supports).
        """
        initial_count = len(self.df)
        idx = self.df[self.df[self.id_col] == entry_id].index
        self.df = self.df[self.df[self.id_col] != entry_id].reset_index(drop=True)
        if len(self.df) == initial_count:
            raise ValueError(f"No entry deleted. {self.id_col}={entry_id} not found.")
        if self.tally_connector and self.company_name and not idx.empty:
            try:
                voucher_xml = self._entry_to_delete_voucher_xml(entry_id)
                self.tally_connector.push_voucher(self.company_name, voucher_xml)
            except Exception as ex:
                logger.error(f"Failed to push delete to Tally: {ex}")

    def get_entry(self, entry_id: Any) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row as dict by ID.
        Returns None if not found.
        """
        row = self.df[self.df[self.id_col] == entry_id]
        if not row.empty:
            return row.iloc[0].to_dict()
        return None

    def save(self, path: str, format: str = "csv") -> None:
        """
        Persist the ledger to disk.
        Supports 'csv', 'xlsx'.
        """
        if format == "csv":
            self.df.to_csv(path, index=False)
        elif format == "xlsx":
            self.df.to_excel(path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def load(self, path: str, format: str = "csv") -> None:
        """
        Load/replace ledger from disk (hot swap for batch ops).
        """
        if format == "csv":
            self.df = pd.read_csv(path)
        elif format == "xlsx":
            self.df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _entry_to_voucher_xml(self, entry: Any) -> str:
        """Convert a DataFrame row or dict to <VOUCHER> XML suitable for Tally. Customize per schema needed."""
        # This must be tailored to your Tally XML schema. Minimal sketch below:
        xml = f'<VOUCHER><ID>{escape(str(entry["ID"]))}</ID>'
        for col, val in entry.items():
            if col != "ID":
                xml += f'<{escape(str(col))}>{escape(str(val))}</{escape(str(col))}>'
        xml += '</VOUCHER>'
        return xml

    def _entry_to_delete_voucher_xml(self, entry_id: Any) -> str:
        """Produce XML to inform Tally something should be deleted (customize as needed for your workflow)."""
        xml = f'<VOUCHER><ID>{entry_id}</ID><ACTION>Delete</ACTION></VOUCHER>'
        return xml


# Backward compatibility wrapper functions for existing api.py
def log_change(df: pd.DataFrame, log_path: str = "data_log.pkl"):
    """Save DataFrame to a pickle log for undo/checkpoints."""
    with open(log_path, "ab") as f:
        pickle.dump(df, f)


def undo_last_change(log_path: str = "data_log.pkl") -> pd.DataFrame:
    """Revert to previous DataFrame state from log."""
    if not os.path.exists(log_path):
        logger.warning("No log file found for undo.")
        return pd.DataFrame()
    try:
        states = []
        with open(log_path, "rb") as f:
            while True:
                try:
                    states.append(pickle.load(f))
                except EOFError:
                    break
        if len(states) > 1:
            # Remove latest state and keep previous
            states.pop()
            with open(log_path, "wb") as f:
                for s in states:
                    pickle.dump(s, f)
            return states[-1]
        elif states:
            logger.warning("Only initial state in log; cannot undo.")
            return states[0]
        else:
            logger.warning("Log is empty.")
            return pd.DataFrame()
    except Exception as e:
        logger.error(f"Undo error: {e}")
        return pd.DataFrame()


def add_entry(df: pd.DataFrame, entry: Dict[str, Any]) -> pd.DataFrame:
    """Backward compatibility: Add a new entry to the DataFrame."""
    try:
        # Try to use ID column if it exists, otherwise use first column
        id_col = "ID" if "ID" in df.columns else df.columns[0]
        crud = LedgerCRUD(df, id_col=id_col)
        # Fill missing columns with None/NaN to satisfy the requirement
        complete_entry = {col: entry.get(col, None) for col in df.columns}
        crud.add_entry(complete_entry)
        # The dataframe is modified in-place via crud.df reference
        return crud.df
    except Exception as e:
        logger.error(f"Add entry error: {e}")
        # Fallback to old method - just add what's provided
        new_df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        return new_df


def update_entry(df: pd.DataFrame, idx: int, updates: Dict[str, Any]) -> pd.DataFrame:
    """Backward compatibility: Update entry at index idx with updates."""
    try:
        # If ID column exists, use it; otherwise use index directly
        if "ID" in df.columns and idx < len(df):
            entry_id = df.iloc[idx]["ID"]
            crud = LedgerCRUD(df, id_col="ID")
            crud.update_entry(entry_id, updates)
            # The dataframe is modified in-place via crud.df reference
            return crud.df
        else:
            # Fallback to old method using index
            for key, value in updates.items():
                if key in df.columns:
                    df.at[idx, key] = value
            return df
    except Exception as e:
        logger.error(f"Update entry error: {e}")
        # Fallback to old method
        for key, value in updates.items():
            if key in df.columns:
                df.at[idx, key] = value
        return df


def delete_entry(df: pd.DataFrame, idx: int) -> pd.DataFrame:
    """Backward compatibility: Delete entry at index idx."""
    try:
        # If ID column exists, use it; otherwise use index directly
        if "ID" in df.columns and idx < len(df):
            entry_id = df.iloc[idx]["ID"]
            crud = LedgerCRUD(df, id_col="ID")
            crud.delete_entry(entry_id)
            # The dataframe is modified in-place via crud.df reference
            return crud.df
        else:
            # Fallback to old method using index
            new_df = df.drop(idx).reset_index(drop=True)
            return new_df
    except Exception as e:
        logger.error(f"Delete entry error: {e}")
        # Fallback to old method
        new_df = df.drop(idx).reset_index(drop=True)
        return new_df
