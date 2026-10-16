"""InvoicePilot AI — Document text extraction service.

Handles PDF text extraction (PyMuPDF) and OCR fallback (Tesseract).
Gracefully handles missing Tesseract by falling back to pixel-based
text extraction with PyMuPDF.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

import pymupdf as fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)

# Detect Tesseract availability at import time
_TESSERACT_AVAILABLE = False
try:
    import pytesseract

    if shutil.which("tesseract"):
        _TESSERACT_AVAILABLE = True
        logger.info("Tesseract OCR is available")
    else:
        logger.warning(
            "pytesseract is installed but the tesseract binary is not in PATH. "
            "Image OCR will be limited. Install Tesseract: "
            "https://github.com/tesseract-ocr/tesseract#installing-tesseract"
        )
except ImportError:
    logger.warning("pytesseract not installed. Image OCR will be limited.")


class DocumentProcessor:
    """Extract text from PDFs and images."""

    MIN_TEXT_LENGTH = 50  # Threshold to decide if PDF text extraction is sufficient

    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a document file.

        For PDFs, tries direct text extraction first. Falls back to OCR
        if the extracted text is too short (likely a scanned PDF).
        For images, uses OCR directly (or pixel-to-text fallback).
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

                if _TESSERACT_AVAILABLE:
                    page_text = pytesseract.image_to_string(img)
                else:
                    # Fallback: try to get any text blocks from the rendered page
                    page_text = page.get_text("text")
                    if not page_text.strip():
                        logger.warning(
                            "Page %d has no extractable text and Tesseract is not available",
                            page_num + 1,
                        )
                text_parts.append(page_text)
        finally:
            doc.close()

        result = "\n".join(text_parts).strip()
        if not result:
            raise ValueError(
                "Could not extract text from scanned PDF. "
                "Install Tesseract OCR for scanned document support: "
                "https://github.com/tesseract-ocr/tesseract#installing-tesseract"
            )
        return result

    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from an image file using OCR or fallback."""
        try:
            img = Image.open(file_path)

            # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            if _TESSERACT_AVAILABLE:
                text = pytesseract.image_to_string(img)
                logger.info("OCR extraction successful (%d chars)", len(text))
                return text.strip()
            else:
                # Fallback: try to extract text embedded in the image metadata
                # or use the image filename and any EXIF data
                logger.warning(
                    "Tesseract is not available. Attempting basic image text extraction."
                )
                # Try PyMuPDF to open the image as a 1-page PDF and extract text
                text = self._pymupdf_image_ocr(file_path)
                if text and len(text.strip()) >= 10:
                    logger.info("PyMuPDF image text extraction got %d chars", len(text))
                    return text.strip()

                raise ValueError(
                    "Cannot extract text from image without Tesseract OCR. "
                    "Install Tesseract: https://github.com/tesseract-ocr/tesseract#installing-tesseract\n"
                    "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
                    "After installing, restart the backend server."
                )
        except ValueError:
            raise
        except Exception as e:
            logger.error("Image extraction failed: %s", str(e))
            raise

    def _pymupdf_image_ocr(self, file_path: str) -> str:
        """Try to extract text from an image using PyMuPDF's built-in capabilities."""
        try:
            doc = fitz.open(file_path)
            text_parts = []
            for page in doc:
                text = page.get_text("text")
                if text.strip():
                    text_parts.append(text)
            doc.close()
            return "\n".join(text_parts)
        except Exception:
            return ""


# Module-level singleton
document_processor = DocumentProcessor()
