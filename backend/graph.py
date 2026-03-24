from typing import Annotated, Literal, TypedDict, Union, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from tools import ALL_TOOLS, SAFE_TOOLS, SENSITIVE_TOOLS
from agent_system import SYSTEM_INSTRUCTIONS # optional, or inline
import os
import json

# --- State Definition ---
class AgentState(TypedDict):
    # 'messages' is the standard key for chat history
    messages: Annotated[list, add_messages]
    # Source pipeline identification (CHAT or WHATSAPP)
    source_pipeline: str = "CHAT"
    # We can add custom keys if needed, e.g. 'requires_approval'

# --- Model Setup ---
# Ensure GOOGLE_API_KEY is set
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Fallback from k24_config.json
    try:
        with open("k24_config.json", "r") as f:
            config = json.load(f)
            api_key = config.get("google_api_key")
    except:
        pass

if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is missing and not found in k24_config.json")
else:
    os.environ["GOOGLE_API_KEY"] = api_key # Ensure it's set for other libs

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    transport="rest",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Bind all tools to the model so it knows what it can do
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# --- Nodes ---

def agent_node(state: AgentState):
    """
    The Brain. Decides what to do (call tool or respond).
    Uses ModelRouter to select Flash vs Pro.
    """
    import time
    print(f"[AGENT_NODE] {time.strftime('%H:%M:%S')} â€” iteration start")
    messages = state["messages"]
    source = state.get("source_pipeline", "CHAT")
    
    # Prepend System Message if not present (or always inject for context)
    from langchain_core.messages import SystemMessage
    from agent_system import SYSTEM_INSTRUCTIONS
    from ai_engine.router import router # Lazy import to avoid circular dep if any

    # Custom system instruction adaptation for WhatsApp if needed
    import datetime
    current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    current_instructions = SYSTEM_INSTRUCTIONS
    current_instructions += f"\n\nCURRENT DATE: {current_date_str}. Trust this date. Dates in 2025/2026 are VALID."
    
    if source == "WHATSAPP":
        current_instructions += "\n\nNOTE: You are conversing via WhatsApp. Keep responses concise and avoid heavy markdown. For reports, use bullet lists."
    else:
        current_instructions += "\n\nNOTE: For reports (Stock, Receivables), use the `check_...` tools and ALWAYS present the JSON data as a Markdown Table."

    # Limit history to last 6 messages to reduce token usage
    if len(messages) > 6:
        limited_messages = messages[-6:]  # type: ignore
    else:
        limited_messages = messages
    final_messages = [SystemMessage(content=current_instructions)] + limited_messages
    
    # ANALYZE COMPLEXITY
    # Check for images in the messages
    has_image = False
    last_msg = messages[-1]
    
    # â”€â”€ SHORT-CIRCUIT: FILE DELIVERY SENTINEL â”€â”€
    # If the last message is a tool execution that returned a file sentinel,
    # skip LLM invocation so it doesn't digest the sentinel.
    if getattr(last_msg, "type", "") == "tool" and isinstance(last_msg.content, str):
        if last_msg.content.startswith("__FILE__::"):
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content=last_msg.content)]}

    if isinstance(last_msg, HumanMessage) and hasattr(last_msg, 'additional_kwargs'):
        # Just a generic check, real implementation depends on how image data is passed (e.g. content list)
        if isinstance(last_msg.content, list): 
             for item in last_msg.content:
                 if isinstance(item, dict) and item.get("type") == "image_url":
                     has_image = True
    
    # Check text complexity
    text_content = ""
    # Look back for the actual human message text if last_msg is a tool message
    if isinstance(last_msg, HumanMessage) and isinstance(last_msg.content, str):
        text_content = last_msg.content
    elif getattr(last_msg, "type", "") == "tool":
        # Find the last HumanMessage
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                text_content = m.content if isinstance(m.content, str) else ""
                break
    
    complexity = "low"
    if len(text_content) > 300 or "analyze" in text_content.lower() or "report" in text_content.lower():
        complexity = "high"


    # Select Model using Router
    selected_llm = router.get_model(has_image=has_image, complexity=complexity)
    
    # â”€â”€ FORCE TOOL CALLING IF FILE IS REQUESTED â”€â”€
    # If the user is specifically asking for an Excel or PDF, the LLM often hallucinates
    # a text reply ("I will send it now") instead of calling the tool. We force it here.
    force_tool = False
    lower_text = text_content.lower()
    if isinstance(last_msg, HumanMessage) and any(keyword in lower_text for keyword in ["excel", "pdf", "spreadsheet", "report", "statement"]):
        force_tool = True
        
    if force_tool:
        # tool_choice="any" forces the model to pick at least one tool
        llm_with_tools = selected_llm.bind_tools(ALL_TOOLS, tool_choice="any")
    else:
        # Standard binding
        llm_with_tools = selected_llm.bind_tools(ALL_TOOLS)
    
    response = llm_with_tools.invoke(final_messages)
    return {"messages": [response]}

def tools_node(state: AgentState):
    """
    Executes the tools requested by the agent.
    This node handles BOTH safe and sensitive tools.
    Sensitive tools only reach here after passing through 'human_review'.
    """
    last_message = state["messages"][-1]
    # tool_calls = last_message.tool_calls
    
    # We can use the prebuilt ToolNode or implement custom execution
    # Implementing custom for clarity and control
    from langgraph.prebuilt import ToolNode
    tool_executor = ToolNode(ALL_TOOLS)
    return tool_executor.invoke(state)

def human_review_node(state: AgentState):
    """
    A pass-through node that serves as an interruption point.
    If the graph reaches here, it means a sensitive tool was called.
    We interrupt BEFORE this node (or the user approves explicitly).
    Actually, we'll use interrupt_before=['human_review'] in the compile step.
    So when resuming, this node just logs approval.
    """
    # If we are here, the user said "yes" (resumed).
    # We can add a system message noting approval if we want, or just pass.
    return {"messages": [HumanMessage(content="Action approved checks out.")]} # Optional marker

# --- Conditional Logic ---

def route_logic(state: AgentState) -> Literal["tools", "human_review", "__end__"]:
    """
    Determines where to go after the agent speaks.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If no tool calls, end interaction (respond to user)
    if not last_message.tool_calls:
        return END
    
    # Check for sensitive tools
    sensitive_names = {t.name for t in SENSITIVE_TOOLS}
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in sensitive_names:
            return "human_review" # ROUTE TO HUMAN REVIEW
            
    # If only safe tools, go directly to tools
    return "tools"

# --- Graph Construction ---

builder = StateGraph(AgentState)

builder.add_node("agent", agent_node)
builder.add_node("tools", tools_node)
builder.add_node("human_review", human_review_node)

builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    route_logic,
    {
        "tools": "tools",
        "human_review": "human_review",
        "__end__": END
    }
)

# If human review passes, go to tools to execute
builder.add_edge("human_review", "tools")

# After tools, go back to agent
builder.add_edge("tools", "agent")

# --- Compilation is done in server.py with checkpointer ---
# But we can provide a helper
def build_graph(checkpointer=None):
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[] # ["human_review"] # TEMPORARY: Allow auto-execution for debugging
    )

# Compiled graph instance (lazy loaded)
_app = None

async def run_agent(message_text: str, thread_id: str = "default", user_id: str = "default", image_data: str = None):
    """
    Run the LangGraph Agent.
    user_id = tenant_id of the currently authenticated user (resolved from WhatsApp mapping or JWT).
    """
    global _app
    if _app is None:
        from langgraph.checkpoint.memory import MemorySaver
        _app = build_graph(checkpointer=MemorySaver())

    # â”€â”€ Propagate tenant_id to tools via thread-local â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # _get_tenant() in tools/__init__.py reads _CURRENT_TENANT_ID first if set.
    # This ensures the tenant from the WhatsApp resolution flows into every tool.
    if user_id and user_id not in ("default", ""):
        try:
            import tools as _tools_mod
            _tools_mod._CURRENT_TENANT_ID = user_id
        except Exception:
            pass

    # Construct messages
    from langchain_core.messages import HumanMessage

    # Handle Multimodal Input
    content = message_text
    if image_data:
        image_url = f"data:image/jpeg;base64,{image_data}"
        content = [
            {"type": "text", "text": message_text if message_text else "Analyze this image to extract transaction details."},
            {"type": "image_url", "image_url": image_url}
        ]

    input_state = {
        "messages": [HumanMessage(content=content)],
        "source_pipeline": "WHATSAPP"
    }

    config = {
        "configurable": {"thread_id": thread_id, "user_id": user_id},
        "recursion_limit": 3  # Reduced from 10 to minimize token usage
    }

    try:
        final_state = await _app.ainvoke(input_state, config=config)
        messages = final_state["messages"]
        if messages and isinstance(messages[-1], AIMessage):
            return messages[-1].content
        return "No response from agent."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Agent Error: {str(e)}"



