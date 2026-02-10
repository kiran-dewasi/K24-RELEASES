from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Determine execution mode
# If USE_REDIS_QUEUE is explicitly "true", we use Redis. Otherwise, we default to Eager (Memory).
# This makes it easier for dev environments (Windows) to run without Redis.
use_redis = os.getenv("USE_REDIS_QUEUE", "false").lower() == "true"
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not use_redis:
    print("⚠️ Redis disabled. Running tasks synchronously (Eager Mode).")
    # In-Memory Configuration
    app = Celery('k24_tasks', broker='memory://', backend='cache+memory://')
    app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
else:
    print(f"✅ Redis enabled. Connecting to {redis_url}")
    # Production / Redis Configuration
    app = Celery('k24_tasks', broker=redis_url, backend=redis_url)
    app.conf.update(
        broker_connection_retry_on_startup=True
    )

# Common Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    task_track_started=True,
)

if __name__ == '__main__':
    app.start()
