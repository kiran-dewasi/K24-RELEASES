"""
Gemini 1.5 Flash Orchestrator for KITTU Agent.

This module handles interactions with the Google Gemini 1.5 Flash API.
It includes initialization, retry logic, streaming support, and response validation.
"""

import os
import logging
import asyncio
import time
from typing import Optional, Callable, Tuple, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

from .gemini_prompts import KITTU_SYSTEM_PROMPT
from .response_validator import validate_gemini_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GeminiOrchestrator:
    """
    Orchestrator for managing Gemini 1.5 Flash API interactions.
    """

    def __init__(self, api_key: Optional[str] = None, system_prompt: str = KITTU_SYSTEM_PROMPT):
        """
        Initialize the Gemini Orchestrator.

        Args:
            api_key: Google Gemini API Key. If None, tries to load from env GOOGLE_API_KEY.
            system_prompt: System instruction for the model.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("No API key provided for Gemini Orchestrator")
            raise ValueError("API Key is required")

        genai.configure(api_key=self.api_key, transport="rest")

        # Gemini 2.0 Flash Configuration
        # CRITICAL: Do NOT use 'thinking' parameter as it is not supported in Flash.
        self.generation_config = GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
            top_p=0.95,
            top_k=40,
        )

        self.model_name = "gemini-2.0-flash"
        self.system_prompt = system_prompt

        logger.info(f"Initializing Gemini Model: {self.model_name}")
        
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_prompt,
                generation_config=self.generation_config
            )
            logger.info("Gemini Model initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize Gemini Model: {str(e)}")
            raise

    async def invoke_with_retry(self, query: str, images: Optional[List[Any]] = None, max_attempts: int = 3, timeout: int = 30) -> str:
        """
        Invokes the Gemini model with retry logic and exponential backoff.

        Args:
            query: The user query string.
            images: Optional list of images (PIL.Image or similar) for multimodal requests.
            max_attempts: Maximum number of retry attempts.
            timeout: Timeout in seconds for each attempt.

        Returns:
            The generated response string.

        Raises:
            TimeoutError: If all retries timeout.
            ValueError: If response validation fails.
            RuntimeError: If all retries fail due to other errors.
        """
        print(f"[GEMINI_CALL] {time.strftime('%H:%M:%S')} — caller: {__name__}")
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_attempts} invoking Gemini...")
                
                # Calculate timeout for this attempt if needed, or just enforce it via asyncio
                # Here we use asyncio.wait_for to enforce the timeout
                response = await asyncio.wait_for(
                    self._call_gemini_flash(query, images),
                    timeout=timeout
                )

                # Validate Response
                is_valid, message = self._validate_response(response)
                if not is_valid:
                    logger.warning(f"Response validation failed on attempt {attempt}: {message}")
                    raise ValueError(f"Invalid response: {message}")

                logger.info(f"Success on attempt {attempt}")
                return response

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt} (>{timeout}s)")
                last_exception = TimeoutError("Request timed out")
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {str(e)}")
                last_exception = e

            # Exponential Backoff
            if attempt < max_attempts:
                delay = min(1 * (2 ** (attempt - 1)), 10)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        logger.error("All retry attempts failed")
        if isinstance(last_exception, TimeoutError):
            raise TimeoutError("All retries timed out")
        elif isinstance(last_exception, ValueError):
            raise last_exception
        else:
            raise RuntimeError(f"All retries failed: {str(last_exception)}")

    async def _call_gemini_flash(self, query: str, images: Optional[List[Any]] = None) -> str:
        """
        Internal method to call the Gemini Flash API.

        Args:
            query: The user query.
            images: Optional list of images.

        Returns:
            The raw response text.
        """
        # Prepare content: if images present, create a list [query, image1, image2...]
        content = [query]
        if images:
            content.extend(images)

        # Run the blocking synchronous call in a thread executor
        loop = asyncio.get_running_loop()
        
        def blocking_call():
            # Use synchronous generate_content
            return self.model.generate_content(content)

        # Execute in thread pool
        response = await loop.run_in_executor(None, blocking_call)
        return response.text

    def _validate_response(self, response: str) -> Tuple[bool, str]:
        """
        Validates the response using the validator module.
        """
        return validate_gemini_response(response)

    async def stream_response(self, query: str, on_chunk_callback: Callable[[str], None]) -> None:
        """
        Streams the response from Gemini Flash.

        Args:
            query: The user query.
            on_chunk_callback: A callback function to handle each chunk of text.
        """
        logger.info("Starting stream response...")
        try:
            response_stream = await self.model.generate_content_async(query, stream=True)
            
            async for chunk in response_stream:
                if chunk.text:
                    on_chunk_callback(chunk.text)
            
            logger.info("Streaming completed successfully")

        except Exception as e:
            logger.error(f"Error during streaming: {str(e)}")
            raise

    async def generate_content_stream(self, query: str) -> AsyncGenerator[str, None]:
        """
        Generator for streaming content, useful for API endpoints.
        """
        try:
            response_stream = await self.model.generate_content_async(query, stream=True)
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Error in generate_content_stream: {str(e)}")
            raise

if __name__ == "__main__":
    # Quick test if run directly
    async def main():
        try:
            orchestrator = GeminiOrchestrator()
            print("Testing connection...")
            response = await orchestrator.invoke_with_retry("Hello, are you online?")
            print(f"Response: {response}")
        except Exception as e:
            print(f"Test failed: {e}")

    asyncio.run(main())
