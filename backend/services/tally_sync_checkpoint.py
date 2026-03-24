import shutil
from datetime import datetime
from pathlib import Path
import json
from contextlib import contextmanager
import logging
from database import get_db_path
import os

# Configure logging
logger = logging.getLogger("tally_sync")

class SyncCheckpoint:
    def __init__(self):
        # Store checkpoints in .k24/checkpoints
        # Use user home directory for persistence
        self.checkpoint_dir = Path.home() / ".k24" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def transaction(self, user_id: str, sync_type: str):
        """
        Atomic sync with rollback capability.
        Creates a backup of the DB before yielding.
        If an exception occurs during the yield block, restores the DB from backup.
        """
        checkpoint_id = self.create_checkpoint(user_id, sync_type)
        logger.info(f"Created sync checkpoint: {checkpoint_id}")
        
        try:
            yield checkpoint_id
            self.commit(checkpoint_id)
        except Exception as e:
            logger.error(f"Sync failed for {sync_type}. Rolling back to {checkpoint_id}. Error: {e}")
            self.rollback(checkpoint_id)
            raise e
    
    def create_checkpoint(self, user_id: str, sync_type: str) -> str:
        """Backup database before sync"""
        timestamp = int(datetime.now().timestamp())
        checkpoint_id = f"{user_id}_{sync_type}_{timestamp}"
        
        # Resolve DB path dynamically
        db_path_str = get_db_path()
        db_path = Path(db_path_str)
        
        if not db_path.exists():
             logger.warning(f"Database not found at {db_path}, skipping checkpoint.")
             return checkpoint_id # Nothing to backup

        backup_path = self.checkpoint_dir / f"{checkpoint_id}.db"
        
        try:
            # Copy DB file
            shutil.copy2(db_path, backup_path)
            
            metadata = {
                "checkpoint_id": checkpoint_id,
                "user_id": user_id,
                "sync_type": sync_type,
                "created_at": datetime.now().isoformat(),
                "db_backup": str(backup_path),
                "original_db": str(db_path)
            }
            
            with open(self.checkpoint_dir / f"{checkpoint_id}.json", 'w') as f:
                json.dump(metadata, f)
                
        except Exception as e:
            logger.error(f"Failed to create checkpoint backup: {e}")
            # Non-blocking, proceed without checkpoint if backup fails? 
            # Or raise? Better to warn and proceed, as sync is critical.
        
        return checkpoint_id
    
    def rollback(self, checkpoint_id: str):
        """Restore database to checkpoint"""
        metadata_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not metadata_path.exists():
            logger.error(f"Checkpoint metadata not found: {metadata_path}")
            return

        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            backup_db = Path(metadata["db_backup"])
            current_db = Path(metadata["original_db"])
            
            if backup_db.exists():
                # Force close handlers if possible or just copy over
                shutil.copy2(backup_db, current_db)
                logger.info(f"✅ Rolled back database to checkpoint: {checkpoint_id}")
            else:
                logger.error(f"Backup file missing: {backup_db}")
                
        except Exception as e:
            logger.error(f"CRITICAL: Failed to rollback database: {e}")
    
    def commit(self, checkpoint_id: str):
        """Mark checkpoint as committed"""
        # Clean up old checkpoints to save space
        self._cleanup_old_checkpoints()

    def _cleanup_old_checkpoints(self):
        try:
            # List all .db files in checkpoint dir
            backups = sorted(self.checkpoint_dir.glob("*.db"), key=lambda f: f.stat().st_mtime)
            # Keep last 5
            if len(backups) > 5:
                for b in backups[:-5]:
                    try:
                        b.unlink(missing_ok=True)
                        # Also try remove .json
                        json_file = b.with_suffix(".json")
                        json_file.unlink(missing_ok=True)
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"Checkpoint cleanup failed: {e}")

checkpoint = SyncCheckpoint()
