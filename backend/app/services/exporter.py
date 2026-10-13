"""InvoicePilot AI — CSV and Excel export service.

Exports invoice data with formula injection protection, proper formatting,
and optional summary sheets.
"""

import csv
import io
import logging
import re
from typing import Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill, numbers
from openpyxl.utils.dataframe import dataframe_to_rows
from sqlalchemy.orm import Session

from app.models import Invoice, LineItem

logger = logging.getLogger(__name__)

# Characters that trigger formula interpretation in spreadsheets
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def _sanitize_cell(value) -> str:
    """Protect against CSV/formula injection from untrusted data."""
    if value is None:
        return ""
    s = str(value)
    if s and s[0] in FORMULA_PREFIXES:
        return "'" + s  # Prefix with single quote
    return s


def _invoices_to_dataframe(invoices: list[Invoice]) -> pd.DataFrame:
    """Convert invoice records to a sanitized DataFrame."""
    rows = []
    for inv in invoices:
        rows.append({
            "Vendor Name": _sanitize_cell(inv.vendor_name),
            "Invoice Number": _sanitize_cell(inv.invoice_number),
            "Invoice Date": _sanitize_cell(inv.invoice_date),
            "Due Date": _sanitize_cell(inv.due_date),
            "Currency": _sanitize_cell(inv.currency),
            "Subtotal": inv.subtotal,
            "Tax Amount": inv.tax_amount,
            "Discount": inv.discount,
            "Total Amount": inv.total_amount,
            "Amount Paid": inv.amount_paid,
            "Outstanding Amount": inv.outstanding_amount,
            "Payment Status": _sanitize_cell(inv.payment_status),
            "Category": _sanitize_cell(inv.expense_category),
            "Document Type": _sanitize_cell(inv.document_type),
            "Review Status": _sanitize_cell(inv.review_status),
        })
    return pd.DataFrame(rows)


class ExportService:
    """Export invoice data to CSV and Excel formats."""

    def export_csv(self, invoices: list[Invoice]) -> io.BytesIO:
        """Generate CSV export as BytesIO buffer."""
        df = _invoices_to_dataframe(invoices)
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")  # BOM for Excel compat
        buffer.seek(0)
        return buffer

    def export_xlsx(self, invoices: list[Invoice]) -> io.BytesIO:
        """Generate XLSX export with formatting and summary sheet."""
        df = _invoices_to_dataframe(invoices)

        buffer = io.BytesIO()
        wb = Workbook()

        # ── Invoices sheet ──
        ws = wb.active
        ws.title = "Invoices"

        # Header style
        header_font = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Write headers
        for col_idx, col_name in enumerate(df.columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # Write data
        money_cols = {"Subtotal", "Tax Amount", "Discount", "Total Amount",
                      "Amount Paid", "Outstanding Amount"}

        for row_idx, row in enumerate(df.itertuples(index=False), 2):
            for col_idx, (col_name, value) in enumerate(zip(df.columns, row), 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border

                if col_name in money_cols and isinstance(value, (int, float)):
                    cell.number_format = '#,##0.00'

        # Auto-width columns
        for col_idx, col_name in enumerate(df.columns, 1):
            max_length = max(
                len(str(col_name)),
                *(len(str(df.iloc[r, col_idx - 1])) for r in range(len(df)))
                if len(df) > 0 else [10],
            )
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = (
                min(max_length + 3, 40)
            )

        # Freeze header row
        ws.freeze_panes = "A2"

        # ── Summary sheet ──
        ws_summary = wb.create_sheet("Summary")

        ws_summary.cell(row=1, column=1, value="InvoicePilot AI — Export Summary").font = (
            Font(name="Calibri", bold=True, size=14)
        )
        ws_summary.cell(row=3, column=1, value="Total Invoices").font = Font(bold=True)
        ws_summary.cell(row=3, column=2, value=len(invoices))

        # Group by currency for totals
        row_offset = 5
        ws_summary.cell(row=row_offset, column=1, value="Totals by Currency").font = (
            Font(bold=True, size=12)
        )
        row_offset += 1

        currency_groups = df.groupby("Currency").agg(
            Count=("Total Amount", "count"),
            Total=("Total Amount", "sum"),
        ).reset_index()

        ws_summary.cell(row=row_offset, column=1, value="Currency").font = Font(bold=True)
        ws_summary.cell(row=row_offset, column=2, value="Count").font = Font(bold=True)
        ws_summary.cell(row=row_offset, column=3, value="Total").font = Font(bold=True)
        row_offset += 1

        for _, crow in currency_groups.iterrows():
            ws_summary.cell(row=row_offset, column=1, value=crow["Currency"])
            ws_summary.cell(row=row_offset, column=2, value=crow["Count"])
            total_cell = ws_summary.cell(row=row_offset, column=3, value=crow["Total"])
            total_cell.number_format = '#,##0.00'
            row_offset += 1

        # Category breakdown
        row_offset += 1
        ws_summary.cell(row=row_offset, column=1, value="By Category").font = (
            Font(bold=True, size=12)
        )
        row_offset += 1

        cat_groups = df.groupby(["Category", "Currency"]).agg(
            Count=("Total Amount", "count"),
            Total=("Total Amount", "sum"),
        ).reset_index()

        ws_summary.cell(row=row_offset, column=1, value="Category").font = Font(bold=True)
        ws_summary.cell(row=row_offset, column=2, value="Currency").font = Font(bold=True)
        ws_summary.cell(row=row_offset, column=3, value="Count").font = Font(bold=True)
        ws_summary.cell(row=row_offset, column=4, value="Total").font = Font(bold=True)
        row_offset += 1

        for _, crow in cat_groups.iterrows():
            ws_summary.cell(row=row_offset, column=1, value=crow["Category"])
            ws_summary.cell(row=row_offset, column=2, value=crow["Currency"])
            ws_summary.cell(row=row_offset, column=3, value=crow["Count"])
            total_cell = ws_summary.cell(row=row_offset, column=4, value=crow["Total"])
            total_cell.number_format = '#,##0.00'
            row_offset += 1

        # Auto-width summary columns
        for col_idx in range(1, 5):
            ws_summary.column_dimensions[
                ws_summary.cell(row=1, column=col_idx).column_letter
            ].width = 20

        wb.save(buffer)
        buffer.seek(0)
        return buffer


# Module-level singleton
export_service = ExportService()
