
from celery import shared_task
import asyncio
from backend.logic import (
    logic_create_ledger_async,
    logic_create_voucher_async,
    logic_process_whatsapp_message
)

# Async Helper
def run_async(coro):
    """Helper to run async code in sync Celery task"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(coro)

@shared_task(bind=True, max_retries=3)
def process_whatsapp_message(self, from_phone, message_text, message_id, webhook_timestamp):
    """
    Process incoming WhatsApp message through agent
    Wrapper around logic.py
    """
    try:
        logic_process_whatsapp_message(from_phone, message_text, message_id, webhook_timestamp)
    except Exception as exc:
        print(f"WhatsApp Task Failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def create_ledger_async(self, ledger_data: dict, user_id: str = "agent", 
                      thread_id: str = None, triggered_by_message_id: str = None):
    """
    Wrapper for create_ledger logic
    """
    return run_async(logic_create_ledger_async(ledger_data, user_id, thread_id, triggered_by_message_id))


@shared_task(bind=True)
def create_voucher_async(self, voucher_data: dict, user_id: str = "agent", 
                       thread_id: str = None, triggered_by_message_id: str = None):
    """
    Wrapper for create_voucher logic
    """
    return run_async(logic_create_voucher_async(voucher_data, user_id, thread_id, triggered_by_message_id))
