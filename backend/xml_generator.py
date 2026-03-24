from datetime import datetime

def generate_sales_xml(party_name: str, amount: float, narration: str = "Created via K24 AI", revenue_ledger_name: str = "Sales") -> str:
    """Generate Tally Sales Voucher XML with dynamic Revenue Ledger"""
    today = datetime.now().strftime("%Y%m%d")
    
    # Updated: Credit "{revenue_ledger_name}"
    # Debit: Party (Receiver) -> is_deemed_positive = Yes
    # Credit: Revenue (Income) -> is_deemed_positive = No
    
    return f"""<ENVELOPE>
<HEADER> <TALLYREQUEST>Import Data</TALLYREQUEST> </HEADER> <BODY> <IMPORTDATA> <REQUESTDESC> <REPORTNAME>Vouchers</REPORTNAME> </REQUESTDESC> <REQUESTDATA> <TALLYMESSAGE xmlns:UDF="TallyUDF"> <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Accounting Voucher View"> <DATE>{today}</DATE> <NARRATION>{narration}</NARRATION> <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME> <PARTYLEDGERNAME>{party_name}</PARTYLEDGERNAME> <EFFECTIVEDATE>{today}</EFFECTIVEDATE> <ALLLEDGERENTRIES.LIST> <LEDGERNAME>{party_name}</LEDGERNAME> <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE> <AMOUNT>{-amount}</AMOUNT> </ALLLEDGERENTRIES.LIST> <ALLLEDGERENTRIES.LIST> <LEDGERNAME>{revenue_ledger_name}</LEDGERNAME> <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE> <AMOUNT>{amount}</AMOUNT> </ALLLEDGERENTRIES.LIST> </VOUCHER> </TALLYMESSAGE> </REQUESTDATA> </IMPORTDATA> </BODY> </ENVELOPE>"""

def generate_validated_sales_xml(party_name: str, amount: float, narration: str = "Created via K24 AI") -> str:
    """
    Ensure required ledgers exist, then return Sales voucher XML.
    Raises Exception if prerequisites cannot be satisfied.
    """
    from tally_preflight import ensure_all_prerequisites
    
    ok = ensure_all_prerequisites(party_name)
    if not ok:
        raise Exception("Failed to ensure required ledgers exist in Tally.")
        
    return generate_sales_xml(party_name, amount, narration=narration)

def generate_ledger_xml(ledger_name: str, parent: str = "Sundry Debtors", opening_balance: float = 0) -> str:
    """Generate Tally Ledger XML"""

    return f"""<ENVELOPE>
<HEADER> <TALLYREQUEST>Import Data</TALLYREQUEST> </HEADER> <BODY> <IMPORTDATA> <REQUESTDESC> <REPORTNAME>All Masters</REPORTNAME> </REQUESTDESC> <REQUESTDATA> <TALLYMESSAGE xmlns:UDF="TallyUDF"> <LEDGER NAME="{ledger_name}" ACTION="Create"> <NAME.LIST> <NAME>{ledger_name}</NAME> </NAME.LIST> <PARENT>{parent}</PARENT> <OPENINGBALANCE>{opening_balance}</OPENINGBALANCE> </LEDGER> </TALLYMESSAGE> </REQUESTDATA> </IMPORTDATA> </BODY> </ENVELOPE>"""

def generate_tally_sales_xml(party_name: str, amount: float, ledger: str = "Sales") -> str:
    """
    Wrapper for generate_sales_xml to match Phase D requirements.
    Passes 'ledger' argument as 'revenue_ledger_name'.
    """
    return generate_sales_xml(party_name, amount, revenue_ledger_name=ledger)

