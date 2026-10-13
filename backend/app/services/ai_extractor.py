"""InvoicePilot AI — AI extraction service using Ollama + Gemma.

Sends extracted document text to a local Gemma model and parses
structured invoice data from the response.
"""

import json
import logging
import re
from typing import Optional

import httpx

from app.config import settings
from app.schemas import AIExtractionResult

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
    """Extracts structured invoice data using Ollama + Gemma."""

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
                        "message": "Ollama is not responding.",
                    }

                # Check if model is available
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check both exact match and prefix match (e.g. "gemma3:4b" matches "gemma3:4b")
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
                    return {
                        "status": "disconnected",
                        "model": self.model,
                        "ollama_url": self.base_url,
                        "message": (
                            f"Model '{self.model}' not found. "
                            f"Available: {', '.join(model_names) or 'none'}. "
                            f"Run: ollama pull {self.model}"
                        ),
                    }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "model": self.model,
                "ollama_url": self.base_url,
                "message": "Cannot connect to Ollama. Is it running?",
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "model": self.model,
                "ollama_url": self.base_url,
                "message": f"Health check failed: {type(e).__name__}",
            }

    async def extract(self, document_text: str) -> AIExtractionResult:
        """
        Send document text to Gemma and parse the structured extraction result.
        Retries on malformed JSON up to max_retries times.
        """
        if settings.demo_mode:
            return self._demo_extraction(document_text)

        # Truncate text to fit within context window (rough token estimate)
        truncated = self._truncate_text(document_text)
        prompt = EXTRACTION_PROMPT.format(
            document_text=truncated,
            categories=", ".join(EXPENSE_CATEGORIES),
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw_response = await self._call_ollama(prompt)
                result = self._parse_response(raw_response)
                logger.info("AI extraction succeeded on attempt %d", attempt)
                return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "AI extraction attempt %d/%d failed: %s",
                    attempt, self.max_retries, str(e)
                )
                last_error = e

        raise ValueError(
            f"AI extraction failed after {self.max_retries} attempts: {last_error}"
        )

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama generate API and return the response text."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": self.context_length,
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

    def _demo_extraction(self, document_text: str) -> AIExtractionResult:
        """Return a demo extraction result when AI is unavailable."""
        # Only used in explicit demo mode
        return AIExtractionResult(
            vendor_name="[Demo] Sample Vendor",
            invoice_number="DEMO-001",
            invoice_date="2026-01-15",
            currency="USD",
            total_amount=0.0,
            document_type="invoice",
            expense_category="Other",
        )


# Module-level singleton
ai_extractor = AIExtractor()
