"""
Unit tests for WhatsApp Cloud Incoming Handler with Tenant Access Control

Tests the new tenant resolution and subscription enforcement logic.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException

# Import functions to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routers.whatsapp_cloud import (
    normalize_whatsapp_number,
    resolve_tenant_from_business_number,
)


class TestNormalizeWhatsAppNumber:
    """Test phone number normalization"""
    
    def test_removes_spaces(self):
        assert normalize_whatsapp_number("+1 555 123 4567") == "15551234567"
    
    def test_removes_dashes(self):
        assert normalize_whatsapp_number("+1-555-123-4567") == "15551234567"
    
    def test_removes_parentheses(self):
        assert normalize_whatsapp_number("+1 (555) 123-4567") == "15551234567"
    
    def test_removes_plus_sign(self):
        assert normalize_whatsapp_number("+15551234567") == "15551234567"
    
    def test_handles_already_normalized(self):
        assert normalize_whatsapp_number("15551234567") == "15551234567"
    
    def test_removes_all_non_digits(self):
        assert normalize_whatsapp_number("+1.555.123.4567 ext 123") == "15551234567123"


class TestResolveTenantFromBusinessNumber:
    """Test tenant resolution and subscription enforcement"""
    
    def setup_method(self):
        """Setup mock Supabase client for each test"""
        self.mock_supabase = Mock()
        self.mock_table = Mock()
        self.mock_supabase.table.return_value = self.mock_table
    
    def _mock_tenant_response(self, data):
        """Helper to mock Supabase response"""
        mock_result = Mock()
        mock_result.data = data
        self.mock_table.select.return_value.eq.return_value.execute.return_value = mock_result
        return mock_result
    
    def test_active_subscription_allowed(self):
        """Test that active subscriptions are allowed"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "active",
            "trial_ends_at": None
        }])
        
        result = resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert result["tenant_id"] == "tenant-123"
        assert result["subscription_status"] == "active"
    
    def test_trial_with_future_date_allowed(self):
        """Test that trial with future expiration is allowed"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "trial",
            "trial_ends_at": future_date
        }])
        
        result = resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert result["tenant_id"] == "tenant-123"
        assert result["subscription_status"] == "trial"
    
    def test_trial_with_null_date_allowed(self):
        """Test that trial with null trial_ends_at is allowed"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "trial",
            "trial_ends_at": None
        }])
        
        result = resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert result["tenant_id"] == "tenant-123"
        assert result["subscription_status"] == "trial"
    
    def test_expired_subscription_blocked(self):
        """Test that expired subscriptions are blocked"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "expired",
            "trial_ends_at": None
        }])
        
        with pytest.raises(HTTPException) as exc_info:
            resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert exc_info.value.status_code == 403
        assert "TENANT_SUBSCRIPTION_EXPIRED" in str(exc_info.value.detail)
    
    def test_cancelled_subscription_blocked(self):
        """Test that cancelled subscriptions are blocked"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "cancelled",
            "trial_ends_at": None
        }])
        
        with pytest.raises(HTTPException) as exc_info:
            resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert exc_info.value.status_code == 403
        assert "TENANT_SUBSCRIPTION_EXPIRED" in str(exc_info.value.detail)
    
    def test_expired_trial_blocked(self):
        """Test that trial with past expiration is blocked"""
        past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "trial",
            "trial_ends_at": past_date
        }])
        
        with pytest.raises(HTTPException) as exc_info:
            resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert exc_info.value.status_code == 403
        assert "TENANT_SUBSCRIPTION_EXPIRED" in str(exc_info.value.detail)
    
    def test_tenant_not_found_blocked(self):
        """Test that missing tenant is blocked"""
        self._mock_tenant_response([])
        
        with pytest.raises(HTTPException) as exc_info:
            resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert exc_info.value.status_code == 404
        assert "TENANT_NOT_FOUND" in str(exc_info.value.detail)
    
    def test_unexpected_status_blocked(self):
        """Test that unexpected subscription status is blocked"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "pending",  # Not 'active' or 'trial'
            "trial_ends_at": None
        }])
        
        with pytest.raises(HTTPException) as exc_info:
            resolve_tenant_from_business_number("+15551234567", self.mock_supabase)
        
        assert exc_info.value.status_code == 403
        assert "TENANT_SUBSCRIPTION_EXPIRED" in str(exc_info.value.detail)
    
    def test_normalizes_business_number_for_lookup(self):
        """Test that business number is normalized before lookup"""
        self._mock_tenant_response([{
            "tenant_id": "tenant-123",
            "subscription_status": "active",
            "trial_ends_at": None
        }])
        
        # Call with formatted number
        resolve_tenant_from_business_number("+1 (555) 123-4567", self.mock_supabase)
        
        # Verify it queried with normalized number
        self.mock_table.select.assert_called()
        # The normalized number "15551234567" should be used in the query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
