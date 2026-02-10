import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class MessageValidator:
    """
    Validates user input for security threats and constraints.
    Checks: Length, Encoding, SQL Injection, Prompt Injection.
    """
    
    # SQL Injection patterns (case insensitive)
    SQL_PATTERNS = [
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
        r"UPDATE\s+.*SET",
        r"UNION\s+SELECT",
        r"--",
        r"/\*",
        r"\*/"
    ]
    
    # Prompt Injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r"IGNORE\s+PREVIOUS",
        r"SYSTEM\s+OVERRIDE",
        r"ADMIN\s+MODE",
        r"DEVELOPER\s+MODE",
        r"DAN\s+MODE",
        r"JAILBREAK"
    ]

    @staticmethod
    def validate_message(message: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a message string.
        Returns: (is_valid, error_code, error_message)
        """
        # 1. Length Validation
        if not message or len(message) < 1:
            return False, "INVALID_LENGTH", "Message cannot be empty"
        if len(message) > 2000:
            return False, "INVALID_LENGTH", "Message must be under 2000 characters"

        # 2. Encoding Validation (Null bytes)
        if '\x00' in message:
            return False, "INVALID_ENCODING", "Message contains null bytes"

        # 3. SQL Injection Detection
        for pattern in MessageValidator.SQL_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                logger.warning(f"SQL Injection attempt detected: {message[:50]}...")
                return False, "INJECTION_DETECTED", "Invalid message format (Security Alert)"

        # 4. Prompt Injection Detection
        for pattern in MessageValidator.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                logger.warning(f"Prompt Injection attempt detected: {message[:50]}...")
                return False, "INJECTION_DETECTED", "Invalid message format (Security Alert)"

        return True, None, None
