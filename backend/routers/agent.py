# K24 AI Agent - FastAPI Router (LangGraph Edition)
# ===================================================
# API endpoints for the Stateful AI agent powered by LangGraph & Supabase

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, AsyncGenerator
import logging
import json
import os
from datetime import datetime

# LangGraph & Persistence
from graph import build_graph
from memory import get_checkpointer as _get_checkpointer_cm
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["AI Agent"])

# ========== Dependencies ==========

async def get_checkpointer_dep():
    """FastAPI Dependency to yield a checkpointer from the pool."""
    async with _get_checkpointer_cm() as cp:
        yield cp

# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    thread_id: str = Field(..., description="Unique conversation ID (UUID)")
    message: str = Field(..., description="User's natural language command")
    # Optional action flag (e.g. for simple confirmation buttons)
    action: Optional[str] = None
    # Context from frontend (e.g. active page, drafted voucher)
    context: Optional[Dict[str, Any]] = None 

# ========== Endpoints ==========

@router.post("/chat")
async def chat(
    request: ChatRequest,
    checkpointer = Depends(get_checkpointer_dep) # Validates DB connection & yields checkpointer
):
    """
    Main chat endpoint - process user's natural language command.
    Uses LangGraph with Supabase persistence.
    """
    try:
        thread_id = request.thread_id
        user_message = request.message
        
        logger.info(f"Chat request for thread {thread_id}: {user_message}")

        # 1. Build the graph with the active checkpointer
        graph = build_graph(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 2. Check current state (for Resume/Interrupt handling)
        snapshot = await graph.aget_state(config)
        
        should_resume = False
        if snapshot.next and "human_review" in snapshot.next:
            # We are paused at human_review
            # Check if user message indicates approval
            if user_message.strip().lower() in ["yes", "approve", "confirm", "ok", "go ahead"]:
                should_resume = True
                logger.info(f"Resuming execution for thread {thread_id} (Approval received)")
            else:
                # User did not approve explicitly.
                # If they said "no", or asked a question, we might want to handle differently.
                # For now, if paused, we only listen for Yes. 
                # If "No", maybe we should cancel? 
                # Let's assume anything else is a "No" or unrelated query, but we are STUCK at interrupt.
                # We will inform the user they are at a decision point.
                if user_message.strip().lower() in ["no", "cancel", "stop"]:
                     # Ideally we would cancel the flow.
                     # For now, just return a message saying it's cancelled (without changing state? or delete state?)
                     # We'll just respond textually.
                     pass
        
        # 3. Stream response
        async def event_generator():
            try:
                # Decide mode: Resume or New Message
                if should_resume:
                     # Resume by invoking with None (which proceeds past the interrupt)
                    input_data = None
                else:
                    # If we are stuck at interrupt and didn't resume, strict LangGraph might not accept a new message easily
                    # without update_state. But let's try sending the message. 
                    # If stuck, adding a message adds to history but might not trigger the node if it's still interrupted.
                    # Actually, if we are interrupted, we MUST resume or update state to move.
                    # If user says "No", we probably want to just reply.
                    if snapshot.next and "human_review" in snapshot.next:
                        yield json.dumps({
                            "type": "message",
                            "content": "There is a pending action waiting for your approval. Type 'yes' to proceed or 'no' to cancel."
                        }) + "\n"
                        return

                    # Add date context to help AI understand "today", "yesterday", etc.
                    now = datetime.now()
                    date_context = f"\n\n[Context: Today is {now.strftime('%B %d, %Y')} ({now.strftime('%Y%m%d')})]"
                    enhanced_message = user_message + date_context
                    
                    input_data = {"messages": [HumanMessage(content=enhanced_message)]}

                # astream returns events. We want to stream tokens or updates.
                # mode="updates" gives us the node outputs.
                async for event in graph.astream(input_data, config, stream_mode="updates"):
                    # Event is a dict of {node_name: output}
                    for node, output in event.items():
                        # Handle Agent output context
                        if node == "agent":
                            messages = output.get("messages", [])
                            if messages:
                                last_msg = messages[-1]
                                if isinstance(last_msg, AIMessage):
                                    if last_msg.tool_calls:
                                        tool_names = [tc['name'] for tc in last_msg.tool_calls]
                                        yield json.dumps({
                                            "type": "thought", 
                                            "content": f"Deciding to use: {', '.join(tool_names)}..."
                                        }) + "\n"
                                    else:
                                        yield json.dumps({
                                            "type": "message", 
                                            "content": last_msg.content
                                        }) + "\n"
                        
                        elif node == "tools":
                             yield json.dumps({
                                 "type": "status",
                                 "content": "Executed actions successfully."
                             }) + "\n"
                
                # Check final state for interrupt (Human Review)
                final_snapshot = await graph.aget_state(config)
                if final_snapshot.next and "human_review" in final_snapshot.next:
                     last_msg = final_snapshot.values["messages"][-1]
                     if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                         tool_call = last_msg.tool_calls[0]
                         yield json.dumps({
                             "type": "approval_request",
                             "content": f"I need your approval to execute: **{tool_call['name']}**.\n\nParams: {json.dumps(tool_call['args'], indent=2)}\n\nType 'yes' to proceed.",
                             "details": tool_call
                         }) + "\n"
                     else:
                         # Should not happen based on logic
                         yield json.dumps({
                             "type": "approval_request",
                             "content": "Operation paused for review. Type 'yes' to proceed."
                         }) + "\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield json.dumps({"type": "error", "content": f"Error: {str(e)}"}) + "\n"

        return StreamingResponse(event_generator(), media_type="application/x-ndjson")

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        # Streaming response might have already started? No, we haven't returned yet.
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "LangGraph Agent"}

# ========== Compatibility ==========
def init_orchestrator():
    """Dummy function for backward compatibility with backend/api.py startup."""
    logger.info("LangGraph Agent does not require explicit orchestration init.")
