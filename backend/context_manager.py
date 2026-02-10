"""
Context Manager for KITTU
Manages user conversation state, preferences, and workflow tracking.

Universal Design:
- Works with any Tally company
- Graceful fallback if Redis unavailable
- Thread-safe operations
- Configurable TTL and history limits
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    timestamp: str
    user_message: str
    assistant_response: str
    intent: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None


@dataclass
class UserContext:
    """User context structure"""
    user_id: str
    company: str
    conversation_history: List[Dict[str, Any]]
    active_workflows: Dict[str, Any]
    preferences: Dict[str, Any]
    last_updated: str
    
    @classmethod
    def create_default(cls, user_id: str, company: str = "SHREE JI SALES") -> "UserContext":
        """Create default context for new user"""
        return cls(
            user_id=user_id,
            company=company,
            conversation_history=[],
            active_workflows={},
            preferences={},
            last_updated=datetime.now().isoformat()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserContext":
        """Create from dictionary"""
        return cls(**data)


class ContextManager:
    """
    Manages conversation context and user state.
    
    Universal Features:
    - Works with any Tally company
    - Automatic TTL cleanup (24 hours default)
    - Conversation history limit (10 turns default)
    - In-memory fallback if Redis unavailable
    - Thread-safe operations
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 86400,  # 24 hours
        max_history: int = 10,
        use_fallback: bool = True
    ):
        """
        Initialize ContextManager
        
        Args:
            redis_url: Redis connection URL
            ttl_seconds: Context expiry time (default 24 hours)
            max_history: Max conversation turns to store (default 10)
            use_fallback: Use in-memory fallback if Redis fails
        """
        self.ttl_seconds = ttl_seconds
        self.max_history = max_history
        self.use_fallback = use_fallback
        self._fallback_storage: Dict[str, UserContext] = {}
        
        # Try to connect to Redis
        try:
            import redis
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Using in-memory fallback.")
            self.redis_client = None
            self.redis_available = False
            if not use_fallback:
                raise
    
    def get_context(self, user_id: str, company: Optional[str] = None) -> UserContext:
        """
        Get user context, creating if doesn't exist
        
        Args:
            user_id: Unique user identifier
            company: Default company if creating new context
            
        Returns:
            UserContext object
        """
        context_key = f"context:{user_id}"
        
        # Try Redis first
        if self.redis_available:
            try:
                data = self.redis_client.get(context_key)
                if data:
                    context = UserContext.from_dict(json.loads(data))
                    logger.debug(f"Retrieved context for user {user_id} from Redis")
                    return context
            except Exception as e:
                logger.error(f"Redis get failed: {e}")
        
        # Check fallback storage
        if user_id in self._fallback_storage:
            logger.debug(f"Retrieved context for user {user_id} from fallback")
            return self._fallback_storage[user_id]
        
        # Create new context
        default_company = company or "SHREE JI SALES"
        context = UserContext.create_default(user_id, default_company)
        logger.info(f"Created new context for user {user_id}, company {default_company}")
        
        # Save immediately
        self._save_context(user_id, context)
        return context
    
    def update_context(
        self,
        user_id: str,
        updates: Dict[str, Any],
        merge: bool = True
    ) -> UserContext:
        """
        Update user context
        
        Args:
            user_id: User identifier
            updates: Dictionary of updates to apply
            merge: If True, merge with existing; if False, replace fields
            
        Returns:
            Updated UserContext
        """
        context = self.get_context(user_id)
        
        if merge:
            # Merge updates into existing context
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        else:
            # Direct field replacement
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        
        context.last_updated = datetime.now().isoformat()
        self._save_context(user_id, context)
        
        logger.debug(f"Updated context for user {user_id}")
        return context
    
    def add_to_history(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        intent: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> None:
        """
        Add conversation turn to history
        
        Args:
            user_id: User identifier
            user_message: User's message
            assistant_response: Assistant's response
            intent: Recognized intent (optional)
            workflow_id: Associated workflow ID (optional)
        """
        context = self.get_context(user_id)
        
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            assistant_response=assistant_response,
            intent=intent,
            workflow_id=workflow_id
        )
        
        context.conversation_history.append(asdict(turn))
        
        # Keep only last N turns
        if len(context.conversation_history) > self.max_history:
            context.conversation_history = context.conversation_history[-self.max_history:]
        
        context.last_updated = datetime.now().isoformat()
        self._save_context(user_id, context)
        
        logger.debug(f"Added turn to history for user {user_id}")
    
    def set_active_workflow(
        self,
        user_id: str,
        workflow_name: str,
        workflow_data: Dict[str, Any]
    ) -> None:
        """
        Track active workflow for user
        
        Args:
            user_id: User identifier
            workflow_name: Name of workflow
            workflow_data: Workflow state data
        """
        context = self.get_context(user_id)
        context.active_workflows[workflow_name] = workflow_data
        context.last_updated = datetime.now().isoformat()
        self._save_context(user_id, context)
        
        logger.info(f"Set active workflow '{workflow_name}' for user {user_id}")
    
    def clear_workflow(self, user_id: str, workflow_name: str) -> None:
        """Clear completed workflow from context"""
        context = self.get_context(user_id)
        if workflow_name in context.active_workflows:
            del context.active_workflows[workflow_name]
            context.last_updated = datetime.now().isoformat()
            self._save_context(user_id, context)
            logger.info(f"Cleared workflow '{workflow_name}' for user {user_id}")
    
    def get_recent_history(self, user_id: str, num_turns: int = 3) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        context = self.get_context(user_id)
        return context.conversation_history[-num_turns:] if context.conversation_history else []
    
    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference"""
        context = self.get_context(user_id)
        context.preferences[key] = value
        context.last_updated = datetime.now().isoformat()
        self._save_context(user_id, context)
        logger.debug(f"Set preference {key}={value} for user {user_id}")
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference"""
        context = self.get_context(user_id)
        return context.preferences.get(key, default)
    
    def _save_context(self, user_id: str, context: UserContext) -> None:
        """Internal: Save context to storage"""
        context_key = f"context:{user_id}"
        context_json = json.dumps(context.to_dict())
        
        # Save to Redis if available
        if self.redis_available:
            try:
                self.redis_client.setex(
                    context_key,
                    self.ttl_seconds,
                    context_json
                )
                logger.debug(f"Saved context to Redis for user {user_id}")
            except Exception as e:
                logger.error(f"Redis save failed: {e}")
                # Fall through to fallback
        
        # Always save to fallback if enabled
        if self.use_fallback:
            self._fallback_storage[user_id] = context
            logger.debug(f"Saved context to fallback for user {user_id}")
    
    def clear_context(self, user_id: str) -> None:
        """Clear all context for user"""
        context_key = f"context:{user_id}"
        
        if self.redis_available:
            try:
                self.redis_client.delete(context_key)
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
        
        if user_id in self._fallback_storage:
            del self._fallback_storage[user_id]
        
        logger.info(f"Cleared context for user {user_id}")
