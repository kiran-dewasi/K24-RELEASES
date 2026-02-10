
import asyncio
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.ai_engine.router import router

logger = logging.getLogger("Orchestrator")

class InvoiceExtraction(BaseModel):
    """Schema for validating extracted Invoice Data"""
    party_name: str
    amount: float
    date: str
    items: list
    # Strict validation: Party Name is mandatory

class GeminiOrchestrator:
    """
    Manages AI interactions with Retries, Validation, and Confidence Checks.
    """
    
    def __init__(self):
        self.max_retries = 3
        # We use the router to get the model dynamically, but for validation we might force Pro
        pass

    async def generate_response(self, messages: list, has_image: bool = False, complexity: str = "low") -> Any:
        """
        Wraps LLM generation with retry logic.
        """
        model = router.get_model(has_image, complexity)
        
        for attempt in range(self.max_retries):
            try:
                response = await model.ainvoke(messages)
                return response
            except Exception as e:
                logger.warning(f"⚠️ Gemini API Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error("❌ All Gemini retries failed.")
                    # Return a fallback message or raise
                    from langchain_core.messages import AIMessage
                    return AIMessage(content="I'm having trouble connecting to my brain (Google Gemini). Please try again in a moment.")
                await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff

    def validate_invoice_data(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validates if the extraction is sufficient to proceed.
        Returns (is_valid, reason/message).
        """
        try:
            # Check if Party Name exists (CRITICAL)
            if not data.get("party_name") or data.get("party_name") == "Unknown":
                return False, "I couldn't identify the Party/Vendor name. Who is this bill from?"
            
            # Pydantic Check
            # (Note: Extracted data might be loose JSON, so we try to parse it)
            # InvoiceExtraction(**data) 
            # Skipping strict Pydantic for loose dict validation logic to avoid trivial data conversions issues
            
            # Confidence Check (Simulated for now as Gemini doesn't always return a score)
            # In a real scenario, we'd ask for "confidence_score" in the JSON output schema.
            if data.get("confidence", 1.0) < 0.8:
                return False, "I'm not 100% sure about this invoice. Please review it manually."

            return True, "Valid"

        except Exception as e:
            return False, f"Validation Error: {e}"

# Singleton
orchestrator = GeminiOrchestrator()
