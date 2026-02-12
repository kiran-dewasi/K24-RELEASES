"""
Desktop Services Package
Exports all desktop services
"""

from .whatsapp_poller import WhatsAppPoller, init_poller, get_poller

__all__ = [
    "WhatsAppPoller",
    "init_poller", 
    "get_poller"
]
