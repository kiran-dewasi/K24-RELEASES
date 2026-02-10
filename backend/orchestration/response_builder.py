"""
Response Builder - Orchestrates structured responses for KITTU

This module provides a unified interface for building different types of responses:
- Text responses (simple messages)
- Card responses (interactive UI components)
- Follow-up responses (asking for missing information)
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class ResponseType(str, Enum):
    """Types of responses KITTU can return"""
    TEXT = "text"
    CARD = "card"
    FOLLOW_UP = "follow_up"
    DRAFT_VOUCHER = "draft_voucher"
    ERROR = "error"


class CardType(str, Enum):
    """Types of interactive cards"""
    PARTY_SELECTOR = "party_selector"
    ITEM_SELECTOR = "item_selector"
    DATE_SELECTOR = "date_selector"
    VOUCHER_DRAFT = "voucher_draft"
    CONFIRMATION = "confirmation"


class ResponseBuilder:
    """
    Builds structured responses for the chat interface
    """
    
    @staticmethod
    def text(message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build a simple text response
        
        Args:
            message: The text message to display
            metadata: Optional metadata (e.g., data sources, timestamps)
            
        Returns:
            Structured response dict
        """
        return {
            "type": ResponseType.TEXT,
            "response": message,
            "metadata": metadata or {}
        }
    
    @staticmethod
    def follow_up(
        question: str,
        missing_slots: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build a follow-up question response
        
        Args:
            question: The question to ask the user
            missing_slots: List of missing information (e.g., ["party_name", "amount"])
            context: Current conversation context
            
        Returns:
            Structured response dict
        """
        return {
            "type": ResponseType.FOLLOW_UP,
            "response": question,
            "missing_slots": missing_slots,
            "context": context or {}
        }
    
    @staticmethod
    def card(
        card_type: CardType,
        title: str,
        data: Dict[str, Any],
        actions: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Build an interactive card response
        
        Args:
            card_type: Type of card to display
            title: Card title
            data: Card data (varies by card type)
            actions: Optional list of action buttons
            
        Returns:
            Structured response dict
        """
        return {
            "type": ResponseType.CARD,
            "card_type": card_type,
            "title": title,
            "data": data,
            "actions": actions or []
        }
    
    @staticmethod
    def draft_voucher(
        party_name: str,
        voucher_type: str,
        amount: float,
        items: List[Dict[str, Any]],
        narration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build a voucher draft for approval
        
        Args:
            party_name: Party/Customer name
            voucher_type: Type of voucher (Sales, Purchase, etc.)
            amount: Total amount
            items: List of line items
            narration: Optional narration
            
        Returns:
            Structured response dict
        """
        return {
            "type": ResponseType.DRAFT_VOUCHER,
            "data": {
                "party_name": party_name,
                "voucher_type": voucher_type,
                "amount": amount,
                "items": items,
                "narration": narration
            }
        }
    
    @staticmethod
    def error(message: str, error_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Build an error response
        
        Args:
            message: Error message
            error_code: Optional error code
            
        Returns:
            Structured response dict
        """
        return {
            "type": ResponseType.ERROR,
            "response": message,
            "error_code": error_code
        }
    
    @staticmethod
    def party_selector(
        parties: List[Dict[str, str]],
        context: str = "Select a party"
    ) -> Dict[str, Any]:
        """
        Build a party selector card
        
        Args:
            parties: List of party objects with 'name' and 'id'
            context: Context message
            
        Returns:
            Structured card response
        """
        return ResponseBuilder.card(
            card_type=CardType.PARTY_SELECTOR,
            title=context,
            data={"parties": parties}
        )
    
    @staticmethod
    def item_selector(
        items: List[Dict[str, Any]],
        context: str = "Add items to voucher"
    ) -> Dict[str, Any]:
        """
        Build an item selector card
        
        Args:
            items: List of available items
            context: Context message
            
        Returns:
            Structured card response
        """
        return ResponseBuilder.card(
            card_type=CardType.ITEM_SELECTOR,
            title=context,
            data={"items": items}
        )
    
    @staticmethod
    def confirmation(
        message: str,
        data: Dict[str, Any],
        confirm_action: str = "confirm",
        cancel_action: str = "cancel"
    ) -> Dict[str, Any]:
        """
        Build a confirmation card
        
        Args:
            message: Confirmation message
            data: Data being confirmed
            confirm_action: Confirm button action
            cancel_action: Cancel button action
            
        Returns:
            Structured card response
        """
        return ResponseBuilder.card(
            card_type=CardType.CONFIRMATION,
            title=message,
            data=data,
            actions=[
                {"type": confirm_action, "label": "Confirm"},
                {"type": cancel_action, "label": "Cancel"}
            ]
        )
