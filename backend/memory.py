import os
import logging
try:
    import asyncpg
except ImportError:
    asyncpg = None

from contextlib import asynccontextmanager
from typing import AsyncGenerator
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    AsyncPostgresSaver = None

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# Global connection pool
_pool: asyncpg.Pool | None = None

def get_database_url() -> str:
    """Retrieve the Supabase/Postgres Database URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        # Default to SQLite for Desktop Mode
        # We need the absolute path logic used in database.py
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Root
        if getattr(sys, "frozen", False):
             base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "k24")
        
        db_path = os.path.join(base_dir, "k24_shadow.db")
        return f"sqlite:///{db_path}"
    return url

async def init_memory():
    """Initialize the asyncpg connection pool."""
    global _pool
    
    if asyncpg is None:
        logger.warning("asyncpg not installed, skipping pool init")
        return

    database_url = get_database_url()
    
    try:
        # Create a connection pool
        # min_size and max_size should be tuned based on Supabase limits (usually 60-100 total, so 10-20 per container is safe)
        if _pool is None:
            _pool = await asyncpg.create_pool(
                dsn=database_url,
                min_size=1,
                max_size=20,
                command_timeout=60
            )
            logger.info("Supabase connection pool initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize Supabase connection pool: {e}")
        # raise # Don't raise, just let it fail gracefully
        pass

async def close_memory():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Supabase connection pool closed.")
        _pool = None

@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[any, None]:
    """
    Yields a LangGraph Checkpointer.
    Refactored to use from_conn_string to avoid asyncpg.pool.PoolConnectionProxy type errors.
    """
    database_url = get_database_url()
    
    if AsyncPostgresSaver and not database_url.startswith("sqlite") and "postgres" in database_url:
        # AsyncPostgresSaver.from_conn_string is a context manager that handles the connection
        async with AsyncPostgresSaver.from_conn_string(database_url) as checkpointer:
            # Note: Setup should be done once on startup, not here.
            yield checkpointer
    else:
        # Fallback to in-memory
        checkpointer = MemorySaver()
        yield checkpointer
