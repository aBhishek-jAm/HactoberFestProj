"""InvoicePilot AI — SQLAlchemy ORM models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """Uploaded file metadata and processing state."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=_uuid)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(10), nullable=False)  # pdf, png, jpg, jpeg
    file_size = Column(Integer, nullable=False)  # bytes
    file_hash = Column(String(64), nullable=True)  # SHA-256 for dedup
    status = Column(
        String(20),
        nullable=False,
        default="uploaded",
        # uploaded | processing | completed | failed | requires_review
    )
    error_message = Column(Text, nullable=True)
    upload_time = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    processed_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    invoice = relationship(
        "Invoice", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    processing_jobs = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_upload_time", "upload_time"),
        Index("ix_documents_file_hash", "file_hash"),
    )


class Invoice(Base):
    """Extracted invoice data from a processed document."""

    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Core fields
    vendor_name = Column(String(255), nullable=True)
    vendor_address = Column(Text, nullable=True)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(String(20), nullable=True)  # stored as ISO string
    due_date = Column(String(20), nullable=True)
    currency = Column(String(10), nullable=True, default="USD")

    # Financial
    subtotal = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    discount = Column(Float, nullable=True, default=0.0)
    total_amount = Column(Float, nullable=True)
    amount_paid = Column(Float, nullable=True)
    outstanding_amount = Column(Float, nullable=True)

    # Classification
    payment_status = Column(String(20), nullable=True)  # paid | unpaid | partial | null
    expense_category = Column(String(50), nullable=True)
    document_type = Column(String(20), nullable=True, default="invoice")  # invoice | receipt | other

    # Quality
    confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    review_status = Column(
        String(20), nullable=False, default="pending"
        # pending | reviewed | flagged
    )
    validation_notes = Column(Text, nullable=True)  # JSON array of issues

    # Raw AI output for debugging (never expose in API)
    raw_extracted_json = Column(Text, nullable=True)

    # User corrections tracking
    user_edited = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    document = relationship("Document", back_populates="invoice")
    line_items = relationship(
        "LineItem", back_populates="invoice", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_invoices_vendor_name", "vendor_name"),
        Index("ix_invoices_invoice_date", "invoice_date"),
        Index("ix_invoices_expense_category", "expense_category"),
        Index("ix_invoices_review_status", "review_status"),
        Index("ix_invoices_currency", "currency"),
    )


class LineItem(Base):
    """Individual line items extracted from an invoice."""

    __tablename__ = "line_items"

    id = Column(String(36), primary_key=True, default=_uuid)
    invoice_id = Column(
        String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )

    description = Column(Text, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    line_total = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationship
    invoice = relationship("Invoice", back_populates="line_items")


class ProcessingJob(Base):
    """Tracks processing attempts for a document."""

    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    status = Column(
        String(20), nullable=False, default="queued"
        # queued | running | completed | failed
    )
    step = Column(String(50), nullable=True)  # current processing step
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationship
    document = relationship("Document", back_populates="processing_jobs")

    __table_args__ = (Index("ix_processing_jobs_status", "status"),)
