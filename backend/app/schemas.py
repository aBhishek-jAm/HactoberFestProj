"""InvoicePilot AI — Pydantic schemas for API request/response validation."""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ──────────────────────────────────────────
# Line Items
# ──────────────────────────────────────────

class LineItemBase(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_amount: Optional[float] = None
    line_total: Optional[float] = None


class LineItemCreate(LineItemBase):
    pass


class LineItemResponse(LineItemBase):
    id: str

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Invoices
# ──────────────────────────────────────────

class InvoiceBase(BaseModel):
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = "USD"
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = 0.0
    total_amount: Optional[float] = None
    amount_paid: Optional[float] = None
    outstanding_amount: Optional[float] = None
    payment_status: Optional[str] = None
    expense_category: Optional[str] = None
    document_type: Optional[str] = "invoice"


class InvoiceUpdate(InvoiceBase):
    """Used for PATCH updates — all fields optional."""
    review_status: Optional[str] = None
    line_items: Optional[list[LineItemCreate]] = None


class InvoiceResponse(InvoiceBase):
    id: str
    document_id: str
    confidence: Optional[float] = None
    review_status: str = "pending"
    validation_notes: Optional[str] = None
    user_edited: bool = False
    line_items: list[LineItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Documents
# ──────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    upload_time: datetime
    processed_time: Optional[datetime] = None
    invoice: Optional[InvoiceResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    upload_time: datetime
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    expense_category: Optional[str] = None
    review_status: Optional[str] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────

class CurrencySummary(BaseModel):
    currency: str
    total_amount: float
    outstanding_amount: float
    count: int


class CategoryBreakdown(BaseModel):
    category: str
    total: float
    count: int
    currency: str


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    total: float
    count: int
    currency: str


class DashboardSummary(BaseModel):
    total_documents: int = 0
    processed_count: int = 0
    review_count: int = 0
    failed_count: int = 0
    currency_summaries: list[CurrencySummary] = []
    category_breakdown: list[CategoryBreakdown] = []
    monthly_trend: list[MonthlyTrend] = []
    recent_documents: list[DocumentListResponse] = []


# ──────────────────────────────────────────
# AI Extraction Schema (what Gemma should return)
# ──────────────────────────────────────────

class AILineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_amount: Optional[float] = None
    line_total: Optional[float] = None


class AIExtractionResult(BaseModel):
    """Schema for validating Gemma's JSON output."""
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount: Optional[float] = None
    total_amount: Optional[float] = None
    amount_paid: Optional[float] = None
    outstanding_amount: Optional[float] = None
    payment_status: Optional[str] = None
    expense_category: Optional[str] = None
    document_type: Optional[str] = None
    line_items: Optional[list[AILineItem]] = None

    @field_validator("total_amount", "subtotal", "tax_amount", "discount",
                     "amount_paid", "outstanding_amount", mode="before")
    @classmethod
    def reject_negative_amounts(cls, v):
        if v is not None and isinstance(v, (int, float)) and v < 0:
            return None  # Reject negative values silently
        return v

    @field_validator("payment_status", mode="before")
    @classmethod
    def normalize_payment_status(cls, v):
        if v is None:
            return None
        v_lower = str(v).strip().lower()
        valid = {"paid", "unpaid", "partial"}
        return v_lower if v_lower in valid else None

    @field_validator("document_type", mode="before")
    @classmethod
    def normalize_document_type(cls, v):
        if v is None:
            return "invoice"
        v_lower = str(v).strip().lower()
        valid = {"invoice", "receipt", "credit_note", "other"}
        return v_lower if v_lower in valid else "other"


# ──────────────────────────────────────────
# Health
# ──────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "0.1.0"


class AIHealthResponse(BaseModel):
    status: str  # connected | disconnected | demo_mode
    model: str
    ollama_url: str
    message: Optional[str] = None


# ──────────────────────────────────────────
# Errors
# ──────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# ──────────────────────────────────────────
# Exports
# ──────────────────────────────────────────

class ExportRequest(BaseModel):
    invoice_ids: Optional[list[str]] = None
    category: Optional[str] = None
    currency: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    review_status: Optional[str] = None
