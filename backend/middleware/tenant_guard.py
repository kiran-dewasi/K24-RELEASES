"""
Tenant Guard Middleware - IDOR Protection
==========================================
Prevents Insecure Direct Object Reference attacks by ensuring
all database queries are filtered by the current user's tenant_id.

Usage:
    from middleware.tenant_guard import TenantGuard
    
    # In any endpoint:
    query = TenantGuard.filter(db.query(Voucher), Voucher, current_user)
    vouchers = query.all()  # Automatically filtered by tenant!
"""

import logging
from typing import TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TenantGuard:
    """
    Security middleware to prevent IDOR attacks.
    Ensures users can ONLY access their own tenant's data.
    """
    
    @staticmethod
    def filter(query: Any, model: Any, user: Any) -> Any:
        """
        Automatically append tenant filter to a SQLAlchemy query.
        
        Args:
            query: The SQLAlchemy query object (e.g., db.query(Voucher))
            model: The model class (e.g., Voucher)
            user: The current user object (must have tenant_id attribute)
        
        Returns:
            Query filtered by tenant_id
        
        Example:
            # Before (vulnerable to IDOR):
            voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
            
            # After (protected):
            voucher = TenantGuard.filter(db.query(Voucher), Voucher, current_user)\\
                      .filter(Voucher.id == voucher_id).first()
        
        Raises:
            ValueError if user has no tenant_id
        """
        # Validate user has tenant_id
        if not hasattr(user, 'tenant_id') or not user.tenant_id:
            logger.warning(f"[SECURITY] User {getattr(user, 'id', 'unknown')} has no tenant_id!")
            raise ValueError("User must have a tenant_id for data access")
        
        # Check if model has tenant_id column
        if hasattr(model, 'tenant_id'):
            logger.debug(f"[GUARD] Filtering {model.__name__} by tenant: {user.tenant_id}")
            return query.filter(model.tenant_id == user.tenant_id)
        
        # Model doesn't have tenant_id - return unfiltered (careful!)
        logger.warning(f"[GUARD] Model {model.__name__} has no tenant_id column!")
        return query
    
    @staticmethod  
    def verify_access(db_session: Any, model: Any, record_id: Any, user: Any) -> Any:
        """
        Verify user has access to a specific record by ID.
        Returns the record if access is allowed, None otherwise.
        
        This is safer than just filtering - it explicitly checks ownership.
        
        Args:
            db_session: SQLAlchemy session
            model: The model class
            record_id: The ID of the record to access
            user: The current user object
        
        Returns:
            The record if user has access, None if not found or forbidden
        
        Example:
            voucher = TenantGuard.verify_access(db, Voucher, voucher_id, current_user)
            if not voucher:
                raise HTTPException(403, "Forbidden")
        """
        if not hasattr(model, 'tenant_id'):
            # Model doesn't have tenant isolation - allow direct access
            return db_session.query(model).filter(model.id == record_id).first()
        
        # Must match tenant_id
        record = db_session.query(model).filter(
            model.id == record_id,
            model.tenant_id == user.tenant_id
        ).first()
        
        if not record:
            # Log potential attack attempt
            existing = db_session.query(model).filter(model.id == record_id).first()
            if existing:
                # Record exists but belongs to different tenant - IDOR attempt!
                logger.warning(
                    f"[SECURITY] IDOR BLOCKED! User {user.id} (tenant: {user.tenant_id}) "
                    f"tried to access {model.__name__} ID {record_id} "
                    f"(belongs to tenant: {existing.tenant_id})"
                )
        
        return record
    
    @staticmethod
    def inject_tenant(data: dict, user: Any) -> dict:
        """
        Inject tenant_id into data dict before creating a record.
        Ensures new records are always tagged with the user's tenant.
        
        Args:
            data: The data dict for creating a new record
            user: The current user object
        
        Returns:
            Data dict with tenant_id added
        
        Example:
            voucher_data = TenantGuard.inject_tenant({
                "party_name": "ABC Corp",
                "amount": 1000
            }, current_user)
            # voucher_data now has tenant_id = current_user.tenant_id
        """
        if not hasattr(user, 'tenant_id') or not user.tenant_id:
            raise ValueError("User must have a tenant_id to create records")
        
        data['tenant_id'] = user.tenant_id
        return data


def require_tenant(func):
    """
    Decorator to ensure current_user has a valid tenant_id.
    Use on any endpoint that deals with tenant-specific data.
    
    Example:
        @router.get("/ledgers")
        @require_tenant
        async def get_ledgers(current_user: User = Depends(get_current_user)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find current_user in kwargs
        current_user = kwargs.get('current_user')
        
        if not current_user:
            # Try to find it in positional args (less common)
            for arg in args:
                if hasattr(arg, 'tenant_id'):
                    current_user = arg
                    break
        
        if not current_user or not getattr(current_user, 'tenant_id', None):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Tenant context required for this operation"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


# Convenience exports
tenant_guard = TenantGuard()

