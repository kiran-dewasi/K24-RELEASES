from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

def trim_messages(messages, max_pairs=3):
    """
    Trims a list of LangChain messages to keep only the last `max_pairs` of Human+AI conversational turns,
    along with the SystemMessage intact at index 0.
    Ensures that ToolMessages are never orphaned from their parent AIMessage(tool_calls).

    Args:
        messages: List of BaseMessage objects.
        max_pairs: Number of Human-initiated conversational turns to keep.

    Returns:
        A valid list of BaseMessage objects safe for LangChain/LangGraph.
    """
    if not messages:
        return []

    system_msgs = []
    chat_msgs = []

    # Separate system messages and chat messages
    for msg in messages:
        msg_type = getattr(msg, "type", "")
        if not msg_type and isinstance(msg, dict):
            msg_type = msg.get("type", "")

        if msg_type == "system" or isinstance(msg, SystemMessage):
            system_msgs.append(msg)
        else:
            chat_msgs.append(msg)

    kept_chat_msgs = []
    human_count = 0
    pending_tool_calls = False

    # Iterate backwards to safely collect the most recent valid history
    for msg in reversed(chat_msgs):
        
        msg_type = getattr(msg, "type", "")
        
        # If we see a ToolMessage, we MUST keep going back until we find its parent AIMessage
        if msg_type == "tool" or isinstance(msg, ToolMessage):
            pending_tool_calls = True
        
        # If we find an AIMessage with tool_calls, it resolves the pending tool calls
        elif msg_type == "ai" or isinstance(msg, AIMessage):
            if getattr(msg, "tool_calls", None) or (isinstance(msg, dict) and msg.get("tool_calls")):
                pending_tool_calls = False

        kept_chat_msgs.append(msg)

        # Count conversational turns based on HumanMessages
        if msg_type == "human" or isinstance(msg, HumanMessage):
            # Only increment turn count if we are NOT inside an unresolved tool call chain
            if not pending_tool_calls:
                human_count += 1
                if human_count >= max_pairs:
                    break

    # Restore chronological order
    kept_chat_msgs.reverse()
    
    return system_msgs + kept_chat_msgs
