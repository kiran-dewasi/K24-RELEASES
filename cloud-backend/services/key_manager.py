import os
import logging

logger = logging.getLogger(__name__)


def get_google_api_key(user_id: str = None) -> str:
    """
    Get Google/Gemini API key.

    On the cloud backend, API keys are not stored per-user in the database
    (UserSettings was local-only and has been removed from the cloud schema).
    The key is sourced from the GOOGLE_API_KEY environment variable set in
    Railway / the cloud deployment.

    The `user_id` argument is accepted for call-site compatibility but is
    not used in the cloud context.
    """
    env_key = os.getenv("GOOGLE_API_KEY")
    if env_key:
        return env_key

    logger.warning("GOOGLE_API_KEY environment variable is not set")
    return None
