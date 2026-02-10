"""
Follow-up Manager - Tracks conversation state and missing information

This module manages multi-turn conversations by tracking what information
is still needed to complete an action (e.g., party name, amount, items).
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationSlot:
    """Represents a piece of information needed for an action"""
    name: str
    required: bool = True
    value: Optional[Any] = None
    prompt: Optional[str] = None  # Question to ask if missing


@dataclass
class ConversationState:
    """Tracks the state of a conversation"""
    intent: str  # e.g., "create_sale", "reconcile_invoices"
    slots: Dict[str, ConversationSlot] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_missing_slots(self) -> List[str]:
        """Get list of missing required slots"""
        return [
            name for name, slot in self.slots.items()
            if slot.required and slot.value is None
        ]
    
    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.get_missing_slots()) == 0
    
    def update_slot(self, name: str, value: Any):
        """Update a slot value"""
        if name in self.slots:
            self.slots[name].value = value
            self.updated_at = datetime.now()


class FollowUpManager:
    """
    Manages conversation state and follow-up questions
    """
    
    # Define slot requirements for different intents
    INTENT_SLOTS = {
        "create_sale": [
            ConversationSlot("party_name", required=True, prompt="Which customer are you selling to?"),
            ConversationSlot("amount", required=True, prompt="What is the total amount?"),
            ConversationSlot("items", required=False, prompt="Would you like to add item details?"),
            ConversationSlot("date", required=False),
        ],
        "create_purchase": [
            ConversationSlot("party_name", required=True, prompt="Which supplier are you purchasing from?"),
            ConversationSlot("amount", required=True, prompt="What is the total amount?"),
            ConversationSlot("items", required=False, prompt="Would you like to add item details?"),
            ConversationSlot("date", required=False),
        ],
        "reconcile_invoices": [
            ConversationSlot("party_name", required=True, prompt="Which party should I reconcile invoices for?"),
        ],
        "update_gstin": [
            ConversationSlot("party_name", required=True, prompt="Which party's GSTIN should I update?"),
            ConversationSlot("gstin", required=True, prompt="What is the new GSTIN number?"),
        ],
    }
    
    def __init__(self):
        """Initialize the FollowUpManager"""
        self.conversations: Dict[str, ConversationState] = {}
    
    def start_conversation(self, user_id: str, intent: str) -> ConversationState:
        """
        Start a new conversation
        
        Args:
            user_id: User identifier
            intent: Intent type (e.g., "create_sale")
            
        Returns:
            New conversation state
        """
        # Get slot template for this intent
        slot_templates = self.INTENT_SLOTS.get(intent, [])
        
        # Create fresh copies of slots
        slots = {
            slot.name: ConversationSlot(
                name=slot.name,
                required=slot.required,
                prompt=slot.prompt
            )
            for slot in slot_templates
        }
        
        conversation = ConversationState(
            intent=intent,
            slots=slots
        )
        
        self.conversations[user_id] = conversation
        return conversation
    
    def get_conversation(self, user_id: str) -> Optional[ConversationState]:
        """Get current conversation for a user"""
        return self.conversations.get(user_id)
    
    def update_conversation(
        self,
        user_id: str,
        slot_updates: Dict[str, Any]
    ) -> ConversationState:
        """
        Update conversation with new information
        
        Args:
            user_id: User identifier
            slot_updates: Dict of slot name -> value
            
        Returns:
            Updated conversation state
        """
        conversation = self.conversations.get(user_id)
        if not conversation:
            raise ValueError(f"No active conversation for user {user_id}")
        
        for slot_name, value in slot_updates.items():
            conversation.update_slot(slot_name, value)
        
        return conversation
    
    def get_next_question(self, user_id: str) -> Optional[str]:
        """
        Get the next follow-up question to ask
        
        Args:
            user_id: User identifier
            
        Returns:
            Question string or None if complete
        """
        conversation = self.conversations.get(user_id)
        if not conversation:
            return None
        
        missing_slots = conversation.get_missing_slots()
        if not missing_slots:
            return None
        
        # Get the first missing slot's prompt
        first_missing = missing_slots[0]
        slot = conversation.slots[first_missing]
        return slot.prompt or f"Please provide {first_missing}"
    
    def clear_conversation(self, user_id: str):
        """Clear conversation state for a user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def extract_slots_from_intent(
        self,
        intent_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract slot values from intent recognition result
        
        Args:
            intent_data: Intent object with entity and parameters
            
        Returns:
            Dict of slot name -> value
        """
        slots = {}
        
        # Extract entity as party_name if present
        if intent_data.get("entity"):
            slots["party_name"] = intent_data["entity"]
        
        # Extract parameters
        params = intent_data.get("parameters", {})
        for key, value in params.items():
            if value is not None:
                slots[key] = value
        
        return slots
    
    def should_ask_follow_up(self, user_id: str) -> bool:
        """
        Check if we should ask a follow-up question
        
        Args:
            user_id: User identifier
            
        Returns:
            True if follow-up needed, False otherwise
        """
        conversation = self.conversations.get(user_id)
        if not conversation:
            return False
        
        return not conversation.is_complete()
