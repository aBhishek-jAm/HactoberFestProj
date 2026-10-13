"""InvoicePilot AI — Document text extraction service.

Handles PDF text extraction (PyMuPDF) and OCR fallback (Tesseract).
"""

import logging
import os
from pathlib import Path
from typing import Optional

import pymupdf as fitz  # PyMuPDF
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Extract text from PDFs and images."""

    MIN_TEXT_LENGTH = 50  # Threshold to decide if PDF text extraction is sufficient

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a document file.

        For PDFs, tries direct text extraction first. Falls back to OCR
        if the extracted text is too short (likely a scanned PDF).
        For images, uses OCR directly.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path.name}")

        ext = path.suffix.lower()

        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg"):
            return self._extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF, falling back to OCR if needed."""
        try:
            text = self._extract_pdf_text(file_path)
            if len(text.strip()) >= self.MIN_TEXT_LENGTH:
                logger.info("PDF text extraction successful (%d chars)", len(text))
                return text.strip()

            logger.info("PDF text too short (%d chars), falling back to OCR", len(text))
            return self._ocr_pdf(file_path)
        except Exception as e:
            logger.error("PDF extraction failed: %s", str(e))
            raise

    def _extract_pdf_text(self, file_path: str) -> str:
        """Direct text extraction from text-based PDFs using PyMuPDF."""
        doc = fitz.open(file_path)
        text_parts = []
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())
        finally:
            doc.close()
        return "\n".join(text_parts)

    def _ocr_pdf(self, file_path: str) -> str:
        """Convert PDF pages to images and run OCR on each page."""
        doc = fitz.open(file_path)
        text_parts = []
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render page to image at 300 DPI for quality OCR
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img)
                text_parts.append(page_text)
        finally:
            doc.close()
        return "\n".join(text_parts)

    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from an image file using OCR."""
        try:
            img = Image.open(file_path)

            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            text = pytesseract.image_to_string(img)
            logger.info("OCR extraction successful (%d chars)", len(text))
            return text.strip()
        except Exception as e:
            logger.error("Image OCR failed: %s", str(e))
            raise


# Module-level singleton
document_processor = DocumentProcessor()
