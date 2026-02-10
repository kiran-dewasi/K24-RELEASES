# K24 AI Agent - Complete LangGraph Orchestrator
# ================================================
# Production-ready agent with validation, error handling, and rollback

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# K24 Components
from backend.agent_state import AgentState, create_initial_state, update_state_with_audit, TransactionStatus
from backend.agent_intent import IntentClassifier, normalize_party_name, validate_intent_parameters
from backend.agent_validator import ValidatorAgent
from backend.agent_gemini import GeminiXMLAgent
from backend.agent_error_handler import AgentErrorHandler, FallbackStrategies, retry_with_backoff
from backend.agent_transaction import TransactionManager
from backend.agent_errors import K24ErrorCode, create_error
from backend.tally_connector import TallyConnector
from backend.classification.intents import IntentCategory, INTENT_TO_CATEGORY, Intent
from backend.gemini.gemini_orchestrator import GeminiOrchestrator

logger = logging.getLogger(__name__)


class K24AgentOrchestrator:
    """
    Complete AI Agent orchestrator using LangGraph state machines.
    Handles the full lifecycle: Intent → Validate → Generate → Execute → Respond
    """
    
    def __init__(
        self,
        api_key: str = None,
        tally_url: str = "http://localhost:9000",
        company_name: str = "Krishasales",
        tally_edu_mode: bool = True
    ):
        """Initialize all agent components"""
        
        # Get API key
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY required")
        
        # Initialize components
        self.intent_classifier = IntentClassifier(api_key=self.api_key)
        self.tally = TallyConnector(url=tally_url)
        self.validator = ValidatorAgent(tally_connector=self.tally)
        self.xml_generator = GeminiXMLAgent(api_key=self.api_key)
        self.error_handler = AgentErrorHandler()
        self.transaction_manager = TransactionManager(tally_connector=self.tally)
        
        # Initialize Gemini Orchestrator for general queries (KITTU)
        self.gemini_orchestrator = GeminiOrchestrator(api_key=self.api_key)
        
        # Configuration
        self.company_name = company_name
        self.tally_url = tally_url
        self.tally_edu_mode = tally_edu_mode
        
        # Build LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes (each node is a step in the workflow)
        workflow.add_node("parse_intent", self._parse_intent_node)
        workflow.add_node("validate_params", self._validate_params_node)
        workflow.add_node("generate_xml", self._generate_xml_node)
        workflow.add_node("generate_answer", self._generate_answer_node)  # New node for KITTU
        workflow.add_node("create_preview", self._create_preview_node)
        workflow.add_node("execute_transaction", self._execute_transaction_node)
        workflow.add_node("verify_transaction", self._verify_transaction_node)
        workflow.add_node("build_response", self._build_response_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Set entry point
        workflow.set_entry_point("parse_intent")
        
        # Add edges (state transitions)
        workflow.add_conditional_edges(
            "parse_intent",
            self._should_proceed_after_intent,
            {
                "validate": "validate_params",
                "answer": "generate_answer",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "validate_params",
            self._should_proceed_after_validation,
            {
                "generate": "generate_xml",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_xml",
            self._should_proceed_after_generation,
            {
                "preview": "create_preview",
                "retry": "generate_xml",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("generate_answer", "build_response")
        workflow.add_edge("create_preview", "build_response")  # Preview → Response (wait for approval)
        workflow.add_edge("execute_transaction", "verify_transaction")
        workflow.add_edge("verify_transaction", "build_response")
        workflow.add_edge("build_response", END)
        workflow.add_edge("handle_error", END)
        
        # Compile with checkpointing
        return workflow.compile(checkpointer=MemorySaver())
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        company_name: str = None,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: process user message through the agent workflow.
        
        Args:
            user_message: Natural language command from user
            user_id: User identifier
            company_name: Tally company name
            auto_approve: If True, auto-approve transactions (for testing)
        
        Returns:
            Structured response dictionary
        """
        
        # Create initial state
        initial_state = create_initial_state(
            user_message=user_message,
            user_id=user_id,
            company_name=company_name or self.company_name,
            tally_url=self.tally_url,
            tally_edu_mode=self.tally_edu_mode
        )
        
        # Run through graph
        try:
            # Execute graph
            config = {"configurable": {"thread_id": user_id}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # If auto-approve and needs approval, execute it
            if auto_approve and final_state.get("requires_approval") and final_state.get("generated_xml"):
                logger.info("Auto-approving transaction")
                final_state = await self._execute_with_approval(final_state)
            
            return final_state.get("final_response", {})
        
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "message": "An unexpected error occurred"
            }
    
    async def approve_transaction(self, transaction_id: str, user_id: str) -> Dict[str, Any]:
        """
        Approve a pending transaction and execute it.
        """
        # TODO: Retrieve state from checkpoint using transaction_id
        # For now, this is a placeholder
        pass

    # ========== Node Functions ==========
    
    async def _parse_intent_node(self, state: AgentState) -> AgentState:
        """Node 1: Parse user intent"""
        
        logger.info(f"[{state['transaction_id']}] Parsing intent")
        
        try:
            intent, confidence, params = await self.intent_classifier.classify_async(state["user_message"])
            
            # Normalize party name
            if "party_name" in params:
                params["party_name"] = normalize_party_name(params["party_name"])
            
            # Add default voucher type based on intent
            voucher_type_map = {
                "create_invoice": "Sales",
                "create_receipt": "Receipt",
                "create_payment": "Payment",
                "create_sales": "Sales"
            }
            if "voucher_type" not in params and intent in voucher_type_map:
                params["voucher_type"] = voucher_type_map[intent]
            
            # Determine category
            category = INTENT_TO_CATEGORY.get(intent, IntentCategory.FALLBACK)
            
            # Handle unknown/fallback by routing to KITTU (generate_answer)
            # We don't error out immediately anymore
            
            return update_state_with_audit(
                state,
                {
                    "intent": intent,
                    "intent_category": category,
                    "intent_confidence": confidence,
                    "raw_parameters": params,
                    "status": TransactionStatus.VALIDATING
                },
                f"Intent classified: {intent} (confidence: {confidence:.2f})"
            )
        
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            return self._add_error_to_state(
                state,
                K24ErrorCode.UNKNOWN_ERROR,
                f"Failed to parse intent: {str(e)}"
            )
    
    def _validate_params_node(self, state: AgentState) -> AgentState:
        """Node 2: Validate parameters"""
        
        logger.info(f"[{state['transaction_id']}] Validating parameters")
        
        try:
            validation_result = self.validator.validate_all(
                intent=state["intent"],
                parameters=state["raw_parameters"]
            )
            
            if validation_result.is_valid:
                return update_state_with_audit(
                    state,
                    {
                        "is_valid": True,
                        "validated_parameters": validation_result.validated_params,
                        "validation_warnings": validation_result.warnings,
                        "validation_confidence": validation_result.confidence,
                        "status": TransactionStatus.GENERATING
                    },
                    f"Validation passed (confidence: {validation_result.confidence:.2f})"
                )
            else:
                # Validation failed
                return update_state_with_audit(
                    state,
                    {
                        "is_valid": False,
                        "validation_errors": [e.to_dict() for e in validation_result.errors],
                        "status": TransactionStatus.FAILED
                    },
                    "Validation failed"
                )
        
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return self._add_error_to_state(
                state,
                K24ErrorCode.UNKNOWN_ERROR,
                f"Validation exception: {str(e)}"
            )
    
    async def _generate_xml_node(self, state: AgentState) -> AgentState:
        """Node 3: Generate Tally XML"""
        
        logger.info(f"[{state['transaction_id']}] Generating XML")
        
        try:
            params = state["validated_parameters"]
            
            # Generate XML (now async)
            success, xml, errors = await self.xml_generator.generate_voucher_xml(
                voucher_type=params.get("voucher_type", "Receipt"),
                party_name=params.get("party_name", ""),
                amount=params.get("amount", 0),
                date=params.get("date"),
                narration=params.get("narration", ""),
                additional_params={
                    "company_name": state["company_name"],
                    "deposit_to": params.get("deposit_to", "Cash"),
                    "tax_rate": params.get("tax_rate", 0)
                }
            )
            
            attempts = state.get("xml_generation_attempts", 0) + 1
            
            if success:
                return update_state_with_audit(
                    state,
                    {
                        "generated_xml": xml,
                        "xml_generation_attempts": attempts,
                        "xml_validation_errors": [],
                        "status": TransactionStatus.AWAITING_APPROVAL
                    },
                    f"XML generated successfully (attempt {attempts})"
                )
            else:
                return update_state_with_audit(
                    state,
                    {
                        "xml_validation_errors": errors,
                        "xml_generation_attempts": attempts
                    },
                    f"XML generation failed (attempt {attempts})"
                )
        
        except Exception as e:
            logger.error(f"XML generation error: {e}")
            return self._add_error_to_state(
                state,
                K24ErrorCode.XML_VALIDATION_FAILED,
                f"XML generation failed: {str(e)}"
            )
    
    async def _generate_answer_node(self, state: AgentState) -> AgentState:
        """Node 3b: Generate Answer for General Queries (KITTU)"""
        
        logger.info(f"[{state['transaction_id']}] Generating Answer via KITTU")
        
        try:
            # Invoke Gemini with KITTU persona
            # We inject context into the query since invoke_with_retry doesn't support context param
            
            context_str = f"Context: Company={state['company_name']}, Intent={state['intent']}"
            full_query = f"{context_str}\n\nUser Query: {state['user_message']}"
            
            response_text = await self.gemini_orchestrator.invoke_with_retry(
                query=full_query
            )
            
            return update_state_with_audit(
                state,
                {
                    "generated_answer": response_text,
                    "status": TransactionStatus.SUCCESS
                },
                "Answer generated via KITTU"
            )
            
        except Exception as e:
            logger.error(f"KITTU generation error: {e}")
            return self._add_error_to_state(
                state,
                K24ErrorCode.UNKNOWN_ERROR,
                f"Failed to generate answer: {str(e)}"
            )
    
    def _create_preview_node(self, state: AgentState) -> AgentState:
        """Node 4: Create transaction preview for user approval"""
        
        logger.info(f"[{state['transaction_id']}] Creating preview")
        
        params = state["validated_parameters"]
        
        # Build preview
        preview = {
            "transaction_id": state["transaction_id"],
            "voucher_type": params.get("voucher_type"),
            "party_name": params.get("party_name"),
            "amount": f"₹{params.get('amount', 0):,.2f}",
            "date": params.get("date"),
            "narration": params.get("narration", ""),
            "warnings": state.get("validation_warnings", [])
        }
        
        # Determine risk level
        amount = params.get("amount", 0)
        risk_level = "HIGH" if amount > 500000 else "MEDIUM" if amount > 100000 else "LOW"
        
        return update_state_with_audit(
            state,
            {
                "transaction_preview": preview,
                "risk_level": risk_level,
                "requires_approval": True
            },
            "Preview created"
        )
    
    def _execute_transaction_node(self, state: AgentState) -> AgentState:
        """Node 5: Execute transaction in Tally"""
        
        logger.info(f"[{state['transaction_id']}] Executing transaction")
        
        try:
            success, result, error = self.transaction_manager.create_transaction(
                voucher_xml=state["generated_xml"],
                transaction_params=state["validated_parameters"],
                user_id=state["user_id"]
            )
            
            if success:
                return update_state_with_audit(
                    state,
                    {
                        "tally_response": result,
                        "tally_reference": result.get("tally_reference"),
                        "execution_timestamp": result.get("completed_at"),
                        "status": TransactionStatus.SUCCESS
                    },
                    "Transaction executed successfully"
                )
            else:
                return self._add_error_to_state(
                    state,
                    K24ErrorCode.TALLY_CONNECTION_FAILED,
                    error.message if error else "Transaction execution failed"
                )
        
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return self._add_error_to_state(
                state,
                K24ErrorCode.UNKNOWN_ERROR,
                f"Execution failed: {str(e)}"
            )
    
    def _verify_transaction_node(self, state: AgentState) -> AgentState:
        """Node 6: Verify transaction was created"""
        
        logger.info(f"[{state['transaction_id']}] Verifying transaction")
        
        # Verification already done in transaction_manager
        tally_response = state.get("tally_response", {})
        verification = tally_response.get("verification", {})
        
        return update_state_with_audit(
            state,
            {
                "verified": verification.get("verified", False),
                "verification_details": verification
            },
            f"Verification: {'SUCCESS' if verification.get('verified') else 'FAILED'}"
        )
    
    def _build_response_node(self, state: AgentState) -> AgentState:
        """Node 7: Build final response for user"""
        
        logger.info(f"[{state['transaction_id']}] Building response")
        
        status = state.get("status", TransactionStatus.PENDING)
        
        if isinstance(status, TransactionStatus):
            status_value = status.value
        else:
            status_value = status
        
        # Calculate duration
        try:
            from datetime import timezone
            # Ensure both are offset-aware
            if "Z" in state["started_at"]:
                started_at = datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))
            else:
                started_at = datetime.fromisoformat(state["started_at"]).replace(tzinfo=timezone.utc)
                
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            duration_ms = 0
        
        if state.get("generated_answer"):
            # General Answer (KITTU)
            response = {
                "status": "SUCCESS",
                "transaction_id": state["transaction_id"],
                "message": state["generated_answer"],
                "type": "answer"
            }
        elif state.get("requires_approval") and not state.get("approved"):
            # Awaiting approval
            response = {
                "status": "AWAITING_APPROVAL",
                "transaction_id": state["transaction_id"],
                "message": "Please review and approve this transaction",
                "preview": state.get("transaction_preview"),
                "risk_level": state.get("risk_level"),
                "warnings": state.get("validation_warnings", []),
                "type": "transaction_preview"
            }
        elif str(status_value).upper() == "SUCCESS":
            # Success
            response = {
                "status": "SUCCESS",
                "transaction_id": state["transaction_id"],
                "message": "Transaction created successfully",
                "details": {
                    "party": state["validated_parameters"].get("party_name"),
                    "amount": f"₹{state['validated_parameters'].get('amount', 0):,.2f}",
                    "date": state["validated_parameters"].get("date"),
                    "tally_reference": state.get("tally_reference")
                },
                "audit_trail": {
                    "created_by": state["user_id"],
                    "timestamp": state.get("execution_timestamp"),
                    "duration_ms": duration_ms
                },
                "type": "transaction_success"
            }
        else:
            # Error
            # Use the first error message if available
            errors = state.get("errors", [])
            error_msg = errors[0].get("message") if errors else "Transaction failed. See errors for details."
            
            response = {
                "status": "FAILED",
                "transaction_id": state["transaction_id"],
                "errors": errors,
                "message": error_msg,
                "type": "error"
            }
        
        return update_state_with_audit(
            state,
            {
                "final_response": response,
                "completed_at": completed_at.isoformat() + "Z",
                "duration_ms": duration_ms
            },
            "Response built"
        )
    
    def _handle_error_node(self, state: AgentState) -> AgentState:
        """Node 8: Handle errors"""
        
        logger.error(f"[{state['transaction_id']}] Handling error")
        
        errors = state.get("errors", [])
        validation_errors = state.get("validation_errors", [])
        
        all_errors = errors + validation_errors
        
        response = {
            "status": "FAILED",
            "transaction_id": state["transaction_id"],
            "errors": all_errors,
            "message": all_errors[0].get("message") if all_errors else "Unknown error"
        }
        
        return update_state_with_audit(
            state,
            {
                "final_response": response,
                "status": TransactionStatus.FAILED,
                "completed_at": datetime.utcnow().isoformat() + "Z"
            },
            "Error handled"
        )
    
    # ========== Conditional Edge Functions ==========
    
    def _should_proceed_after_intent(self, state: AgentState) -> str:
        """Decide next step after intent parsing"""
        category = state.get("intent_category")
        
        if category == IntentCategory.CREATE_OPERATIONS:
            return "validate"
        else:
            # For all other categories (Queries, Compliance, Unknown), route to KITTU
            return "answer"
    
    def _should_proceed_after_validation(self, state: AgentState) -> str:
        """Decide next step after validation"""
        if state.get("is_valid"):
            return "generate"
        return "error"
    
    def _should_proceed_after_generation(self, state: AgentState) -> str:
        """Decide next step after XML generation"""
        if state.get("generated_xml"):
            return "preview"
        
        # Check if we should retry
        attempts = state.get("xml_generation_attempts", 0)
        if attempts < 2:
            return "retry"
        
        return "error"
    
    # ========== Helper Functions ==========
    
    def _add_error_to_state(
        self,
        state: AgentState,
        error_code: K24ErrorCode,
        message: str
    ) -> AgentState:
        """Add error to state"""
        
        error = create_error(error_code, message)
        
        new_errors = state.get("errors", []) + [error.to_dict()]
        
        return update_state_with_audit(
            state,
            {
                "errors": new_errors,
                "status": TransactionStatus.FAILED
            },
            f"Error: {error_code.value}"
        )
    
    async def _execute_with_approval(self, state: AgentState) -> AgentState:
        """Execute transaction after approval"""
        
        # Mark as approved
        state = update_state_with_audit(
            state,
            {
                "approved": True,
                "approval_timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "Transaction approved"
        )
        
        # Execute
        state = self._execute_transaction_node(state)
        state = self._verify_transaction_node(state)
        state = self._build_response_node(state)
        
        return state


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        orchestrator = K24AgentOrchestrator()
        
        test_message = "Create invoice for HDFC Bank for ₹50,000 with 18% GST"
        
        result = await orchestrator.process_message(
            user_message=test_message,
            user_id="KITTU",
            auto_approve=False  # Set to True to auto-execute
        )
        
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())
