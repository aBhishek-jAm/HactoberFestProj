"""InvoicePilot AI — Invoice validation service.

Performs deterministic arithmetic checks, duplicate detection,
date validation, and field consistency verification.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Invoice
from app.schemas import AIExtractionResult

logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a single validation finding."""

    def __init__(self, field: str, severity: str, message: str):
        self.field = field
        self.severity = severity  # "error" | "warning" | "info"
        self.message = message

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "severity": self.severity,
            "message": self.message,
        }


class InvoiceValidator:
    """Validate extracted invoice data with deterministic checks."""

    def __init__(self, tolerance: float = None):
        self.tolerance = tolerance or settings.arithmetic_tolerance

    def validate(
        self, data: AIExtractionResult, db: Optional[Session] = None
    ) -> tuple[list[dict], float]:
        """
        Run all validations on extracted data.

        Returns:
            - List of validation issue dicts
            - Confidence score (0.0 - 1.0)
        """
        issues: list[ValidationIssue] = []

        # Core field checks
        issues.extend(self._check_required_fields(data))
        issues.extend(self._check_arithmetic(data))
        issues.extend(self._check_dates(data))
        issues.extend(self._check_currency(data))
        issues.extend(self._check_line_items(data))
        issues.extend(self._check_payment_consistency(data))

        # Duplicate check (needs DB)
        if db is not None:
            issues.extend(self._check_duplicates(data, db))

        confidence = self._calculate_confidence(data, issues)

        return [i.to_dict() for i in issues], confidence

    def _check_required_fields(self, data: AIExtractionResult) -> list[ValidationIssue]:
        """Check for missing important fields."""
        issues = []

        if not data.vendor_name:
            issues.append(
                ValidationIssue("vendor_name", "warning", "Vendor name is missing")
            )
        if not data.total_amount and data.total_amount != 0:
            issues.append(
                ValidationIssue("total_amount", "warning", "Total amount is missing")
            )
        if not data.invoice_date:
            issues.append(
                ValidationIssue("invoice_date", "warning", "Invoice date is missing")
            )
        if not data.currency:
            issues.append(
                ValidationIssue("currency", "info", "Currency not specified, defaulting to USD")
            )

        return issues

    def _check_arithmetic(self, data: AIExtractionResult) -> list[ValidationIssue]:
        """Verify subtotal + tax - discount ≈ total."""
        issues = []

        subtotal = data.subtotal
        tax = data.tax_amount or 0.0
        discount = data.discount or 0.0
        total = data.total_amount

        if subtotal is not None and total is not None:
            expected = subtotal + tax - discount
            diff = abs(expected - total)

            if diff > 0 and diff > abs(total * self.tolerance) and diff > 0.01:
                issues.append(
                    ValidationIssue(
                        "total_amount",
                        "warning",
                        f"Arithmetic mismatch: subtotal({subtotal}) + tax({tax}) "
                        f"- discount({discount}) = {expected:.2f}, "
                        f"but total is {total:.2f} (diff: {diff:.2f})",
                    )
                )

        # Check line items sum vs subtotal
        if data.line_items:
            line_sum = sum(
                item.line_total for item in data.line_items if item.line_total is not None
            )
            if line_sum > 0 and subtotal is not None:
                diff = abs(line_sum - subtotal)
                if diff > abs(subtotal * self.tolerance) and diff > 0.01:
                    issues.append(
                        ValidationIssue(
                            "line_items",
                            "info",
                            f"Line items sum ({line_sum:.2f}) differs from "
                            f"subtotal ({subtotal:.2f})",
                        )
                    )

        return issues

    def _check_dates(self, data: AIExtractionResult) -> list[ValidationIssue]:
        """Validate date formats and logic."""
        issues = []

        invoice_dt = self._parse_date(data.invoice_date)
        due_dt = self._parse_date(data.due_date)

        if data.invoice_date and invoice_dt is None:
            issues.append(
                ValidationIssue(
                    "invoice_date", "warning", f"Invalid date format: {data.invoice_date}"
                )
            )

        if data.due_date and due_dt is None:
            issues.append(
                ValidationIssue(
                    "due_date", "warning", f"Invalid date format: {data.due_date}"
                )
            )

        if invoice_dt and due_dt and due_dt < invoice_dt:
            issues.append(
                ValidationIssue(
                    "due_date", "warning", "Due date is before invoice date"
                )
            )

        # Flag very old or future dates
        if invoice_dt:
            now = datetime.now()
            if invoice_dt.year < 2000:
                issues.append(
                    ValidationIssue(
                        "invoice_date", "warning", f"Invoice date seems too old: {data.invoice_date}"
                    )
                )
            if invoice_dt > now:
                issues.append(
                    ValidationIssue(
                        "invoice_date", "info", "Invoice date is in the future"
                    )
                )

        return issues

    def _check_currency(self, data: AIExtractionResult) -> list[ValidationIssue]:
        """Basic currency code validation."""
        issues = []

        if data.currency:
            if len(data.currency) != 3 or not data.currency.isalpha():
                issues.append(
                    ValidationIssue(
                        "currency",
                        "warning",
                        f"Invalid currency code: {data.currency}",
                    )
                )

        return issues

    def _check_line_items(self, data: AIExtractionResult) -> list[ValidationIssue]:
        """Validate individual line items."""
        issues = []

        if not data.line_items:
            return issues

        for i, item in enumerate(data.line_items):
            # Check line total consistency
            if (
                item.quantity is not None
                and item.unit_price is not None
                and item.line_total is not None
            ):
                expected = item.quantity * item.unit_price
                if item.tax_amount:
                    expected += item.tax_amount
                diff = abs(expected - item.line_total)
                if diff > 0.01 and diff > abs(item.line_total * self.tolerance):
                    issues.append(
                        ValidationIssue(
                            f"line_items[{i}]",
                            "info",
                            f"Line item {i + 1} total mismatch: "
                            f"qty({item.quantity}) × price({item.unit_price}) "
                            f"= {expected:.2f}, got {item.line_total:.2f}",
                        )
                    )

        return issues

    def _check_payment_consistency(
        self, data: AIExtractionResult
    ) -> list[ValidationIssue]:
        """Check payment-related field consistency."""
        issues = []

        if data.payment_status == "paid" and data.outstanding_amount:
            if data.outstanding_amount > 0:
                issues.append(
                    ValidationIssue(
                        "payment_status",
                        "warning",
                        f"Status is 'paid' but outstanding amount is {data.outstanding_amount}",
                    )
                )

        if data.amount_paid is not None and data.total_amount is not None:
            if data.amount_paid > data.total_amount * 1.01:  # 1% tolerance
                issues.append(
                    ValidationIssue(
                        "amount_paid",
                        "warning",
                        f"Amount paid ({data.amount_paid}) exceeds total ({data.total_amount})",
                    )
                )

        return issues

    def _check_duplicates(
        self, data: AIExtractionResult, db: Session
    ) -> list[ValidationIssue]:
        """Check for potential duplicate invoices."""
        issues = []

        if data.invoice_number and data.vendor_name:
            existing = (
                db.query(Invoice)
                .filter(
                    Invoice.invoice_number == data.invoice_number,
                    Invoice.vendor_name == data.vendor_name,
                )
                .first()
            )
            if existing:
                issues.append(
                    ValidationIssue(
                        "invoice_number",
                        "warning",
                        f"Potential duplicate: invoice {data.invoice_number} "
                        f"from {data.vendor_name} already exists",
                    )
                )

        return issues

    def _calculate_confidence(
        self, data: AIExtractionResult, issues: list[ValidationIssue]
    ) -> float:
        """Calculate extraction confidence score."""
        score = 1.0

        # Deduct for missing fields
        critical_fields = [data.vendor_name, data.total_amount, data.invoice_date]
        missing_critical = sum(1 for f in critical_fields if f is None)
        score -= missing_critical * 0.15

        # Deduct for validation issues
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        score -= error_count * 0.2
        score -= warning_count * 0.05

        # Bonus for complete data
        optional_fields = [
            data.invoice_number, data.currency, data.subtotal,
            data.tax_amount, data.expense_category,
        ]
        present_optional = sum(1 for f in optional_fields if f is not None)
        score += present_optional * 0.02

        return max(0.0, min(1.0, round(score, 2)))

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Try parsing common date formats."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None


# Module-level singleton
invoice_validator = InvoiceValidator()
