"""
Ledger Service - Tally-like Automatic Ledger Management

This service implements the core "Create Once, Use Forever" pattern:
- When a ledger name is referenced in any voucher, we auto-create if missing
- Existing ledgers are reused (case-insensitive matching)
- No duplicate ledgers are ever created
- Mimics Tally's seamless ledger management

Usage:
    from backend.services.ledger_service import LedgerService
    ledger_service = LedgerService(db)
    ledger_id = await ledger_service.get_or_create_ledger("Customer ABC", "Sundry Debtors")
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import Ledger, get_db
from backend.tally_engine import TallyEngine

logger = logging.getLogger("LedgerService")


class LedgerService:
    """
    Centralized Ledger Service implementing Tally-like auto-creation behavior.
    """
    
    def __init__(self, db: Session, tally_engine: Optional[TallyEngine] = None):
        self.db = db
        self.tally_engine = tally_engine or TallyEngine()
    
    def get_or_create_ledger(
        self,
        ledger_name: str,
        under_group: Optional[str] = None,
        ledger_type: Optional[str] = None,
        voucher_type: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default"
    ) -> Optional[int]:
        """
        Get existing ledger or auto-create new one.
        
        TALLY-LIKE BEHAVIOR:
        1. Search for existing ledger (case-insensitive, trimmed)
        2. If found -> return existing ledger ID
        3. If not found -> auto-create with smart defaults
        4. NEVER ask user to create ledger again
        
        Args:
            ledger_name: The ledger name (customer/vendor/account name)
            under_group: Parent group (e.g., "Sundry Debtors", "Sundry Creditors")
            ledger_type: Type classification (customer, supplier, bank, etc.)
            voucher_type: Context from voucher for smart inference
            additional_data: Extra fields like GSTIN, address, etc.
            tenant_id: Multi-tenant support
            
        Returns:
            Ledger ID (integer) or None if creation failed
        """
        if not ledger_name or not ledger_name.strip():
            logger.warning("Empty ledger name provided, skipping")
            return None
            
        # Normalize the name
        normalized_name = ledger_name.strip()
        
        # 1. SEARCH FOR EXISTING LEDGER (Case-insensitive)
        existing_ledger = self._find_existing_ledger(normalized_name, tenant_id)
        
        if existing_ledger:
            logger.info(f"✅ Ledger EXISTS: '{existing_ledger.name}' (ID: {existing_ledger.id})")
            return existing_ledger.id
        
        # 2. AUTO-CREATE NEW LEDGER
        logger.info(f"🆕 Creating new ledger: '{normalized_name}'")
        
        # Smart Group Inference
        if not under_group:
            under_group = self._infer_group_from_context(normalized_name, voucher_type)
        
        # Smart Type Inference  
        if not ledger_type:
            ledger_type = self._infer_type_from_context(normalized_name, under_group, voucher_type)
        
        # Create in Database
        new_ledger = self._create_ledger_in_db(
            name=normalized_name,
            under_group=under_group,
            ledger_type=ledger_type,
            additional_data=additional_data or {},
            tenant_id=tenant_id
        )
        
        if new_ledger:
            # Also create in Tally (async safe)
            try:
                self._sync_ledger_to_tally(new_ledger)
            except Exception as e:
                logger.warning(f"Tally sync failed for ledger '{normalized_name}': {e}")
                # Don't fail - local ledger is created, Tally sync can retry later
            
            logger.info(f"✅ Ledger CREATED: '{new_ledger.name}' (ID: {new_ledger.id}) under '{under_group}'")
            return new_ledger.id
        
        logger.error(f"❌ Failed to create ledger: '{normalized_name}'")
        return None
    
    def _find_existing_ledger(self, name: str, tenant_id: str) -> Optional[Ledger]:
        """
        Find existing ledger by name (case-insensitive) or alias.
        Follows Tally's matching priority:
        1. Exact name match (case-insensitive)
        2. Alias match
        3. Tally GUID match (if syncing)
        """
        # Case-insensitive name search
        ledger = self.db.query(Ledger).filter(
            Ledger.tenant_id == tenant_id,
            func.lower(Ledger.name) == func.lower(name.strip()),
            Ledger.is_active != False
        ).first()
        
        if ledger:
            return ledger
        
        # Try alias match
        ledger = self.db.query(Ledger).filter(
            Ledger.tenant_id == tenant_id,
            func.lower(Ledger.alias) == func.lower(name.strip()),
            Ledger.is_active != False
        ).first()
        
        return ledger
    
    def _infer_group_from_context(self, name: str, voucher_type: Optional[str] = None) -> str:
        """
        Smart inference of ledger group based on name and context.
        
        Heuristics:
        - Sales vouchers -> party is probably "Sundry Debtors" (customer)
        - Purchase vouchers -> party is probably "Sundry Creditors" (vendor)
        - Name contains "bank" -> "Bank Accounts"
        - Name is "cash" -> "Cash-in-Hand"
        - Default -> "Sundry Debtors"
        """
        name_lower = name.lower().strip()
        
        # Name-based inference (highest priority)
        if name_lower == 'cash' or name_lower == 'cash in hand' or name_lower == 'cash account':
            return 'Cash-in-Hand'
        
        if 'bank' in name_lower:
            return 'Bank Accounts'
        
        if any(keyword in name_lower for keyword in ['expense', 'rent', 'salary', 'electricity', 'telephone']):
            return 'Indirect Expenses'
        
        if any(keyword in name_lower for keyword in ['sales', 'income', 'revenue']):
            return 'Sales Accounts'
        
        if any(keyword in name_lower for keyword in ['purchase', 'cost']):
            return 'Purchase Accounts'
        
        # Voucher-type based inference
        if voucher_type:
            vtype = voucher_type.lower()
            
            if vtype in ['sales', 'receipt', 'debit note']:
                return 'Sundry Debtors'  # Customer
            
            if vtype in ['purchase', 'payment', 'credit note']:
                return 'Sundry Creditors'  # Vendor
        
        # Default: Sundry Debtors (most common case - customers)
        return 'Sundry Debtors'
    
    def _infer_type_from_context(
        self, 
        name: str, 
        group: str, 
        voucher_type: Optional[str] = None
    ) -> str:
        """
        Infer ledger type from group and context.
        """
        group_lower = group.lower() if group else ""
        
        if 'debtor' in group_lower:
            return 'customer'
        if 'creditor' in group_lower:
            return 'supplier'
        if 'bank' in group_lower:
            return 'bank'
        if 'cash' in group_lower:
            return 'cash'
        if 'expense' in group_lower:
            return 'expense'
        if 'income' in group_lower or 'sales' in group_lower:
            return 'income'
        if 'purchase' in group_lower:
            return 'expense'
        
        return 'other'
    
    def _create_ledger_in_db(
        self,
        name: str,
        under_group: str,
        ledger_type: str,
        additional_data: Dict[str, Any],
        tenant_id: str
    ) -> Optional[Ledger]:
        """
        Create ledger record in the database.
        """
        try:
            new_ledger = Ledger(
                tenant_id=tenant_id,
                name=name,
                parent=under_group,  # 'parent' maps to 'under_group' in our schema
                ledger_type=ledger_type,
                created_from='Auto',  # Mark as auto-created
                is_active=True,
                opening_balance=0.0,
                closing_balance=0.0,
                # Optional fields from additional_data
                alias=additional_data.get('alias'),
                gstin=additional_data.get('gstin'),
                pan=additional_data.get('pan'),
                address=additional_data.get('address'),
                city=additional_data.get('city'),
                state=additional_data.get('state'),
                pincode=additional_data.get('pincode'),
                phone=additional_data.get('phone'),
                email=additional_data.get('email'),
                contact_person=additional_data.get('contact_person'),
                credit_limit=additional_data.get('credit_limit'),
                credit_days=additional_data.get('credit_days'),
                tally_guid=additional_data.get('tally_guid'),
            )
            
            self.db.add(new_ledger)
            self.db.commit()
            self.db.refresh(new_ledger)
            
            return new_ledger
            
        except Exception as e:
            logger.error(f"Database error creating ledger '{name}': {e}")
            self.db.rollback()
            return None
    
    def _sync_ledger_to_tally(self, ledger: Ledger) -> bool:
        """
        Sync the newly created ledger to Tally.
        Uses the existing TallyEngine.ensure_ledger_exists pattern.
        """
        try:
            result = self.tally_engine.ensure_ledger_exists(
                name=ledger.name,
                group=ledger.parent,
                gstin=ledger.gstin
            )
            return result is not None
        except Exception as e:
            logger.warning(f"Tally sync failed for ledger: {e}")
            return False
    
    def search_ledgers(
        self,
        query: str,
        tenant_id: str = "default",
        ledger_type: Optional[str] = None,
        limit: int = 10
    ) -> list:
        """
        Search ledgers for autocomplete functionality.
        
        Returns list of matching ledgers for dropdown suggestions.
        """
        if not query or len(query) < 2:
            return []
        
        base_query = self.db.query(Ledger).filter(
            Ledger.tenant_id == tenant_id,
            Ledger.is_active != False,
            Ledger.name.ilike(f"%{query}%")
        )
        
        if ledger_type:
            base_query = base_query.filter(Ledger.ledger_type == ledger_type)
        
        ledgers = base_query.order_by(Ledger.name).limit(limit).all()
        
        return [
            {
                "id": l.id,
                "name": l.name,
                "group": l.parent,
                "type": l.ledger_type,
                "balance": l.closing_balance,
                "gstin": l.gstin
            }
            for l in ledgers
        ]
    
    def get_ledger_by_id(self, ledger_id: int) -> Optional[Ledger]:
        """Get ledger by ID."""
        return self.db.query(Ledger).filter(Ledger.id == ledger_id).first()
    
    def get_ledger_by_name(self, name: str, tenant_id: str = "default") -> Optional[Ledger]:
        """Get ledger by name (case-insensitive)."""
        return self._find_existing_ledger(name, tenant_id)


# Convenience function for quick access without instantiation
def get_or_create_ledger(
    db: Session,
    ledger_name: str,
    under_group: Optional[str] = None,
    voucher_type: Optional[str] = None,
    tenant_id: str = "default"
) -> Optional[int]:
    """
    Quick function to get or create a ledger.
    
    Example:
        ledger_id = get_or_create_ledger(db, "ABC Traders", voucher_type="Sales")
    """
    service = LedgerService(db)
    return service.get_or_create_ledger(
        ledger_name=ledger_name,
        under_group=under_group,
        voucher_type=voucher_type,
        tenant_id=tenant_id
    )
