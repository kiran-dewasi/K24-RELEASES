"""
K24 Gemini Streaming Handler
============================
Utilities for handling streaming responses from Gemini.
"""

import asyncio
from typing import AsyncGenerator, Callable, Optional
from .gemini_orchestrator import GeminiOrchestrator

async def stream_response(
    orchestrator: GeminiOrchestrator,
    query: str,
    context: Optional[dict] = None
) -> AsyncGenerator[str, None]:
    """
    Stream response from Gemini as an async generator.
    This is useful for FastAPI StreamingResponse.
    
    Args:
        orchestrator: Configured GeminiOrchestrator instance
        query: User query
        context: Optional context
        
    Yields:
        Text chunks
    """
    # Format context into query if needed
    if context:
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        query = f"Context:\n{context_str}\n\nQuery: {query}"
        
    try:
        async for chunk in orchestrator.generate_content_stream(query):
            yield chunk
    except Exception as e:
        yield f"ERROR: {str(e)}"
