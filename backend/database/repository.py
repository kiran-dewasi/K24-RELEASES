from backend.database.supabase_client import supabase
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import json

class ChatRepository:
    """Handles all chat message operations with Supabase"""

    def __init__(self):
        self.supabase = supabase

    async def create_thread(self, thread_id: str, user_id: str = "unknown") -> Optional[Dict]:
        """Ensure thread exists in threads table."""
        if not self.supabase:
            return None
        try:
            loop = asyncio.get_event_loop()
            data = {
                'id': str(thread_id),
                'user_id': user_id,
                # 'title': 'New Chat', # Optional, depends on schema
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            # upsert=True is default for upsert method usually, but let's just try insert and catch or upsert
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('threads').upsert(data).execute()
            )
            print(f"[INFO] Thread ensured: {thread_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            # If it fails, maybe table usage is different, but strictly we need this for FK
            print(f"[WARN] Failed to create/upsert thread: {e}") 
            return None


    async def save_message(self, thread_id: str, role: str, content: str, 
                          source: str = 'ui', user_id: Optional[str] = None) -> Optional[Dict]:
        """Save a message to chat_history table."""
        if not self.supabase:
            return None

        try:
            # Run blocking Supabase call asynchronously
            loop = asyncio.get_event_loop()
            
            insert_data = {
                'thread_id': str(thread_id),
                'role': role,
                'content': content,
                'source': source,
                'user_id': user_id,
                'tenant_id': "default",  # Default tenant for now
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Execute in thread pool to avoid blocking
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('chat_history').insert(insert_data).execute()
            )
            
            if result.data:
                saved = result.data[0]
                print(f"[INFO] Message saved: {role} | thread={thread_id} | msg_id={saved.get('id')}")
                return saved
            else:
                print("No data returned from insert")
                return None
                
        except Exception as e:
            print(f"[ERR] FAILED to save message: {str(e)}")
            return None

    async def get_thread_history(self, thread_id: str, limit: int = 50) -> List[Dict]:
        """Get all messages in a thread, ordered chronologically (oldest first)."""
        if not self.supabase:
            return []

        try:
            loop = asyncio.get_event_loop()
            
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('chat_history')\
                    .select('*')\
                    .eq('thread_id', str(thread_id))\
                    .order('created_at', desc=False)\
                    .limit(limit)\
                    .execute()
            )
            
            messages = result.data if result.data else []
            print(f"[INFO] Retrieved {len(messages)} messages for thread {thread_id}")
            return messages
            
        except Exception as e:
            print(f"[ERR] FAILED to get thread history: {str(e)}")
            return []

    async def get_latest_message(self, thread_id: str) -> Optional[Dict]:
        """Get the most recent message in a thread"""
        if not self.supabase:
            return None
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('chat_history')\
                    .select('*')\
                    .eq('thread_id', str(thread_id))\
                    .order('created_at', desc=True)\
                    .limit(1)\
                    .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"[ERR] Failed to get latest message: {e}")
            return None

    async def count_messages(self, thread_id: str) -> int:
        """Count total messages in a thread"""
        if not self.supabase:
            return 0
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('chat_history')\
                    .select('id', count='exact')\
                    .eq('thread_id', str(thread_id))\
                    .execute()
            )
            return result.count if hasattr(result, 'count') else 0
        except Exception as e:
            print(f"[ERR] Failed to count messages: {e}")
            return 0

class AuditRepository:
    """Handle all audit logging (APPEND-ONLY)"""

    def __init__(self):
        self.supabase = supabase

    async def log_operation(self, 
                           table_name: str,
                           record_id: str,
                           operation: str,
                           executed_by: str,
                           before_state: Optional[Dict] = None,
                           after_state: Optional[Dict] = None,
                           triggered_by_message_id: Optional[str] = None,
                           thread_id: Optional[str] = None,
                           celery_task_id: Optional[str] = None,
                           financial_impact: Optional[Dict] = None,
                           metadata: Dict = {}) -> Optional[Dict]:
        """Log an operation to the audit trail (IMMUTABLE)."""
        if not self.supabase:
            return None

        try:
            loop = asyncio.get_event_loop()
            audit_entry = {
                'table_name': table_name,
                'record_id': record_id,
                'operation': operation,
                'executed_by': executed_by,
                'before_state': before_state,
                'after_state': after_state,
                'triggered_by_message_id': triggered_by_message_id,
                'thread_id': thread_id,
                'celery_task_id': celery_task_id,
                'financial_impact': financial_impact,
                'metadata': metadata,
                'created_at': datetime.utcnow().isoformat(),
            }
            
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('audit_logs').insert(audit_entry).execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Log operation failed: {e}")
            return None

    async def get_audit_trail(self, table_name: str, record_id: str) -> List[Dict]:
        """Get full history"""
        if not self.supabase:
            return []
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('audit_logs')\
                    .select('*')\
                    .eq('table_name', table_name)\
                    .eq('record_id', record_id)\
                    .order('created_at', desc=True)\
                    .execute()
            )
            return result.data if result.data else []
        except Exception as e:
             return []

class TaskRepository:
    """Handle task progress tracking"""
    
    def __init__(self):
        self.supabase = supabase

    async def create_task_progress(self, celery_task_id: str, thread_id: str, operation: str) -> Optional[Dict]:
        if not self.supabase:
            return None
        try:
            loop = asyncio.get_event_loop()
            data = {
                'celery_task_id': celery_task_id,
                'thread_id': thread_id,
                'operation': operation,
                'status': 'pending',
                'progress_percent': 0,
                'created_at': datetime.utcnow().isoformat()
            }
            result = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('task_progress').insert(data).execute()
            )
            return result.data[0] if result.data else None
        except:
             return None
        
    async def update_task_progress(self, celery_task_id: str, status: str, 
                                  progress_percent: int, current_step: Optional[str] = None,
                                  result: Optional[Dict] = None, error: Optional[str] = None) -> Optional[Dict]:
        if not self.supabase:
            return None
        try:
            loop = asyncio.get_event_loop()
            data = {
                'status': status,
                'progress_percent': progress_percent,
                'updated_at': datetime.utcnow().isoformat()
            }
            if current_step:
                data['current_step'] = current_step
            if result:
                data['result'] = result
            if error:
                data['error'] = error
                
            res = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('task_progress')\
                    .update(data)\
                    .eq('celery_task_id', celery_task_id)\
                    .execute()
            )
            return res.data[0] if res.data else None
        except:
             return None

    async def get_task_progress(self, celery_task_id: str) -> Optional[Dict]:
        """Get task progress"""
        if not self.supabase:
            return None
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None,
                lambda: self.supabase.table('task_progress')\
                    .select('*')\
                    .eq('celery_task_id', celery_task_id)\
                    .execute()
            )
            return res.data[0] if res.data else None
        except:
             return None
