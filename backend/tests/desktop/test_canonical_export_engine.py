"""
Tests for CanonicalExportEngine
"""
import sys
import os
import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from database import SessionLocal
from services.canonical_export_engine import CanonicalExportEngine

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def engine(db_session):
    return CanonicalExportEngine(db=db_session, tenant_id="default")

def test_generate_export_bytes_pdf(engine):
    filters = {
        "date_from": "2024-04-01",
        "date_to": "2025-03-31"
    }
    result = engine.generate_export_bytes(report_type="sales-register", format="pdf", filters=filters)
    assert "bytes" in result
    assert result["bytes"], "bytes should not be empty"
    assert len(result["bytes"]) > 500
    assert result["mime_type"] == "application/pdf"
    assert result["filename"].endswith(".pdf")

def test_generate_export_bytes_excel(engine):
    filters = {
        "date_from": "2024-04-01",
        "date_to": "2025-03-31"
    }
    result = engine.generate_export_bytes(report_type="sales-register", format="excel", filters=filters)
    assert "bytes" in result
    assert result["bytes"], "bytes should not be empty"
    assert len(result["bytes"]) > 500
    assert result["mime_type"].startswith("application/vnd")
    assert result["filename"].endswith(".xlsx")

def test_generate_export_file_writes_file(engine):
    filters = {
        "date_from": "2024-04-01",
        "date_to": "2025-03-31"
    }
    result = engine.generate_export_file(report_type="sales-register", format="pdf", filters=filters)
    
    file_path = result.get("file_path")
    filename = result.get("filename")
    
    assert file_path, "file_path should not be empty"
    assert os.path.isabs(file_path), "file_path should be absolute"
    assert os.path.exists(file_path), "File should exist on disk"
    assert os.path.getsize(file_path) > 500, "File size should be > 500 bytes"
    assert filename.endswith(".pdf")
