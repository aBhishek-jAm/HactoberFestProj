"""InvoicePilot AI — Backend unit tests.

Tests cover PDF extraction, AI response parsing, validation,
exports, API endpoints, and formula injection protection.
All AI calls are mocked so tests run without Ollama.
"""

import io
import json
import os
import pytest
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Document, Invoice, LineItem
from app.schemas import AIExtractionResult, AILineItem
from app.services.validator import InvoiceValidator
from app.services.exporter import ExportService, _sanitize_cell


# ──────────────────────────────────────────
# Test Database Setup
# ──────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_invoicepilot.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_document(db_session):
    """Insert a sample document for testing."""
    doc = Document(
        id="test-doc-001",
        original_filename="test_invoice.pdf",
        stored_filename="abc123.pdf",
        file_type="pdf",
        file_size=1024,
        file_hash="aabbccdd",
        status="completed",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def sample_invoice(db_session, sample_document):
    """Insert a sample invoice with line items."""
    invoice = Invoice(
        id="test-inv-001",
        document_id=sample_document.id,
        vendor_name="Test Vendor LLC",
        invoice_number="INV-2026-001",
        invoice_date="2026-10-01",
        due_date="2026-11-01",
        currency="USD",
        subtotal=1000.00,
        tax_amount=100.00,
        discount=0.00,
        total_amount=1100.00,
        amount_paid=None,
        outstanding_amount=1100.00,
        payment_status="unpaid",
        expense_category="Office Supplies",
        document_type="invoice",
        confidence=0.85,
        review_status="pending",
    )
    db_session.add(invoice)

    line = LineItem(
        invoice_id=invoice.id,
        description="Office stationery pack",
        quantity=5,
        unit_price=200.00,
        tax_amount=100.00,
        line_total=1100.00,
    )
    db_session.add(line)
    db_session.commit()
    return invoice


# ──────────────────────────────────────────
# AI Extraction Result Parsing Tests
# ──────────────────────────────────────────


class TestAIExtractionSchema:
    """Test Pydantic schema validation for AI model output."""

    def test_valid_full_response(self):
        data = {
            "vendor_name": "Example Corp",
            "invoice_number": "INV-100",
            "invoice_date": "2026-10-10",
            "due_date": "2026-11-10",
            "currency": "USD",
            "subtotal": 500.00,
            "tax_amount": 50.00,
            "discount": 10.00,
            "total_amount": 540.00,
            "amount_paid": 0,
            "outstanding_amount": 540.00,
            "payment_status": "unpaid",
            "expense_category": "Office Supplies",
            "document_type": "invoice",
            "line_items": [
                {
                    "description": "Widget A",
                    "quantity": 5,
                    "unit_price": 100.00,
                    "tax_amount": 50.00,
                    "line_total": 550.00,
                }
            ],
        }
        result = AIExtractionResult.model_validate(data)
        assert result.vendor_name == "Example Corp"
        assert result.total_amount == 540.00
        assert len(result.line_items) == 1

    def test_null_fields_accepted(self):
        data = {
            "vendor_name": "Test",
            "invoice_number": None,
            "invoice_date": None,
            "total_amount": None,
        }
        result = AIExtractionResult.model_validate(data)
        assert result.invoice_number is None
        assert result.total_amount is None

    def test_negative_amount_rejected(self):
        data = {"total_amount": -500.00, "subtotal": -100}
        result = AIExtractionResult.model_validate(data)
        assert result.total_amount is None
        assert result.subtotal is None

    def test_invalid_payment_status_normalized(self):
        data = {"payment_status": "COMPLETED"}
        result = AIExtractionResult.model_validate(data)
        assert result.payment_status is None  # Not in valid set

    def test_valid_payment_status(self):
        for status in ["paid", "PAID", "Unpaid", "partial"]:
            result = AIExtractionResult.model_validate({"payment_status": status})
            assert result.payment_status in {"paid", "unpaid", "partial"}

    def test_document_type_normalized(self):
        result = AIExtractionResult.model_validate({"document_type": "INVOICE"})
        assert result.document_type == "invoice"

        result = AIExtractionResult.model_validate({"document_type": "unknown_thing"})
        assert result.document_type == "other"

    def test_empty_input(self):
        result = AIExtractionResult.model_validate({})
        assert result.vendor_name is None
        assert result.document_type is None  # No default when not provided

    def test_extra_fields_ignored(self):
        data = {"vendor_name": "Test", "unknown_field": "hello", "extra": 123}
        result = AIExtractionResult.model_validate(data)
        assert result.vendor_name == "Test"


# ──────────────────────────────────────────
# AI Response Parsing Tests
# ──────────────────────────────────────────


class TestAIResponseParsing:
    """Test parsing raw model output into structured results."""

    def test_clean_json(self):
        from app.services.ai_extractor import AIExtractor
        extractor = AIExtractor()

        raw = '{"vendor_name": "Test Co", "total_amount": 100.00}'
        result = extractor._parse_response(raw)
        assert result.vendor_name == "Test Co"

    def test_json_with_markdown_fences(self):
        from app.services.ai_extractor import AIExtractor
        extractor = AIExtractor()

        raw = '```json\n{"vendor_name": "Test", "total_amount": 50}\n```'
        result = extractor._parse_response(raw)
        assert result.vendor_name == "Test"

    def test_json_with_surrounding_text(self):
        from app.services.ai_extractor import AIExtractor
        extractor = AIExtractor()

        raw = 'Here is the extracted data:\n{"vendor_name": "X Corp"}\nDone.'
        result = extractor._parse_response(raw)
        assert result.vendor_name == "X Corp"

    def test_no_json_raises(self):
        from app.services.ai_extractor import AIExtractor
        extractor = AIExtractor()

        with pytest.raises(json.JSONDecodeError):
            extractor._parse_response("No JSON here at all")

    def test_malformed_json_raises(self):
        from app.services.ai_extractor import AIExtractor
        extractor = AIExtractor()

        with pytest.raises(json.JSONDecodeError):
            extractor._parse_response('{"vendor_name": "unclosed')


# ──────────────────────────────────────────
# Validation Tests
# ──────────────────────────────────────────


class TestInvoiceValidator:
    """Test deterministic validation checks."""

    def test_arithmetic_match(self):
        validator = InvoiceValidator(tolerance=0.02)
        data = AIExtractionResult(
            vendor_name="Test",
            subtotal=1000.00,
            tax_amount=180.00,
            discount=0.00,
            total_amount=1180.00,
        )
        issues, confidence = validator.validate(data)
        # Should have no arithmetic issues
        arith_issues = [i for i in issues if i["field"] == "total_amount" and "mismatch" in i["message"]]
        assert len(arith_issues) == 0

    def test_arithmetic_mismatch(self):
        validator = InvoiceValidator(tolerance=0.02)
        data = AIExtractionResult(
            vendor_name="Test",
            subtotal=1000.00,
            tax_amount=180.00,
            discount=0.00,
            total_amount=1500.00,  # Wrong!
        )
        issues, confidence = validator.validate(data)
        arith_issues = [i for i in issues if "mismatch" in i.get("message", "")]
        assert len(arith_issues) > 0

    def test_missing_fields_warning(self):
        validator = InvoiceValidator()
        data = AIExtractionResult()  # All empty
        issues, confidence = validator.validate(data)
        field_names = [i["field"] for i in issues]
        assert "vendor_name" in field_names
        assert "total_amount" in field_names

    def test_invalid_date_format(self):
        validator = InvoiceValidator()
        data = AIExtractionResult(
            vendor_name="Test",
            invoice_date="not-a-date",
            total_amount=100.00,
        )
        issues, _ = validator.validate(data)
        date_issues = [i for i in issues if i["field"] == "invoice_date" and "Invalid" in i["message"]]
        assert len(date_issues) > 0

    def test_due_date_before_invoice_date(self):
        validator = InvoiceValidator()
        data = AIExtractionResult(
            vendor_name="Test",
            invoice_date="2026-10-15",
            due_date="2026-10-01",  # Before invoice date
            total_amount=100.00,
        )
        issues, _ = validator.validate(data)
        due_issues = [i for i in issues if i["field"] == "due_date" and "before" in i["message"]]
        assert len(due_issues) > 0

    def test_invalid_currency(self):
        validator = InvoiceValidator()
        data = AIExtractionResult(
            vendor_name="Test",
            currency="INVALID",
            total_amount=100.00,
        )
        issues, _ = validator.validate(data)
        cur_issues = [i for i in issues if i["field"] == "currency"]
        assert len(cur_issues) > 0

    def test_payment_status_inconsistency(self):
        validator = InvoiceValidator()
        data = AIExtractionResult(
            vendor_name="Test",
            payment_status="paid",
            outstanding_amount=500.00,
            total_amount=500.00,
        )
        issues, _ = validator.validate(data)
        pay_issues = [i for i in issues if i["field"] == "payment_status"]
        assert len(pay_issues) > 0

    def test_confidence_scoring(self):
        validator = InvoiceValidator()
        # Complete data should have high confidence
        full = AIExtractionResult(
            vendor_name="Test",
            invoice_number="INV-001",
            invoice_date="2026-10-01",
            currency="USD",
            subtotal=100,
            tax_amount=10,
            total_amount=110,
            expense_category="Office Supplies",
        )
        _, confidence = validator.validate(full)
        assert confidence >= 0.8

        # Empty data should have low confidence
        empty = AIExtractionResult()
        _, confidence = validator.validate(empty)
        assert confidence < 0.6

    def test_duplicate_detection(self, db_session, sample_invoice):
        validator = InvoiceValidator()
        data = AIExtractionResult(
            vendor_name="Test Vendor LLC",
            invoice_number="INV-2026-001",
            total_amount=1100.00,
        )
        issues, _ = validator.validate(data, db=db_session)
        dup_issues = [i for i in issues if "duplicate" in i.get("message", "").lower()]
        assert len(dup_issues) > 0


# ──────────────────────────────────────────
# Export Tests
# ──────────────────────────────────────────


class TestExportService:
    """Test CSV and Excel export functionality."""

    def _make_invoices(self, db_session, sample_invoice):
        """Get list of invoices for export."""
        return db_session.query(Invoice).all()

    def test_csv_export(self, db_session, sample_invoice):
        service = ExportService()
        invoices = self._make_invoices(db_session, sample_invoice)
        buffer = service.export_csv(invoices)
        content = buffer.read().decode("utf-8-sig")
        assert "Test Vendor LLC" in content
        assert "INV-2026-001" in content
        assert "1100" in content

    def test_xlsx_export(self, db_session, sample_invoice):
        service = ExportService()
        invoices = self._make_invoices(db_session, sample_invoice)
        buffer = service.export_xlsx(invoices)
        # Should produce valid xlsx bytes
        data = buffer.read()
        assert len(data) > 100
        # XLSX files start with PK (zip format)
        assert data[:2] == b"PK"

    def test_formula_injection_protection(self):
        assert _sanitize_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
        assert _sanitize_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
        assert _sanitize_cell("-1+2") == "'-1+2"
        assert _sanitize_cell("@SUM(A1)") == "'@SUM(A1)"
        assert _sanitize_cell("Normal text") == "Normal text"
        assert _sanitize_cell(None) == ""
        assert _sanitize_cell(42) == "42"

    def test_empty_export(self):
        service = ExportService()
        buffer = service.export_csv([])
        content = buffer.read().decode("utf-8-sig")
        # Empty invoice list produces minimal CSV
        assert isinstance(content, str)


# ──────────────────────────────────────────
# API Tests
# ──────────────────────────────────────────


class TestHealthEndpoints:
    """Test health check API endpoints."""

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"

    def test_ai_health(self):
        resp = client.get("/api/health/ai")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "model" in data


class TestDocumentAPI:
    """Test document CRUD endpoints."""

    def test_upload_invalid_type(self):
        """Reject unsupported file types."""
        file = io.BytesIO(b"not a real file")
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("test.txt", file, "text/plain"))],
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_upload_empty_file(self):
        """Reject empty files."""
        file = io.BytesIO(b"")
        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("test.pdf", file, "application/pdf"))],
        )
        assert resp.status_code == 400

    def test_list_documents_empty(self):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_nonexistent_document(self):
        resp = client.get("/api/documents/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_nonexistent_document(self):
        resp = client.delete("/api/documents/nonexistent-id")
        assert resp.status_code == 404

    def test_dashboard_empty(self):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0
        assert data["currency_summaries"] == []

    def test_dashboard_with_data(self, sample_invoice):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 1
        assert data["processed_count"] == 1

    def test_expense_report_empty(self):
        resp = client.get("/api/reports/expenses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoices"] == 0

    def test_export_csv_no_data(self):
        resp = client.get("/api/exports/csv")
        assert resp.status_code == 404

    def test_export_csv_with_data(self, sample_invoice):
        resp = client.get("/api/exports/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_export_xlsx_with_data(self, sample_invoice):
        resp = client.get("/api/exports/xlsx")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]


class TestDocumentUpdate:
    """Test document update (user corrections)."""

    def test_update_invoice(self, sample_invoice):
        resp = client.patch(
            "/api/documents/test-doc-001",
            json={"vendor_name": "Updated Vendor", "review_status": "reviewed"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice"]["vendor_name"] == "Updated Vendor"
        assert data["invoice"]["review_status"] == "reviewed"
        assert data["invoice"]["user_edited"] is True

    def test_update_nonexistent(self):
        resp = client.patch("/api/documents/no-such-id", json={"vendor_name": "X"})
        assert resp.status_code == 404


# ──────────────────────────────────────────
# Currency Handling Tests
# ──────────────────────────────────────────


class TestCurrencyHandling:
    """Verify that currencies are never silently mixed."""

    def test_dashboard_groups_by_currency(self, db_session):
        """Dashboard should group totals by currency, not mix them."""
        # Create two invoices in different currencies
        doc1 = Document(id="cur-doc-1", original_filename="a.pdf", stored_filename="a1.pdf",
                       file_type="pdf", file_size=100, status="completed")
        doc2 = Document(id="cur-doc-2", original_filename="b.pdf", stored_filename="b1.pdf",
                       file_type="pdf", file_size=100, status="completed")
        db_session.add_all([doc1, doc2])
        db_session.commit()

        inv1 = Invoice(document_id="cur-doc-1", vendor_name="A", currency="USD",
                      total_amount=100, review_status="pending")
        inv2 = Invoice(document_id="cur-doc-2", vendor_name="B", currency="EUR",
                      total_amount=200, review_status="pending")
        db_session.add_all([inv1, inv2])
        db_session.commit()

        resp = client.get("/api/dashboard/summary")
        data = resp.json()
        assert len(data["currency_summaries"]) == 2
        currencies = {s["currency"] for s in data["currency_summaries"]}
        assert "USD" in currencies
        assert "EUR" in currencies


# ──────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────


@pytest.fixture(autouse=True, scope="session")
def cleanup_test_db():
    yield
    try:
        if os.path.exists("./test_invoicepilot.db"):
            os.remove("./test_invoicepilot.db")
    except PermissionError:
        pass  # Windows may hold a lock on SQLite file
