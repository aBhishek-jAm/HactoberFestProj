"""InvoicePilot AI — AI extraction service using Ollama + Gemma.

Sends extracted document text to a local Gemma model and parses
structured invoice data from the response. Falls back to intelligent
regex-based heuristic extraction when Ollama is unavailable.
"""

import json
import logging
import re
from typing import Optional

import httpx

from app.config import settings
from app.schemas import AIExtractionResult, AILineItem

logger = logging.getLogger(__name__)

# Expense categories for the prompt
EXPENSE_CATEGORIES = [
    "Office Supplies",
    "Software & Subscriptions",
    "Travel",
    "Food & Meals",
    "Utilities",
    "Marketing",
    "Professional Services",
    "Equipment",
    "Rent",
    "Insurance",
    "Other",
]

EXTRACTION_PROMPT = """You are an invoice data extraction assistant. Extract structured data from the following document text.

Return ONLY a valid JSON object with these fields (use null for unknown values, do not invent data):

{{
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "currency": "3-letter ISO code or null",
  "subtotal": number or null,
  "tax_amount": number or null,
  "discount": number or null,
  "total_amount": number or null,
  "amount_paid": number or null,
  "outstanding_amount": number or null,
  "payment_status": "paid" or "unpaid" or "partial" or null,
  "expense_category": one of {categories} or null,
  "document_type": "invoice" or "receipt" or "credit_note" or "other",
  "line_items": [
    {{
      "description": "string",
      "quantity": number or null,
      "unit_price": number or null,
      "tax_amount": number or null,
      "line_total": number or null
    }}
  ]
}}

Rules:
- Return ONLY the JSON object. No markdown, no explanation, no code fences.
- Use null for any field you cannot determine from the text.
- Dates must be in YYYY-MM-DD format.
- All monetary values must be numbers, not strings.
- Do not guess or fabricate values.

Document text:
---
{document_text}
---"""


class AIExtractor:
    """Extracts structured invoice data using Ollama + Gemma with regex fallback."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.max_retries = settings.max_retries
        self.context_length = settings.ollama_context_length

    async def check_connection(self) -> dict:
        """Check if Ollama is reachable and the model is available."""
        if settings.demo_mode:
            return {
                "status": "demo_mode",
                "model": self.model,
                "ollama_url": self.base_url,
                "message": "Running in demo mode. AI extraction is simulated.",
            }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check Ollama is running
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return {
                        "status": "disconnected",
                        "model": self.model,
                        "ollama_url": self.base_url,
                        "message": "Ollama is not responding. Heuristic extraction will be used.",
                    }

                # Check if model is available
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check both exact match and prefix match
                model_available = any(
                    self.model in name or name.startswith(self.model.split(":")[0])
                    for name in model_names
                )

                if model_available:
                    return {
                        "status": "connected",
                        "model": self.model,
                        "ollama_url": self.base_url,
                        "message": f"Model '{self.model}' is available.",
                    }
                else:
                    # Try to auto-detect any available model
                    if model_names:
                        available_str = ", ".join(model_names)
                        return {
                            "status": "fallback",
                            "model": self.model,
                            "ollama_url": self.base_url,
                            "message": (
                                f"Model '{self.model}' not found. "
                                f"Available: {available_str}. "
                                f"Will use heuristic extraction. "
                                f"Run: ollama pull {self.model}"
                            ),
                        }
                    return {
                        "status": "disconnected",
                        "model": self.model,
                        "ollama_url": self.base_url,
                        "message": (
                            f"No models found. Run: ollama pull {self.model}"
                        ),
                    }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "model": self.model,
                "ollama_url": self.base_url,
                "message": "Cannot connect to Ollama. Heuristic extraction will be used.",
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "model": self.model,
                "ollama_url": self.base_url,
                "message": f"Health check failed: {type(e).__name__}. Heuristic extraction will be used.",
            }

    async def _find_working_model(self) -> Optional[str]:
        """Try to find any available model in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return None
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Prefer the configured model
                for name in model_names:
                    if self.model in name or name.startswith(self.model.split(":")[0]):
                        return name

                # Fall back to any gemma model
                for name in model_names:
                    if "gemma" in name.lower():
                        return name

                # Fall back to any available model
                if model_names:
                    return model_names[0]
        except Exception:
            pass
        return None

    async def extract(self, document_text: str) -> AIExtractionResult:
        """
        Send document text to Gemma and parse the structured extraction result.
        Falls back to heuristic regex extraction if Ollama is unavailable.
        """
        if settings.demo_mode:
            return self._heuristic_extraction(document_text)

        # Try AI extraction first
        try:
            # Find a working model (may differ from config)
            working_model = await self._find_working_model()

            if working_model:
                logger.info("Using Ollama model: %s", working_model)
                truncated = self._truncate_text(document_text)
                prompt = EXTRACTION_PROMPT.format(
                    document_text=truncated,
                    categories=", ".join(EXPENSE_CATEGORIES),
                )

                last_error: Optional[Exception] = None
                for attempt in range(1, self.max_retries + 1):
                    try:
                        raw_response = await self._call_ollama(prompt, working_model)
                        result = self._parse_response(raw_response)
                        logger.info("AI extraction succeeded on attempt %d", attempt)
                        return result
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(
                            "AI extraction attempt %d/%d failed: %s",
                            attempt, self.max_retries, str(e)
                        )
                        last_error = e

                logger.warning(
                    "AI extraction failed after %d attempts, falling back to heuristic: %s",
                    self.max_retries, last_error,
                )
            else:
                logger.info("No Ollama model available, using heuristic extraction")

        except httpx.ConnectError:
            logger.info("Cannot connect to Ollama, using heuristic extraction")
        except httpx.HTTPStatusError as e:
            logger.warning("Ollama HTTP error %s, using heuristic extraction", e.response.status_code)
        except Exception as e:
            logger.warning("Ollama error (%s): %s, using heuristic extraction", type(e).__name__, str(e)[:100])

        # Fallback to regex-based heuristic extraction
        return self._heuristic_extraction(document_text)

    async def _call_ollama(self, prompt: str, model: Optional[str] = None) -> str:
        """Call Ollama generate API and return the response text."""
        use_model = model or self.model
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": use_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",  # Force JSON output for faster, structured responses
                "options": {
                    "num_ctx": self.context_length,
                    "num_predict": settings.ollama_num_predict,
                    "temperature": 0.1,  # Low temp for structured extraction
                },
            }
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")


    def _parse_response(self, raw: str) -> AIExtractionResult:
        """Parse raw model output into validated AIExtractionResult."""
        # Strip markdown code fences if model included them
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Find JSON object boundaries
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise json.JSONDecodeError("No JSON object found", cleaned, 0)

        json_str = cleaned[start : end + 1]
        data = json.loads(json_str)

        if not isinstance(data, dict):
            raise ValueError("Expected JSON object, got " + type(data).__name__)

        return AIExtractionResult.model_validate(data)

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within estimated token limit."""
        # Rough estimate: 1 token ≈ 4 characters.
        # Reserve ~1500 tokens for prompt template + response
        max_chars = (self.context_length - 1500) * 4
        if len(text) > max_chars:
            logger.info(
                "Truncating document text from %d to %d chars", len(text), max_chars
            )
            return text[:max_chars] + "\n[...truncated...]"
        return text

    # ──────────────────────────────────────────
    # Heuristic / Regex-Based Fallback Extractor
    # ──────────────────────────────────────────

    def _heuristic_extraction(self, text: str) -> AIExtractionResult:
        """
        Intelligent regex-based extraction when Ollama is unavailable.
        Parses vendor info, invoice numbers, dates, monetary amounts,
        and line items directly from the document text.
        """
        logger.info("Running heuristic extraction on %d chars of text", len(text))

        vendor_name = self._extract_vendor_name(text)
        vendor_address = self._extract_vendor_address(text)
        invoice_number = self._extract_invoice_number(text)
        invoice_date = self._extract_date(text, ["invoice date", "date", "issued", "invoice dt"])
        due_date = self._extract_date(text, ["due date", "due", "payment due", "due dt"])
        currency = self._extract_currency(text)
        amounts = self._extract_amounts(text)
        payment_status = self._extract_payment_status(text)
        doc_type = self._extract_document_type(text)
        line_items = self._extract_line_items(text)
        category = self._categorize_expense(text, vendor_name)

        return AIExtractionResult(
            vendor_name=vendor_name,
            vendor_address=vendor_address,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            currency=currency,
            subtotal=amounts.get("subtotal"),
            tax_amount=amounts.get("tax"),
            discount=amounts.get("discount"),
            total_amount=amounts.get("total"),
            amount_paid=amounts.get("paid"),
            outstanding_amount=amounts.get("outstanding"),
            payment_status=payment_status,
            expense_category=category,
            document_type=doc_type,
            line_items=line_items if line_items else None,
        )

    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """Extract vendor/company name from document."""
        lines = text.strip().split("\n")
        # Skip header keywords, look for first substantial line
        skip = {"invoice", "receipt", "tax invoice", "bill", "credit note",
                "statement", "purchase order", "from:", "bill to:", "to:"}

        # Try "From:" pattern first
        for line in lines:
            clean = line.strip()
            lower = clean.lower()
            if lower.startswith("from:") or lower.startswith("supplier:") or lower.startswith("vendor:"):
                name = clean.split(":", 1)[1].strip()
                if name and len(name) > 2:
                    return name

        # Look for company-like names (LLC, Inc, Ltd, Corp, etc.)
        company_re = re.compile(
            r"([A-Z][A-Za-z\s&\-\.]+(?:LLC|Inc\.?|Ltd\.?|Corp\.?|Co\.?|Pvt\.?\s*Ltd\.?|"
            r"Private\s+Limited|Limited|Consulting|Studio|Technologies|Solutions|Services|"
            r"Agency|Group|Partners))",
            re.IGNORECASE,
        )
        match = company_re.search(text[:1500])  # Search first portion
        if match:
            return match.group(1).strip()

        # Fallback: first non-trivial line that's not a keyword
        for line in lines[:10]:
            clean = line.strip()
            if (
                clean
                and len(clean) > 3
                and len(clean) < 80
                and clean.lower() not in skip
                and not clean.startswith("---")
                and not clean.startswith("===")
            ):
                return clean

        return None

    def _extract_vendor_address(self, text: str) -> Optional[str]:
        """Extract address from text."""
        # Look for lines with address patterns (street numbers, city/state/zip)
        addr_re = re.compile(
            r"(\d+\s+[\w\s]+(?:Avenue|Ave|Street|St|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd|Block|MG\s+Road)"
            r"[^,\n]*(?:,\s*[^,\n]+){0,3})",
            re.IGNORECASE,
        )
        match = addr_re.search(text[:2000])
        if match:
            return match.group(1).strip()
        return None

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice/receipt number."""
        patterns = [
            # "Invoice #: INV-2026-0042" or "Invoice No: 12345"
            r"(?:Invoice|Inv|Receipt|Rec)\s*(?:#|No\.?|Number|Num)\s*[:.]?\s*([A-Z0-9][\w\-/]{2,25})",
            # "Receipt No: REC-78234"
            r"(?:Receipt|Order|Ref)\s*(?:#|No\.?|Number)\s*[:.]?\s*([A-Z0-9][\w\-/]{2,25})",
            # Standalone "# INV-2026-001"
            r"#\s*([A-Z]{2,5}[\-/]\d{2,}[\w\-]*)",
            # "Invoice No: GST/2026/0198" (with slash-based numbers)
            r"(?:Invoice|Inv)\s*(?:No\.?|Number|#)\s*[:.]?\s*([A-Za-z0-9][\w\-/]{3,25})",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                # Reject if it looks like a word rather than a document number
                if result.lower() in ("details", "date", "summary", "pilot", "invoicepilot"):
                    continue
                return result
        return None

    def _extract_date(self, text: str, keywords: list[str]) -> Optional[str]:
        """Extract a date associated with given keywords."""
        # Date patterns: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, etc.
        date_re = r"(\d{4}[\-/]\d{1,2}[\-/]\d{1,2}|\d{1,2}[\-/]\d{1,2}[\-/]\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4})"

        for kw in keywords:
            pattern = rf"(?:{kw})\s*[:]\s*{date_re}"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._normalize_date(match.group(1))

        # Look for any date near the top of the document
        for line in text.split("\n")[:30]:
            match = re.search(date_re, line, re.IGNORECASE)
            if match and any(kw in line.lower() for kw in keywords):
                return self._normalize_date(match.group(1))

        return None

    def _normalize_date(self, date_str: str) -> str:
        """Try to normalize a date string to YYYY-MM-DD."""
        import re as re_mod
        from datetime import datetime

        date_str = date_str.strip()

        # Already YYYY-MM-DD
        if re_mod.match(r"\d{4}-\d{1,2}-\d{1,2}$", date_str):
            return date_str

        # DD/MM/YYYY or MM/DD/YYYY
        match = re_mod.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", date_str)
        if match:
            a, b, year = int(match.group(1)), int(match.group(2)), match.group(3)
            if a > 12:  # Must be DD/MM/YYYY
                return f"{year}-{b:02d}-{a:02d}"
            elif b > 12:  # Must be MM/DD/YYYY
                return f"{year}-{a:02d}-{b:02d}"
            else:
                # Ambiguous, assume DD/MM/YYYY (international format)
                return f"{year}-{b:02d}-{a:02d}"

        # YYYY/MM/DD
        match = re_mod.match(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", date_str)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

        # "15 September 2026" style
        month_names = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        match = re_mod.match(r"(\d{1,2})\s+(\w{3})\w*\.?\s+(\d{4})", date_str)
        if match:
            day, mon, year = match.group(1), match.group(2).lower()[:3], match.group(3)
            if mon in month_names:
                return f"{year}-{month_names[mon]}-{int(day):02d}"

        return date_str

    def _extract_currency(self, text: str) -> Optional[str]:
        """Detect currency from text."""
        text_upper = text.upper()

        # Explicit currency mentions
        currency_patterns = [
            (r"\b(USD|US\s*Dollar)\b", "USD"),
            (r"\b(EUR|Euro)\b", "EUR"),
            (r"\b(GBP|British\s*Pound)\b", "GBP"),
            (r"\b(INR|Indian\s*Rupee)\b", "INR"),
            (r"\b(CAD|Canadian\s*Dollar)\b", "CAD"),
            (r"\b(AUD|Australian\s*Dollar)\b", "AUD"),
            (r"\b(JPY|Japanese\s*Yen)\b", "JPY"),
        ]
        for pat, code in currency_patterns:
            if re.search(pat, text_upper):
                return code

        # Symbol detection
        if "₹" in text or "INR" in text_upper or "RUPEE" in text_upper:
            return "INR"
        if "€" in text:
            return "EUR"
        if "£" in text:
            return "GBP"
        if "¥" in text:
            return "JPY"
        if "$" in text:
            return "USD"

        # Currency keyword near amounts
        curr_kw_re = re.search(r"(?:Currency|Curr)[\s:]*([A-Z]{3})", text, re.IGNORECASE)
        if curr_kw_re:
            return curr_kw_re.group(1).upper()

        return "USD"  # Default

    def _extract_amounts(self, text: str) -> dict:
        """Extract monetary amounts (total, subtotal, tax, etc.)."""
        amounts = {}

        # Pre-process: join lines where a label is followed by a value on the next line
        # e.g. "Subtotal:\n$4,200.00" -> "Subtotal: $4,200.00"
        joined_text = re.sub(
            r'((?:total|subtotal|sub-total|tax|discount|paid|outstanding|balance|amount|due|charged|value)[^\n]{0,30}):?\s*\n\s*',
            r'\1: ',
            text,
            flags=re.IGNORECASE,
        )

        # Amount extraction patterns — maps keywords to dict keys
        # Use [^\d]*? to skip non-digit chars (currency symbols, spaces) between label and amount
        amount_keywords = {
            "subtotal": [
                r"sub[\s\-]?total[^\d]*?\$?\s*([\d,]+\.\d{2})",
                r"taxable\s+amount[^\d]*?\$?\s*([\d,]+\.\d{2})",
            ],
            "total": [
                # Require "total" NOT preceded by "sub" to avoid matching "subtotal"
                r"(?<!sub)(?<!sub\s)total\s*(?:due|amount|invoice\s*value|charged)[^\d]*?\$?\s*([\d,]+\.\d{2})",
                r"(?<!sub)(?<!sub\s)total\s*\(?\s*(?:USD|EUR|GBP|INR|CAD|AUD)?\s*\)?[^\d]*?\$?\s*([\d,]+\.\d{2})",
                r"(?:grand\s+)?total[^\d]*?\$?\s*([\d,]+\.\d{2})",
            ],
            "tax": [
                # Match "Tax (8.25%): $346.50" — skip the percentage, capture the dollar amount
                r"(?:tax|vat|gst|sales\s+tax)\s*(?:\([^)]*%\))?[^\d$₹€£]*?[\$₹€£]\s*([\d,]+\.\d{2})",
                # Match "CGST @ 9%: INR 6,750.00" style
                r"(?:tax|vat|gst)[^:]*?:\s*(?:INR|USD|EUR|GBP|\$|₹|€|£)?\s*([\d,]+\.\d{2})",
            ],
            "discount": [
                r"discount[^\d]*?\$?\s*([\d,]+\.\d{2})",
            ],
            "paid": [
                r"(?:amount\s+)?paid[^\d]*?\$?\s*([\d,]+\.\d{2})",
            ],
            "outstanding": [
                r"(?:outstanding|balance\s+due|amount\s+due)[^\d]*?\$?\s*([\d,]+\.\d{2})",
            ],
        }

        for key, patterns in amount_keywords.items():
            for pat in patterns:
                match = re.search(pat, joined_text, re.IGNORECASE)
                if match:
                    try:
                        val = float(match.group(1).replace(",", ""))
                        if val > 0:
                            amounts[key] = val
                            break
                    except ValueError:
                        continue

        # If we found tax amounts but no single "tax", sum CGST+SGST
        if "tax" not in amounts:
            cgst = sgst = 0.0
            for pat_name, pat_val in [("cgst", r"CGST[^:]*?:\s*[^\d]*([\d,]+\.?\d{0,2})"),
                                       ("sgst", r"SGST[^:]*?:\s*[^\d]*([\d,]+\.?\d{0,2})")]:
                m = re.search(pat_val, text, re.IGNORECASE)
                if m:
                    try:
                        if pat_name == "cgst":
                            cgst = float(m.group(1).replace(",", ""))
                        else:
                            sgst = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
            if cgst + sgst > 0:
                amounts["tax"] = cgst + sgst

        # Smart derivation: compute missing values from what we have
        # If total equals subtotal but we have tax, the "total" regex matched subtotal by accident
        if ("total" in amounts and "subtotal" in amounts and "tax" in amounts
                and amounts["total"] == amounts["subtotal"]):
            amounts["total"] = round(amounts["subtotal"] + amounts["tax"], 2)

        # If no total but have subtotal + tax, derive it
        if "total" not in amounts and "subtotal" in amounts and "tax" in amounts:
            amounts["total"] = round(amounts["subtotal"] + amounts["tax"], 2)

        # If no subtotal but have total and tax, derive it
        if "subtotal" not in amounts and "total" in amounts and "tax" in amounts:
            amounts["subtotal"] = round(amounts["total"] - amounts["tax"], 2)

        return amounts

    def _extract_payment_status(self, text: str) -> Optional[str]:
        """Detect payment status from document text."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["paid", "approved", "settled", "payment received"]):
            if any(kw in text_lower for kw in ["unpaid", "not paid", "amount due", "balance due", "outstanding"]):
                return "unpaid"
            return "paid"

        if any(kw in text_lower for kw in ["unpaid", "overdue", "pending", "amount due", "balance due"]):
            return "unpaid"

        if "partial" in text_lower:
            return "partial"

        return None

    def _extract_document_type(self, text: str) -> str:
        """Determine document type."""
        text_lower = text.lower()
        if "receipt" in text_lower:
            return "receipt"
        if "credit note" in text_lower or "credit memo" in text_lower:
            return "credit_note"
        if "invoice" in text_lower or "bill" in text_lower:
            return "invoice"
        return "invoice"

    def _extract_line_items(self, text: str) -> list[AILineItem]:
        """Extract line items from structured text."""
        items = []

        # Pattern: description followed by amount(s)
        # Look for lines with a dollar/currency amount
        amount_line_re = re.compile(
            r"^[\s]*(.{5,60}?)\s{2,}(\d+)?\s*[\$₹€£]?\s*([\d,]+\.?\d{0,2})\s*$",
            re.MULTILINE,
        )

        for match in amount_line_re.finditer(text):
            desc = match.group(1).strip()
            qty_str = match.group(2)
            amount_str = match.group(3)

            # Skip header/summary lines
            skip_words = {"total", "subtotal", "tax", "discount", "due", "paid", "balance",
                          "description", "amount", "qty", "quantity", "item", "---"}
            if any(sw in desc.lower() for sw in skip_words):
                continue

            try:
                amount = float(amount_str.replace(",", ""))
                qty = float(qty_str) if qty_str else 1.0
                unit_price = round(amount / qty, 2) if qty > 0 else amount

                items.append(AILineItem(
                    description=desc,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=amount,
                ))
            except (ValueError, ZeroDivisionError):
                continue

        # Also try "description   $amount" pattern (with currency symbol)
        if not items:
            currency_line_re = re.compile(
                r"^[\s]*(.{5,60}?)\s+[\$₹€£]\s*([\d,]+\.?\d{0,2})\s*$",
                re.MULTILINE,
            )
            for match in currency_line_re.finditer(text):
                desc = match.group(1).strip()
                amount_str = match.group(2)

                skip_words = {"total", "subtotal", "tax", "discount", "due", "paid", "balance"}
                if any(sw in desc.lower() for sw in skip_words):
                    continue

                try:
                    amount = float(amount_str.replace(",", ""))
                    items.append(AILineItem(
                        description=desc,
                        quantity=1.0,
                        unit_price=amount,
                        line_total=amount,
                    ))
                except ValueError:
                    continue

        return items[:20]  # Cap at 20 items

    def _categorize_expense(self, text: str, vendor_name: Optional[str] = None) -> str:
        """Categorize expense based on document content."""
        combined = (text + " " + (vendor_name or "")).lower()

        category_keywords = {
            "Software & Subscriptions": [
                "software", "subscription", "saas", "cloud", "hosting", "domain",
                "license", "api", "storage", "backup", "plan", "pro plan",
            ],
            "Professional Services": [
                "consulting", "legal", "accounting", "advisory", "audit",
                "design", "development", "architecture", "engineering",
                "freelance", "contractor",
            ],
            "Travel": [
                "flight", "hotel", "airfare", "uber", "taxi", "rental car",
                "transportation", "travel", "lodging", "mileage",
            ],
            "Food & Meals": [
                "restaurant", "cafe", "coffee", "catering", "lunch", "dinner",
                "breakfast", "meal", "food", "beverage", "latte", "croissant",
            ],
            "Office Supplies": [
                "office", "paper", "printer", "toner", "stationery", "supplies",
                "desk", "chair", "monitor",
            ],
            "Equipment": [
                "computer", "laptop", "phone", "hardware", "server", "gpu",
                "keyboard", "mouse", "headset", "camera",
            ],
            "Marketing": [
                "advertising", "marketing", "ads", "promotion", "social media",
                "seo", "campaign", "branding",
            ],
            "Utilities": [
                "electric", "gas", "water", "internet", "phone bill", "utility",
                "broadband", "fiber", "mobile",
            ],
            "Rent": ["rent", "lease", "coworking", "office space", "workspace"],
            "Insurance": ["insurance", "policy", "premium", "coverage"],
        }

        best_category = "Other"
        best_score = 0

        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def _demo_extraction(self, document_text: str) -> AIExtractionResult:
        """Return a demo extraction result when AI is unavailable."""
        # Only used in explicit demo mode — now redirects to heuristic
        return self._heuristic_extraction(document_text)


# Module-level singleton
ai_extractor = AIExtractor()
