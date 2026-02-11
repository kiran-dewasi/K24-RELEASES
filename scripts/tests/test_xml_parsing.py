import pytest
from backend.tally_xml_builder import parse_xml_safely as parse_xml_txb
from backend.tally_connector import parse_xml_safely, TallyConnector
import pandas as pd


def test_parse_xml_safely():
    broken_xml = "<root><child>data</child"
    assert parse_xml_safely(broken_xml) is None
    good_xml = "<root><child>data</child></root>"
    assert parse_xml_safely(good_xml) is not None

def test_parse_xml_safely_xml_builder():
    broken_xml = "<root><child>data</child"
    assert parse_xml_txb(broken_xml) is None
    good_xml = "<root><child>data</child></root>"
    assert parse_xml_txb(good_xml) is not None

def test_parse_ledger_xml_valid():
    xml = """
    <ENVELOPE><LEDGER><NAME>Test</NAME><AMOUNT>100</AMOUNT></LEDGER></ENVELOPE>
    """
    df = TallyConnector._parse_ledger_xml(xml)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert 'NAME' in df.columns
    assert df.iloc[0]['NAME'] == 'Test'

def test_parse_ledger_xml_invalid():
    xml = "<ENVELOPE><LEDGER><NAME>Test</NAME>"
    df = TallyConnector._parse_ledger_xml(xml)
    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_parse_voucher_xml_valid():
    xml = """
    <ENVELOPE><VOUCHER><DETAIL>OK</DETAIL></VOUCHER></ENVELOPE>
    """
    df = TallyConnector._parse_voucher_xml(xml)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert 'DETAIL' in df.columns
    assert df.iloc[0]['DETAIL'] == 'OK'

def test_parse_voucher_xml_invalid():
    xml = "<ENVELOPE><VOUCHER><DETAIL>OK"
    df = TallyConnector._parse_voucher_xml(xml)
    assert isinstance(df, pd.DataFrame)
    assert df.empty
