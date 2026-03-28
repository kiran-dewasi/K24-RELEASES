from typing import Optional
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import TOOLS
from dotenv import load_dotenv

load_dotenv()

class ModelRouter:
    """
    Intelligent router to select the best LLM model based on task complexity.
    """
    
    FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.0-flash")
    PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-flash")
    FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-pro")
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not set for ModelRouter")

    def get_model(self, has_image: bool = False, complexity: str = "low") -> ChatGoogleGenerativeAI:
        """
        Returns a configured LLM instance based on requirements.
        
        Args:
            has_image (bool): True if the input context contains images/PDFs.
            complexity (str): "high" for complex reasoning, "low" for basic tasks.
        """
        
        # Rule 1 & 2: Images or High Complexity -> Use PRO
        if has_image or complexity == "high":
            print(f"ðŸ§  ModelRouter: Selecting PREMIUM model ({self.PRO_MODEL}) - Reason: {'Image Input' if has_image else 'High Complexity'}")
            return self._create_llm(self.PRO_MODEL)
            
        # Default: Use FLASH
        print(f"âš¡ ModelRouter: Selecting FAST model ({self.FLASH_MODEL})")
        return self._create_llm(self.FLASH_MODEL)

    def _create_llm(self, model_name: str) -> ChatGoogleGenerativeAI:
        """Creates the LLM instance with tools bound."""
        # Verification: Ensure API Key is present
        if not self.api_key:
             self.api_key = os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
             raise ValueError("API Key is missing in ModelRouter. Please check GOOGLE_API_KEY.")

        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                transport="rest",
                temperature=0.1,
                top_p=0.95,
                google_api_key=self.api_key
            ).bind_tools(TOOLS)
            
            if model_name == self.PRO_MODEL:
                from google.api_core.exceptions import ResourceExhausted
                fallback_llm = ChatGoogleGenerativeAI(
                    model=self.FALLBACK_MODEL,
                    transport="rest",
                    temperature=0.1,
                    top_p=0.95,
                    google_api_key=self.api_key
                ).bind_tools(TOOLS)
                # with_fallbacks will catch exceptions (like 429) and route to fallback
                llm = llm.with_fallbacks(
                    [fallback_llm],
                    exceptions_to_handle=(Exception,) # or specifically ResourceExhausted
                )
                
            return llm
        except Exception as e:
            print(f"âŒ Error initializing {model_name}: {e}")
            # Fallback to Flash if Pro fails (rudimentary fallback)
            if model_name != self.FLASH_MODEL:
                print("âš ï¸ Falling back to Flash model...")
                return self._create_llm(self.FLASH_MODEL)
            raise e


# Create a singleton instance for easy import
router = ModelRouter()

