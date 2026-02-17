# Cloud Backend Routers
# These routers are cloud-hosted and do NOT depend on local Tally

# Only whatsapp_cloud is currently ready (no desktop dependencies)
from . import whatsapp_cloud
from . import webhooks

# TODO: Refactor these routers to remove backend.* dependencies:
# from . import auth
# from . import whatsapp
# from . import baileys
# from . import devices
# from . import query

__all__ = [
    "whatsapp_cloud",
    "webhooks",
]
