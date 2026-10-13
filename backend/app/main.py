"""InvoicePilot AI — FastAPI application and API routes.

This is the main entry point for the backend. All REST endpoints are
defined here for simplicity. In a larger app they would be split into
router modules.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Depends,
    HTTPException,
    Query,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, desc

from app.config import settings
from app.database import get_db, init_db
from app.models import Document, Invoice, LineItem, ProcessingJob
from app.schemas import (
    DocumentResponse,
    DocumentListResponse,
    InvoiceUpdate,
    InvoiceResponse,
    DashboardSummary,
    CurrencySummary,
    CategoryBreakdown,
    MonthlyTrend,
    HealthResponse,
    AIHealthResponse,
    ErrorResponse,
    ExportRequest,
)
from app.services.document_processor import document_processor
from app.services.ai_extractor import ai_extractor
from app.services.validator import invoice_validator
from app.services.exporter import export_service

# ──────────────────────────────────────────
# Logging (no document text in logs)
# ──────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("invoicepilot")

# ──────────────────────────────────────────
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and upload directory on startup."""
    init_db()
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info(
        "InvoicePilot AI started | model=%s | demo=%s",
        settings.ollama_model,
        settings.demo_mode,
    )
    yield


app = FastAPI(
    title="InvoicePilot AI",
    description="AI-powered invoice and receipt processing API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────
# Health Endpoints
# ──────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", database="connected", version="0.1.0")


@app.get("/api/health/ai", response_model=AIHealthResponse)
async def ai_health_check():
    result = await ai_extractor.check_connection()
    return AIHealthResponse(**result)


# ──────────────────────────────────────────
# Document Upload
# ──────────────────────────────────────────


@app.post("/api/documents/upload", response_model=list[DocumentResponse])
async def upload_documents(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Upload one or more documents for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    responses = []
    for upload_file in files:
        doc = await _handle_single_upload(upload_file, db)
        responses.append(doc)
        # Queue background processing
        background_tasks.add_task(_process_document, doc.id)

    return responses


async def _handle_single_upload(upload_file: UploadFile, db: Session) -> Document:
    """Validate and save a single uploaded file."""
    # Validate file extension
    original = upload_file.filename or "unknown"
    ext = Path(original).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Allowed: {settings.allowed_extensions}",
        )

    # Read file content
    content = await upload_file.read()

    # Validate size
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content)} bytes. Max: {settings.max_file_size_mb}MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Compute hash for dedup
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for exact duplicate file
    existing = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate file: this document was already uploaded as '{existing.original_filename}'",
        )

    # Generate safe stored filename (prevent path traversal)
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    stored_path = os.path.join(settings.upload_dir, stored_filename)

    # Ensure we're writing inside the upload directory
    real_upload_dir = os.path.realpath(settings.upload_dir)
    real_stored_path = os.path.realpath(stored_path)
    if not real_stored_path.startswith(real_upload_dir):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Save file
    with open(stored_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        original_filename=original,
        stored_filename=stored_filename,
        file_type=ext,
        file_size=len(content),
        file_hash=file_hash,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info("Uploaded document: %s (%s, %d bytes)", doc.id, ext, len(content))
    return doc


# ──────────────────────────────────────────
# Document Processing (background task)
# ──────────────────────────────────────────


async def _process_document(document_id: str):
    """Full extraction pipeline: text extraction → AI → validation → save."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error("Document %s not found for processing", document_id)
            return

        # Create processing job
        job = ProcessingJob(document_id=doc.id, status="running", started_at=datetime.now(timezone.utc))
        db.add(job)

        doc.status = "processing"
        db.commit()

        file_path = os.path.join(settings.upload_dir, doc.stored_filename)

        try:
            # Step 1: Extract text
            job.step = "text_extraction"
            db.commit()
            extracted_text = document_processor.extract_text(file_path)

            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValueError("Could not extract meaningful text from document")

            # Step 2: AI extraction
            job.step = "ai_extraction"
            db.commit()
            ai_result = await ai_extractor.extract(extracted_text)

            # Step 3: Validation
            job.step = "validation"
            db.commit()
            issues, confidence = invoice_validator.validate(ai_result, db)

            # Step 4: Save extracted data
            job.step = "saving"
            db.commit()

            # Determine review status based on issues
            error_issues = [i for i in issues if i["severity"] == "error"]
            warning_issues = [i for i in issues if i["severity"] == "warning"]

            if error_issues:
                review_status = "flagged"
            elif warning_issues:
                review_status = "pending"
            else:
                review_status = "pending"  # Never auto-mark as reviewed

            # Create Invoice record
            invoice = Invoice(
                document_id=doc.id,
                vendor_name=ai_result.vendor_name,
                vendor_address=ai_result.vendor_address,
                invoice_number=ai_result.invoice_number,
                invoice_date=ai_result.invoice_date,
                due_date=ai_result.due_date,
                currency=ai_result.currency or "USD",
                subtotal=ai_result.subtotal,
                tax_amount=ai_result.tax_amount,
                discount=ai_result.discount or 0.0,
                total_amount=ai_result.total_amount,
                amount_paid=ai_result.amount_paid,
                outstanding_amount=ai_result.outstanding_amount,
                payment_status=ai_result.payment_status,
                expense_category=ai_result.expense_category,
                document_type=ai_result.document_type or "invoice",
                confidence=confidence,
                review_status=review_status,
                validation_notes=json.dumps(issues) if issues else None,
                raw_extracted_json=json.dumps(ai_result.model_dump()),
            )
            db.add(invoice)

            # Save line items
            if ai_result.line_items:
                for item in ai_result.line_items:
                    line = LineItem(
                        invoice_id=invoice.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        tax_amount=item.tax_amount,
                        line_total=item.line_total,
                    )
                    db.add(line)

            doc.status = "completed"
            doc.processed_time = datetime.now(timezone.utc)

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

            db.commit()
            logger.info(
                "Document %s processed successfully (confidence=%.2f, issues=%d)",
                doc.id, confidence, len(issues),
            )

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)[:500]  # Truncate error
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.error("Processing failed for %s: %s", doc.id, str(e)[:200])

    except Exception as e:
        logger.error("Fatal processing error for %s: %s", document_id, str(e)[:200])
    finally:
        db.close()


# ──────────────────────────────────────────
# Document CRUD
# ──────────────────────────────────────────


@app.get("/api/documents", response_model=list[DocumentListResponse])
def list_documents(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("upload_time"),
    sort_order: Optional[str] = Query("desc"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List documents with search and filtering."""
    query = db.query(Document)

    if status:
        query = query.filter(Document.status == status)

    # Join with Invoice for invoice-specific filters
    if any([search, category, currency, review_status, date_from, date_to]):
        query = query.outerjoin(Invoice)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Invoice.vendor_name.ilike(search_term))
                | (Invoice.invoice_number.ilike(search_term))
                | (Document.original_filename.ilike(search_term))
            )

        if category:
            query = query.filter(Invoice.expense_category == category)
        if currency:
            query = query.filter(Invoice.currency == currency)
        if review_status:
            query = query.filter(Invoice.review_status == review_status)
        if date_from:
            query = query.filter(Invoice.invoice_date >= date_from)
        if date_to:
            query = query.filter(Invoice.invoice_date <= date_to)

    # Sorting
    if sort_by == "date" and hasattr(Invoice, "invoice_date"):
        query = query.outerjoin(Invoice) if not any([search, category, currency]) else query
        order_col = Invoice.invoice_date
    elif sort_by == "amount":
        query = query.outerjoin(Invoice) if not any([search, category, currency]) else query
        order_col = Invoice.total_amount
    else:
        order_col = Document.upload_time

    if sort_order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())

    docs = query.offset(offset).limit(limit).all()

    # Map to list response
    results = []
    for doc in docs:
        inv = doc.invoice
        results.append(
            DocumentListResponse(
                id=doc.id,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                status=doc.status,
                upload_time=doc.upload_time,
                vendor_name=inv.vendor_name if inv else None,
                total_amount=inv.total_amount if inv else None,
                currency=inv.currency if inv else None,
                expense_category=inv.expense_category if inv else None,
                review_status=inv.review_status if inv else None,
            )
        )
    return results


@app.get("/api/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get a single document with its extracted invoice data."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/api/documents/{document_id}/process", response_model=dict)
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Manually trigger processing for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed")

    background_tasks.add_task(_process_document, document_id)
    return {"message": "Processing started", "document_id": document_id}


@app.post("/api/documents/{document_id}/retry", response_model=dict)
async def retry_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Retry processing for a failed document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up previous extraction
    if doc.invoice:
        db.delete(doc.invoice)

    doc.status = "uploaded"
    doc.error_message = None
    doc.processed_time = None
    db.commit()

    background_tasks.add_task(_process_document, document_id)
    return {"message": "Retry started", "document_id": document_id}


@app.patch("/api/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    update: InvoiceUpdate,
    db: Session = Depends(get_db),
):
    """Update extracted invoice data (user corrections)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.invoice:
        raise HTTPException(status_code=400, detail="No invoice data to update")

    invoice = doc.invoice
    update_data = update.model_dump(exclude_unset=True)

    # Handle line items separately
    new_line_items = update_data.pop("line_items", None)

    # Update invoice fields
    for field, value in update_data.items():
        if hasattr(invoice, field):
            setattr(invoice, field, value)

    invoice.user_edited = True
    invoice.updated_at = datetime.now(timezone.utc)

    # Replace line items if provided
    if new_line_items is not None:
        # Delete existing
        db.query(LineItem).filter(LineItem.invoice_id == invoice.id).delete()

        # Create new
        for item_data in new_line_items:
            line = LineItem(
                invoice_id=invoice.id,
                description=item_data.get("description"),
                quantity=item_data.get("quantity"),
                unit_price=item_data.get("unit_price"),
                tax_amount=item_data.get("tax_amount"),
                line_total=item_data.get("line_total"),
            )
            db.add(line)

    db.commit()
    db.refresh(doc)

    logger.info("Document %s updated by user", document_id)
    return doc


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and its associated data + file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete stored file
    file_path = os.path.join(settings.upload_dir, doc.stored_filename)
    real_upload_dir = os.path.realpath(settings.upload_dir)
    real_file_path = os.path.realpath(file_path)
    if real_file_path.startswith(real_upload_dir) and os.path.exists(real_file_path):
        os.remove(real_file_path)

    # Cascade delete handles invoice + line items + processing jobs
    db.delete(doc)
    db.commit()

    logger.info("Document %s deleted", document_id)
    return {"message": "Document deleted"}


# ──────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────


@app.get("/api/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics from actual database records."""
    total = db.query(func.count(Document.id)).scalar() or 0
    processed = (
        db.query(func.count(Document.id))
        .filter(Document.status == "completed")
        .scalar()
        or 0
    )
    review = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.review_status.in_(["pending", "flagged"]))
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(Document.id))
        .filter(Document.status == "failed")
        .scalar()
        or 0
    )

    # Currency summaries (grouped by currency — never mix currencies)
    currency_rows = (
        db.query(
            Invoice.currency,
            func.sum(Invoice.total_amount).label("total"),
            func.sum(
                case((Invoice.outstanding_amount.isnot(None), Invoice.outstanding_amount), else_=0)
            ).label("outstanding"),
            func.count(Invoice.id).label("cnt"),
        )
        .group_by(Invoice.currency)
        .all()
    )
    currency_summaries = [
        CurrencySummary(
            currency=row.currency or "USD",
            total_amount=round(row.total or 0, 2),
            outstanding_amount=round(row.outstanding or 0, 2),
            count=row.cnt,
        )
        for row in currency_rows
    ]

    # Category breakdown (grouped by category + currency)
    cat_rows = (
        db.query(
            Invoice.expense_category,
            Invoice.currency,
            func.sum(Invoice.total_amount).label("total"),
            func.count(Invoice.id).label("cnt"),
        )
        .group_by(Invoice.expense_category, Invoice.currency)
        .all()
    )
    category_breakdown = [
        CategoryBreakdown(
            category=row.expense_category or "Uncategorized",
            total=round(row.total or 0, 2),
            count=row.cnt,
            currency=row.currency or "USD",
        )
        for row in cat_rows
    ]

    # Monthly trend (by currency)
    monthly_rows = (
        db.query(
            func.substr(Invoice.invoice_date, 1, 7).label("month"),
            Invoice.currency,
            func.sum(Invoice.total_amount).label("total"),
            func.count(Invoice.id).label("cnt"),
        )
        .filter(Invoice.invoice_date.isnot(None))
        .group_by("month", Invoice.currency)
        .order_by("month")
        .all()
    )
    monthly_trend = [
        MonthlyTrend(
            month=row.month or "Unknown",
            total=round(row.total or 0, 2),
            count=row.cnt,
            currency=row.currency or "USD",
        )
        for row in monthly_rows
    ]

    # Recent documents
    recent_docs = (
        db.query(Document)
        .order_by(desc(Document.upload_time))
        .limit(10)
        .all()
    )
    recent = [
        DocumentListResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            upload_time=doc.upload_time,
            vendor_name=doc.invoice.vendor_name if doc.invoice else None,
            total_amount=doc.invoice.total_amount if doc.invoice else None,
            currency=doc.invoice.currency if doc.invoice else None,
            expense_category=doc.invoice.expense_category if doc.invoice else None,
            review_status=doc.invoice.review_status if doc.invoice else None,
        )
        for doc in recent_docs
    ]

    return DashboardSummary(
        total_documents=total,
        processed_count=processed,
        review_count=review,
        failed_count=failed,
        currency_summaries=currency_summaries,
        category_breakdown=category_breakdown,
        monthly_trend=monthly_trend,
        recent_documents=recent,
    )


# ──────────────────────────────────────────
# Expense Reports
# ──────────────────────────────────────────


@app.get("/api/reports/expenses")
def expense_report(
    category: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get expense report data grouped by category and currency."""
    query = db.query(Invoice)

    if category:
        query = query.filter(Invoice.expense_category == category)
    if currency:
        query = query.filter(Invoice.currency == currency)
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)

    invoices = query.all()

    # Group by category and currency
    groups = {}
    for inv in invoices:
        key = (inv.expense_category or "Uncategorized", inv.currency or "USD")
        if key not in groups:
            groups[key] = {"category": key[0], "currency": key[1], "total": 0.0, "count": 0, "invoices": []}
        groups[key]["total"] += inv.total_amount or 0
        groups[key]["count"] += 1
        groups[key]["invoices"].append({
            "id": inv.id,
            "vendor_name": inv.vendor_name,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "total_amount": inv.total_amount,
        })

    return {
        "groups": list(groups.values()),
        "total_invoices": len(invoices),
    }


# ──────────────────────────────────────────
# Exports
# ──────────────────────────────────────────


@app.get("/api/exports/csv")
def export_csv(
    invoice_ids: Optional[str] = Query(None, description="Comma-separated invoice IDs"),
    category: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export invoices as CSV."""
    invoices = _get_filtered_invoices(db, invoice_ids, category, currency, date_from, date_to, review_status)

    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices match the filter criteria")

    buffer = export_service.export_csv(invoices)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoicepilot_export.csv"},
    )


@app.get("/api/exports/xlsx")
def export_xlsx(
    invoice_ids: Optional[str] = Query(None, description="Comma-separated invoice IDs"),
    category: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export invoices as XLSX with formatting and summary."""
    invoices = _get_filtered_invoices(db, invoice_ids, category, currency, date_from, date_to, review_status)

    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices match the filter criteria")

    buffer = export_service.export_xlsx(invoices)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=invoicepilot_export.xlsx"},
    )


def _get_filtered_invoices(
    db: Session,
    invoice_ids: Optional[str],
    category: Optional[str],
    currency: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    review_status: Optional[str],
) -> list[Invoice]:
    """Build filtered invoice query."""
    query = db.query(Invoice)

    if invoice_ids:
        ids = [i.strip() for i in invoice_ids.split(",") if i.strip()]
        query = query.filter(Invoice.id.in_(ids))
    if category:
        query = query.filter(Invoice.expense_category == category)
    if currency:
        query = query.filter(Invoice.currency == currency)
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)
    if review_status:
        query = query.filter(Invoice.review_status == review_status)

    return query.all()
