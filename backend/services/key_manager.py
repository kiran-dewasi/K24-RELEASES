import os
import logging
from backend.database import get_db, UserSettings
from backend.database.encryption import encryptor

logger = logging.getLogger(__name__)

def get_google_api_key(user_id: str = None) -> str:
    """
    Get Google/Gemini API key.
    Priority:
    1. Encrypted key in UserSettings (if user_id provided)
    2. GOOGLE_API_KEY environment variable (Legacy/Dev)
    3. k24_config.json (Legacy)
    """
    # 1. Try DB first (Secure User-owned Key)
    if user_id:
        try:
            db = next(get_db())
            settings = db.query(UserSettings).filter(UserSettings.user_id == str(user_id)).first()
            if settings and settings.google_api_key:
                try:
                    # Try to decrypt
                    decrypted = encryptor.decrypt(settings.google_api_key)
                    if decrypted and len(decrypted) > 20: # Basic validity check
                        return decrypted
                except Exception as e:
                    logger.error(f"Failed to decrypt user API key: {e}")
        except Exception as e:
            logger.error(f"DB Key fetch failed: {e}")

    # 2. Environment Variable
    env_key = os.getenv("GOOGLE_API_KEY")
    if env_key:
        return env_key
        
    return None
