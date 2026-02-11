from backend.compliance.gst_engine import GSTEngine

def test_gst_logic():
    print("🔍 Testing GST Logic...")
    
    # 1. Test GSTIN Validation
    valid_gstin = "27ABCDE1234F1Z5" # Maharashtra
    invalid_gstin_len = "27ABCDE1234F1Z" # Short
    invalid_gstin_state = "99ABCDE1234F1Z5" # Invalid State
    
    assert GSTEngine.validate_gstin(valid_gstin)["valid"] == True
    assert GSTEngine.validate_gstin(invalid_gstin_len)["valid"] == False
    assert GSTEngine.validate_gstin(invalid_gstin_state)["valid"] == False
    print("✅ GSTIN Validation Passed")
    
    # 2. Test Tax Calculation
    amount = 10000
    company_gstin = "27ABCDE1234F1Z5" # Maharashtra
    
    # Case A: Intra-State (Maharashtra to Maharashtra)
    party_gstin_intra = "27XYZAB5678G1Z9"
    tax_intra = GSTEngine.calculate_tax(amount, party_gstin_intra, company_gstin)
    assert tax_intra["type"] == "Intra-State"
    assert tax_intra["cgst"] == 900.0 # 9%
    assert tax_intra["sgst"] == 900.0 # 9%
    assert tax_intra["igst"] == 0.0
    print("✅ Intra-State Tax Calculation Passed")
    
    # Case B: Inter-State (Gujarat to Maharashtra)
    party_gstin_inter = "24XYZAB5678G1Z9" # Gujarat
    tax_inter = GSTEngine.calculate_tax(amount, party_gstin_inter, company_gstin)
    assert tax_inter["type"] == "Inter-State"
    assert tax_inter["igst"] == 1800.0 # 18%
    assert tax_inter["cgst"] == 0.0
    assert tax_inter["sgst"] == 0.0
    print("✅ Inter-State Tax Calculation Passed")
    
    print("🎉 All GST Tests Passed!")

if __name__ == "__main__":
    try:
        test_gst_logic()
    except AssertionError as e:
        print(f"❌ Test Failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
