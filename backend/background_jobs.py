
"""
Background Jobs Abstraction Layer
This module provides a unified way to enqueue background tasks.
It switches between 'FastAPI BackgroundTasks' (Desktop Mode) and 'Celery' (Server Mode)
based on environment configuration.
"""

import os
import asyncio
from typing import Optional, Dict, Any
from fastapi import BackgroundTasks

# Config
USE_CELERY = os.getenv("USE_REDIS_QUEUE", "false").lower() == "true"

# Import Logic
from backend.logic import (
    logic_create_ledger_async,
    logic_create_voucher_async, 
    logic_process_whatsapp_message
)

# Import Celery Tasks (Only if needed, but we avoid top-level import to prevent errors if Celery missing)
# We do lazy import inside functions if USE_CELERY is True

class BackgroundJobManager:
    def __init__(self):
        self.mode = "CELERY" if USE_CELERY else "IN_PROCESS"
        print(f"[JOB MANAGER] Initialized in {self.mode} mode")

    async def enqueue_create_voucher(self, voucher_data: Dict[str, Any], user_id: str, 
                                     thread_id: str = None, 
                                     background_tasks: Optional[BackgroundTasks] = None):
        """
        Enqueue a voucher creation task.
        """
        if self.mode == "CELERY":
            # Lazy Import to avoid crashes in Desktop Mode
            from backend.tasks import create_voucher_async as celery_task
            # Note: The task in tasks.py is async, but Celery wraps it. 
            # We assume tasks.py is updated to wrap logic.py
            celery_task.delay(voucher_data, user_id, thread_id)
            return "queued_celery"
        else:
            # Desktop Mode
            if background_tasks:
                background_tasks.add_task(logic_create_voucher_async, voucher_data, user_id, thread_id)
                return "queued_background_task"
            else:
                # Direct Await (Fallback)
                print("[JOB MANAGER] Warning: No BackgroundTasks object provided. Awaiting directly.")
                return await logic_create_voucher_async(voucher_data, user_id, thread_id)


    async def enqueue_create_ledger(self, ledger_data: Dict[str, Any], user_id: str, 
                                    thread_id: str = None, 
                                    background_tasks: Optional[BackgroundTasks] = None):
        """
        Enqueue a ledger creation task.
        """
        if self.mode == "CELERY":
            from backend.tasks import create_ledger_async as celery_task
            celery_task.delay(ledger_data, user_id, thread_id)
            return "queued_celery"
        else:
            if background_tasks:
                background_tasks.add_task(logic_create_ledger_async, ledger_data, user_id, thread_id)
                return "queued_background_task"
            else:
                return await logic_create_ledger_async(ledger_data, user_id, thread_id)


    def enqueue_whatsapp_processing(self, from_phone, message_text, message_id, webhook_timestamp, 
                                   background_tasks: Optional[BackgroundTasks] = None):
        """
        Enqueue WhatsApp message processing.
        """
        if self.mode == "CELERY":
            from backend.tasks import process_whatsapp_message
            process_whatsapp_message.delay(from_phone, message_text, message_id, webhook_timestamp)
            return "queued_celery"
        else:
            # Logic function is sync or async? 
            # logic.py: logic_process_whatsapp_message is sync.
            if background_tasks:
                background_tasks.add_task(logic_process_whatsapp_message, from_phone, message_text, message_id, webhook_timestamp)
                return "queued_background_task"
            else:
                # Run inline
                return logic_process_whatsapp_message(from_phone, message_text, message_id, webhook_timestamp)


# Global Instance
job_manager = BackgroundJobManager()
