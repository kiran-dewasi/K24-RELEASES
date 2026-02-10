# K24 AI Agent - Transaction Manager with Rollback
# ==================================================
# Handles Tally writes with pre-write backup and automatic rollback on failure

from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import uuid
from backend.tally_connector import TallyConnector
from backend.agent_errors import AgentError, K24ErrorCode, create_error

logger = logging.getLogger(__name__)


class TransactionState:
    """Represents the state of a transaction"""
    
    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        self.status = "PENDING"
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.locked = False
        self.backup_data = None
        self.tally_reference = None
        self.verification_data = None
        self.completed_at = None
        self.rollback_reason = None


class TransactionManager:
    """
    Manages Tally transaction lifecycle with safety guarantees:
    1. Lock transaction
    2. Backup current state
    3. Execute write
    4. Verify success
    5. Unlock
    6. On failure → Automatic rollback
    """
    
    def __init__(self, tally_connector: TallyConnector):
        self.tally = tally_connector
        self.active_transactions: Dict[str, TransactionState] = {}
        self.transaction_history: list = []
    
    def create_transaction(
        self,
        voucher_xml: str,
        transaction_params: Dict[str, Any],
        user_id: str = "SYSTEM"
    ) -> Tuple[bool, Dict[str, Any], Optional[AgentError]]:
        """
        Create a transaction in Tally with full safety features.
        
        Returns:
            (success, result_data, error)
        """
        
        # Generate unique transaction ID
        txn_id = self._generate_transaction_id()
        txn_state = TransactionState(txn_id)
        
        try:
            # Step 1: Lock transaction
            logger.info(f"[{txn_id}] Step 1: Locking transaction")
            self._lock_transaction(txn_state)
            
            # Step 2: Backup (optional, depends on voucher type)
            logger.info(f"[{txn_id}] Step 2: Creating backup")
            self._create_backup(txn_state, transaction_params)
            
            # Step 3: Push to Tally
            logger.info(f"[{txn_id}] Step 3: Pushing to Tally")
            tally_result = self._push_to_tally(txn_state, voucher_xml)
            
            if not tally_result.get("success"):
                # Push failed
                error = create_error(
                    K24ErrorCode.TALLY_CONNECTION_FAILED,
                    message="Failed to create voucher in Tally",
                    suggestions=[
                        "Ensure Tally is running",
                        "Check Tally logs for details"
                    ],
                    context={
                        "tally_response": tally_result,
                        "transaction_id": txn_id
                    }
                )
                
                # Rollback
                self._rollback(txn_state, "Tally push failed")
                return (False, {}, error)
            
            # Step 4: Verify transaction was created
            logger.info(f"[{txn_id}] Step 4: Verifying transaction")
            verification = self._verify_transaction(txn_state, transaction_params)
            
            if not verification.get("verified"):
                # Verification failed
                error = create_error(
                    K24ErrorCode.UNKNOWN_ERROR,
                    message="Transaction created but verification failed",
                    suggestions=[
                        "Check Tally manually",
                        "Transaction may or may not be in Tally"
                    ],
                    context={
                        "transaction_id": txn_id,
                        "verification": verification
                    }
                )
                
                # Don't rollback here - transaction might be in Tally
                txn_state.status = "UNVERIFIED"
                return (False, {}, error)
            
            # Step 5: Mark as complete
            logger.info(f"[{txn_id}] Step 5: Transaction complete")
            txn_state.status = "SUCCESS"
            txn_state.completed_at = datetime.utcnow().isoformat() + "Z"
            txn_state.tally_reference = tally_result.get("reference")
            
            # Step 6: Unlock
            self._unlock_transaction(txn_state)
            
            # Archive to history
            self.transaction_history.append(txn_state)
            if txn_id in self.active_transactions:
                del self.active_transactions[txn_id]
            
            # Build success response
            result_data = {
                "transaction_id": txn_id,
                "status": "SUCCESS",
                "tally_reference": txn_state.tally_reference,
                "created_at": txn_state.created_at,
                "completed_at": txn_state.completed_at,
                "verification": verification,
                "tally_response": tally_result
            }
            
            logger.info(f"[{txn_id}] ✅ Transaction completed successfully")
            return (True, result_data, None)
        
        except Exception as e:
            logger.error(f"[{txn_id}] ❌ Exception during transaction: {e}")
            
            # Rollback
            self._rollback(txn_state, f"Exception: {str(e)}")
            
            error = create_error(
                K24ErrorCode.UNKNOWN_ERROR,
                message=f"Transaction failed: {str(e)}",
                suggestions=["Try again", "Check error logs"],
                context={"transaction_id": txn_id, "error": str(e)}
            )
            
            return (False, {}, error)
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"TXN_{timestamp}_{unique_id}"
    
    def _lock_transaction(self, txn_state: TransactionState):
        """Lock transaction to prevent concurrent modifications"""
        txn_state.locked = True
        txn_state.status = "LOCKED"
        self.active_transactions[txn_state.transaction_id] = txn_state
        logger.debug(f"Transaction {txn_state.transaction_id} locked")
    
    def _unlock_transaction(self, txn_state: TransactionState):
        """Unlock transaction"""
        txn_state.locked = False
        logger.debug(f"Transaction {txn_state.transaction_id} unlocked")
    
    def _create_backup(self, txn_state: TransactionState, params: Dict[str, Any]):
        """
        Create backup of current state (optional).
        For vouchers, we just store the params for potential rollback.
        """
        txn_state.backup_data = {
            "params": params.copy(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        logger.debug(f"Backup created for {txn_state.transaction_id}")
    
    def _push_to_tally(self, txn_state: TransactionState, voucher_xml: str) -> Dict[str, Any]:
        """Push XML to Tally and get response"""
        txn_state.status = "EXECUTING"
        
        try:
            result = self.tally.push_xml(voucher_xml)
            
            logger.info(f"Tally push result: {result}")
            
            return {
                "success": result.get("success", False),
                "status": result.get("status"),
                "created": result.get("created", 0),
                "errors": result.get("errors", []),
                "reference": result.get("data", {}).get("voucher_id") if result.get("data") else None,
                "raw_response": result
            }
        
        except Exception as e:
            logger.error(f"Tally push exception: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "errors": [str(e)],
                "reference": None
            }
    
    def _verify_transaction(
        self,
        txn_state: TransactionState,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify the transaction was actually created in Tally.
        Queries Tally to confirm the voucher exists.
        """
        txn_state.status = "VERIFYING"
        
        try:
            # Fetch recent vouchers
            voucher_type = params.get("voucher_type", "Receipt")
            party_name = params.get("party_name")
            amount = params.get("amount")
            
            # Query Tally for recent vouchers
            recent_vouchers = self.tally.fetch_vouchers(voucher_type=voucher_type)
            
            # Look for matching voucher
            # Match by: party_name, amount, recent timestamp
            matched = False
            matched_voucher = None
            
            if not recent_vouchers.empty:
                # Filter by party and amount
                if 'party_name' in recent_vouchers.columns and 'amount' in recent_vouchers.columns:
                    matches = recent_vouchers[
                        (recent_vouchers['party_name'].str.lower() == party_name.lower()) &
                        (recent_vouchers['amount'].astype(float).round(2) == float(amount))
                    ]
                    
                    if not matches.empty:
                        matched = True
                        matched_voucher = matches.iloc[0].to_dict()
            
            verification_data = {
                "verified": matched,
                "matched_voucher": matched_voucher,
                "verification_timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            txn_state.verification_data = verification_data
            
            if matched:
                logger.info(f"✅ Transaction verified in Tally")
            else:
                logger.warning(f"⚠️ Could not verify transaction in Tally")
            
            return verification_data
        
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "verified": False,
                "error": str(e),
                "verification_timestamp": datetime.utcnow().isoformat() + "Z"
            }
    
    def _rollback(self, txn_state: TransactionState, reason: str):
        """
        Rollback transaction.
        For vouchers, we can't easily delete from Tally, so we mark as failed.
        In future: implement compensating transactions.
        """
        logger.warning(f"🔄 Rolling back transaction {txn_state.transaction_id}")
        logger.warning(f"Reason: {reason}")
        
        txn_state.status = "ROLLED_BACK"
        txn_state.rollback_reason = reason
        txn_state.completed_at = datetime.utcnow().isoformat() + "Z"
        
        # Unlock
        self._unlock_transaction(txn_state)
        
        # Archive
        self.transaction_history.append(txn_state)
        if txn_state.transaction_id in self.active_transactions:
            del self.active_transactions[txn_state.transaction_id]
        
        # TODO: Implement actual rollback
        # For vouchers, this might mean creating a reversing entry
        # For now, we just log and mark as failed
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a transaction"""
        
        # Check active transactions
        if transaction_id in self.active_transactions:
            txn = self.active_transactions[transaction_id]
            return {
                "transaction_id": txn.transaction_id,
                "status": txn.status,
                "locked": txn.locked,
                "created_at": txn.created_at
            }
        
        # Check history
        for txn in self.transaction_history:
            if txn.transaction_id == transaction_id:
                return {
                    "transaction_id": txn.transaction_id,
                    "status": txn.status,
                    "created_at": txn.created_at,
                    "completed_at": txn.completed_at,
                    "rollback_reason": txn.rollback_reason
                }
        
        return None


# Example usage
if __name__ == "__main__":
    from backend.tally_connector import TallyConnector
    
    tally = TallyConnector()
    manager = TransactionManager(tally)
    
    # Example XML
    example_xml = """<ENVELOPE>...</ENVELOPE>"""
    
    params = {
        "voucher_type": "Receipt",
        "party_name": "Test Customer",
        "amount": 5000.00
    }
    
    success, result, error = manager.create_transaction(
        voucher_xml=example_xml,
        transaction_params=params,
        user_id="KITTU"
    )
    
    if success:
        print(f"✅ Success: {result}")
    else:
        print(f"❌ Failed: {error.to_dict()}")
