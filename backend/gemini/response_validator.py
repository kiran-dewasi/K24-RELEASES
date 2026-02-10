"""
Response Validator for Gemini 2.0 Flash.

This module provides validation logic to ensure that responses from the Gemini API
are safe, valid, and conform to expected formats before being processed by the application.
"""

import logging
from typing import Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)

def validate_gemini_response(response: Optional[str]) -> Tuple[bool, str]:
    """
    Validates the response from Gemini 2.0 Flash.

    Args:
        response: The raw string response from the model.

    Returns:
        A tuple containing:
        - bool: True if valid, False otherwise.
        - str: Error message if invalid, or "Valid" if valid.
    """
    # 1. Check for None or empty
    if response is None:
        logger.warning("Validation failed: Response is None")
        return False, "Response is empty"
    
    if not response.strip():
        logger.warning("Validation failed: Response is empty string")
        return False, "Response is empty"

    # 2. Check Length
    # Flash responses should be concise but informative.
    # Minimum 50 chars (to avoid "I don't know" or single words)
    # Maximum 5000 chars (to avoid token limits downstream)
    if len(response) < 50:
        logger.warning(f"Validation failed: Response too short ({len(response)} chars)")
        return False, "Response too short"
    
    if len(response) > 5000:
        logger.warning(f"Validation failed: Response too long ({len(response)} chars)")
        return False, "Response too long"

    # 3. Check Encoding (UTF-8)
    try:
        response.encode('utf-8')
    except UnicodeEncodeError:
        logger.error("Validation failed: Invalid UTF-8 encoding")
        return False, "Invalid encoding"

    # 4. Check for SQL Injection Patterns
    # Basic check to prevent raw SQL leakage or injection attempts in generated text
    # that might be executed if mishandled.
    sql_patterns = [
        "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE USERS", 
        "UNION SELECT", "OR 1=1", "--",
        "DROP DATABASE", "UNION ALL SELECT", "ALTER TABLE", "TRUNCATE TABLE"
    ]
    upper_response = response.upper()
    for pattern in sql_patterns:
        if pattern in upper_response:
            logger.warning(f"Validation failed: Suspicious SQL pattern found: {pattern}")
            return False, "Contains suspicious patterns"

    # 5. Check for Hallucination Markers
    # These are phrases that might indicate the model is making things up 
    # or breaking character in a way that exposes internal logic.
    hallucination_markers = [
        "[insert data]", "<placeholder>", "I am a large language model",
        "As an AI", "training data"
    ]
    for marker in hallucination_markers:
        if marker.lower() in response.lower():
            logger.warning(f"Validation failed: Hallucination marker found: {marker}")
            return False, "Contains hallucination indicators"

    # 6. Check for Error Markers
    # Sometimes the API returns an error message as the content.
    error_markers = [
        "400 Bad Request", "500 Internal Server Error", "API key not valid",
        "quota exceeded"
    ]
    for marker in error_markers:
        if marker.lower() in response.lower():
            logger.warning(f"Validation failed: Error marker found: {marker}")
            return False, "Response contains error message"

    logger.info("Response validation passed")
    return True, "Valid"
