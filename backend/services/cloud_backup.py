import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from backend.database import get_db_path
from backend.database.encryption import encryptor
import requests

logger = logging.getLogger("cloud_backup")

# Load Supabase config from env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

class CloudBackupService:
    def __init__(self):
        self.enabled = bool(SUPABASE_URL and SUPABASE_KEY)
        if not self.enabled:
            logger.warning("Supabase URL/KEY missing. Cloud backup disabled.")

    def create_backup(self, user_id: str = "system"):
        """Run backup synchronously (can be run in threadpool)"""
        if not self.enabled:
            return False

        try:
            # 1. Locate DB
            db_path_str = get_db_path()
            db_path = Path(db_path_str)
            
            if not db_path.exists():
                logger.error(f"Database not found at {db_path}")
                return False

            # 2. Compress (Zip)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{user_id}_{timestamp}"
            zip_path = db_path.parent / f"{backup_name}.zip"
            
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(db_path, arcname="k24_shadow.db")

            # 3. Encrypt
            with open(zip_path, "rb") as f:
                file_data = f.read()
            
            encrypted_data = encryptor.cipher.encrypt(file_data)
            
            # 4. Upload to Supabase Storage via REST API
            # POST /storage/v1/object/{bucket}/{path}
            bucket = "backups"
            file_path = f"{user_id}/{backup_name}.enc"
            
            url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"
            headers = {
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "apikey": SUPABASE_KEY,
                "Content-Type": "application/octet-stream",
                "x-upsert": "true"
            }
            
            response = requests.post(url, data=encrypted_data, headers=headers)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Upload failed: {response.status_code} {response.text}")
                # Fallback: maybe bucket doesn't exist?
                return False
            
            # 5. Cleanup
            if zip_path.exists():
                os.remove(zip_path)
                
            logger.info(f"Cloud backup successful: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Cloud backup failed: {e}")
            try:
                if 'zip_path' in locals() and zip_path.exists():
                    os.remove(zip_path)
            except:
                pass
            return False

backup_service = CloudBackupService()
