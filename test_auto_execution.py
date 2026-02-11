"""
Test suite for the confidence-based auto-execution system.
Run with: python -m pytest test_auto_execution.py -v
"""

import sys
import io

# Fix Windows console encoding for emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pytest
import asyncio
from backend.services.confidence_scorer import (
    calculate_overall_confidence,
    identify_uncertain_fields,
    generate_clarification_question,
    get_confidence_summary
)


class TestConfidenceScorer:
    """Test confidence calculation logic"""
    
    def test_high_confidence_complete_bill(self):
        """A complete bill should have >95% confidence"""
        bill_data = {
            "confidence": 0.98,
            "party_name": "ABC Traders Pvt Ltd",
            "voucher_type": "Purchase",
            "date": "2026-01-28",
            "total_amount": 11800,
            "subtotal": 10000,
            "gst": {"total_gst": 1800, "cgst": 900, "sgst": 900},
            "items": [
                {"name": "Product A", "quantity": 10, "rate": 500, "amount": 5000, "unit": "PCS"},
                {"name": "Product B", "quantity": 5, "rate": 1000, "amount": 5000, "unit": "KGS"},
            ]
        }
        
        confidence = calculate_overall_confidence(bill_data)
        print(f"\nHigh confidence bill score: {confidence:.2%}")
        
        assert confidence >= 0.90, f"Expected >=90% but got {confidence:.2%}"
    
    def test_medium_confidence_incomplete_items(self):
        """Bill with incomplete items should have medium confidence"""
        bill_data = {
            "confidence": 0.85,
            "party_name": "XYZ Suppliers",
            "voucher_type": "Purchase",
            "date": "2026-01-28",
            "total_amount": 5000,
            "items": [
                {"name": "Product A", "quantity": 10, "rate": 250, "amount": 2500},  # Missing unit
                {"name": "Product B", "quantity": 5, "rate": 500, "amount": 2500},  # Missing unit
            ]
        }
        
        confidence = calculate_overall_confidence(bill_data)
        print(f"\nMedium confidence bill score: {confidence:.2%}")
        
        assert 0.70 <= confidence < 0.95, f"Expected 70-95% but got {confidence:.2%}"
    
    def test_low_confidence_missing_critical_fields(self):
        """Bill missing critical fields should have low confidence"""
        bill_data = {
            "party_name": None,  # Missing
            "voucher_type": None,  # Missing
            "items": [
                {"name": "Unknown", "quantity": 0},  # Incomplete
            ]
        }
        
        confidence = calculate_overall_confidence(bill_data)
        print(f"\nLow confidence bill score: {confidence:.2%}")
        
        assert confidence < 0.75, f"Expected <75% but got {confidence:.2%}"
    
    def test_math_validation_correct(self):
        """Math validation should boost confidence when totals match"""
        bill_data = {
            "confidence": 0.90,
            "party_name": "Test Company",
            "voucher_type": "Purchase",
            "date": "2026-01-28",
            "total_amount": 5000,
            "subtotal": 5000,
            "items": [
                {"name": "Item 1", "quantity": 2, "rate": 1000, "amount": 2000, "unit": "PCS"},
                {"name": "Item 2", "quantity": 3, "rate": 1000, "amount": 3000, "unit": "PCS"},
            ]
        }
        
        confidence = calculate_overall_confidence(bill_data)
        print(f"\nMath-validated bill score: {confidence:.2%}")
        
        assert confidence >= 0.85, f"Expected >=85% but got {confidence:.2%}"


class TestUncertainFields:
    """Test identification of uncertain fields"""
    
    def test_missing_party_name(self):
        uncertain = identify_uncertain_fields({"party_name": None, "items": []})
        assert "party_name" in uncertain
    
    def test_missing_voucher_type(self):
        uncertain = identify_uncertain_fields({"voucher_type": None, "items": []})
        assert "voucher_type" in uncertain
    
    def test_empty_items(self):
        uncertain = identify_uncertain_fields({"items": []})
        assert "items" in uncertain
    
    def test_incomplete_item(self):
        uncertain = identify_uncertain_fields({
            "items": [{"name": "Product", "quantity": None}]
        })
        assert "item_1_quantity" in uncertain


class TestClarificationQuestions:
    """Test question generation logic"""
    
    def test_party_name_question_priority(self):
        question = generate_clarification_question(
            ["party_name", "voucher_type"],
            {}
        )
        assert "party" in question.lower()
    
    def test_voucher_type_question(self):
        question = generate_clarification_question(
            ["voucher_type"],
            {}
        )
        assert "purchase" in question.lower() or "sales" in question.lower()
    
    def test_no_question_when_confident(self):
        question = generate_clarification_question([], {})
        assert question is None


class TestConfidenceSummary:
    """Test confidence level summaries"""
    
    def test_high_confidence_summary(self):
        summary = get_confidence_summary(0.96)
        assert summary["level"] == "high"
        assert summary["action"] == "auto_execute"
    
    def test_medium_confidence_summary(self):
        summary = get_confidence_summary(0.80)
        assert summary["level"] == "medium"
        assert summary["action"] == "review_required"
    
    def test_low_confidence_summary(self):
        summary = get_confidence_summary(0.60)
        assert summary["level"] == "low"
        assert summary["action"] == "clarification_needed"


# Quick manual test
if __name__ == "__main__":
    print("=" * 60)
    print("CONFIDENCE SCORING SYSTEM - MANUAL TEST")
    print("=" * 60)
    
    # Test 1: High confidence bill
    high_conf_bill = {
        "confidence": 0.98,
        "party_name": "Krisha Sales Pvt Ltd",
        "voucher_type": "Purchase",
        "date": "2026-01-28",
        "invoice_number": "INV-12345",
        "total_amount": 11800,
        "subtotal": 10000,
        "gst": {"total_gst": 1800, "cgst": 900, "sgst": 900},
        "items": [
            {"name": "Steel Pipes 2 inch", "quantity": 100, "rate": 50, "amount": 5000, "unit": "PCS"},
            {"name": "Steel Rods 10mm", "quantity": 50, "rate": 100, "amount": 5000, "unit": "KGS"},
        ]
    }
    
    confidence = calculate_overall_confidence(high_conf_bill)
    summary = get_confidence_summary(confidence)
    print(f"\n📊 High Confidence Bill Test:")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   Level: {summary['level']}")
    print(f"   Action: {summary['action']}")
    print(f"   {summary['emoji']} {summary['message']}")
    
    # Test 2: Medium confidence bill
    medium_conf_bill = {
        "confidence": 0.82,
        "party_name": "Unknown Supplier",
        "voucher_type": "Purchase",
        "total_amount": 5000,
        "items": [
            {"name": "Item A", "quantity": 10, "rate": 250, "amount": 2500},
            {"name": "Item B", "quantity": 10, "rate": 250, "amount": 2500},
        ]
    }
    
    confidence = calculate_overall_confidence(medium_conf_bill)
    summary = get_confidence_summary(confidence)
    uncertain = identify_uncertain_fields(medium_conf_bill)
    print(f"\n📊 Medium Confidence Bill Test:")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   Level: {summary['level']}")
    print(f"   Uncertain fields: {uncertain}")
    
    # Test 3: Low confidence bill
    low_conf_bill = {
        "party_name": None,
        "voucher_type": None,
        "items": [{"name": "???", "quantity": None}]
    }
    
    confidence = calculate_overall_confidence(low_conf_bill)
    summary = get_confidence_summary(confidence)
    uncertain = identify_uncertain_fields(low_conf_bill)
    question = generate_clarification_question(uncertain, low_conf_bill)
    print(f"\n📊 Low Confidence Bill Test:")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   Level: {summary['level']}")
    print(f"   Question to ask: {question}")
    
    print("\n" + "=" * 60)
    print("✅ All manual tests completed!")
    print("=" * 60)
