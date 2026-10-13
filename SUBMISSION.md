# InvoicePilot AI: Private, Local-First AI Invoice & Expense Assistant for Freelancers

*Built for the Hacktoberfest 2026 Open-Source AI Challenge: Side Hustle Track.*

---

## 1. The Problem

Every month, millions of freelancers, independent contractors, and small business owners face the same dreaded administrative burden: **the shoebox of receipts and stack of invoices**.

Whether preparing quarterly taxes, sending client expense reimbursements, or closing monthly bookkeeping, independent workers spend **3 to 7 hours every month** manually re-typing invoice numbers, line-item totals, tax breakdowns, and dates into spreadsheets.

### Why existing solutions fail freelancers:
1. **Expensive SaaS subscriptions**: Traditional enterprise document processors (like ABBYY, AWS Textract, or proprietary accountant tools) cost $30–$100/month or charge per-page fees with steep commitments.
2. **Severe privacy and confidentiality risks**: Uploading confidential client contracts, NDAs, personal tax identification numbers (SSNs/EINs/GSTINs), and client billing rates to multi-tenant commercial cloud AI APIs violates freelance client NDAs and data jurisdiction laws (GDPR/HIPAA/CCPA).
3. **Black-box AI hallucinations**: Generic chatbots hallucinate invoice numbers, invent subtotal arithmetic, and cannot be trusted with tax records.

**InvoicePilot AI** solves this by pairing **local open-weight AI (Gemma running via Ollama)** with **deterministic arithmetic verification**, **formula-injection-safe exports**, and a **clean, modern web interface**.

Your financial records **never leave your device**.

---

## 2. Target Customers & Real-World Use Cases

| Target Persona | Key Pain Point | How InvoicePilot AI Helps |
| :--- | :--- | :--- |
| **Independent Tech Consultants & Freelancers** | Multiple clients, mixed currencies (USD, EUR, GBP, INR), monthly expense reports. | Batch uploads 20+ receipts/invoices; extracts vendor, tax, and currency in seconds; exports directly to Excel. |
| **Creative Agencies & Boutiques** | Subcontractor invoices with complex line-item breakdowns. | Extracts line items, validates subtotal + tax = total math, highlights arithmetic errors. |
| **Side Hustlers & Solopreneurs** | Budget-conscious; cannot afford $50/month accounting software. | 100% free and open-source. Runs locally on consumer laptops with Ollama. |
| **Privacy-Conscious Professionals** | Strict client NDAs preventing document uploads to public cloud APIs. | Air-gapped local inference. Financial PDFs and images are processed on `localhost`. |

---

## 3. Technical Architecture & System Design

InvoicePilot AI follows a **hybrid AI + deterministic verification architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                 InvoicePilot AI Web UI                      │
│     (React 19 + TypeScript + Vite + Tailwind CSS + Lucide)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (Python)                 │
│                                                             │
│  ┌────────────────────────┐    ┌─────────────────────────┐  │
│  │ Document Ingestion     │    │ AI Extraction Engine    │  │
│  │ • PyMuPDF (native text)│───►│ • Gemma 2 / 3 via Ollama│  │
│  │ • Tesseract (OCR image)│    │ • Schema-guided JSON    │  │
│  └────────────────────────┘    └────────────┬────────────┘  │
│                                             │               │
│  ┌────────────────────────┐    ┌────────────▼────────────┐  │
│  │ Deterministic Validator│◄───┤ Defensive JSON Repair   │  │
│  │ • Subtotal + Tax check │    │ • Markdown fence repair │  │
│  │ • Confidence scoring   │    │ • Malformed fix regex   │  │
│  │ • Duplicate detection  │    └─────────────────────────┘  │
│  └───────────┬────────────┘                                 │
│              │                                              │
│  ┌───────────▼────────────┐    ┌─────────────────────────┐  │
│  │ SQLite Persistence     │    │ Export Service          │  │
│  │ • SQLAlchemy Models    │───►│ • CSV (OWASP sanitized) │  │
│  │ • Audit logs & edits   │    │ • OpenPyXL Excel (.xlsx)│  │
│  └────────────────────────┘    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### The Ingestion & AI Pipeline:

1. **Document Text Extraction (`app/services/document_processor.py`)**:
   - Native PDFs are parsed using **PyMuPDF** (`pymupdf`), achieving near-instantaneous text extraction without image rendering overhead.
   - Scanned PDFs or uploaded images (`.png`, `.jpg`, `.jpeg`) fall back dynamically to **Tesseract OCR**.
2. **Structured AI Inference with Gemma (`app/services/ai_extractor.py`)**:
   - Prompts the locally running Gemma model via Ollama with strict JSON schema instructions and few-shot formatting guidance.
   - Robust defensive repair parses markdown codeblocks, truncations, or malformed characters before validation.
   - Built-in graceful fallback to heuristic regex parsing if Ollama is offline or in demo mode.
3. **Deterministic Verification Engine (`app/services/validator.py`)**:
   - Computes: `abs(subtotal + tax - total_amount) <= tolerance`
   - Calculates line-item sum consistency.
   - Performs date sanity checks (issue date vs. due date).
   - ISO-4217 currency code validation.
   - Computes a granular **0.0–1.0 Confidence Score** with transparent issue flags (`MISSING_MANDATORY_FIELD`, `ARITHMETIC_MISMATCH`, `DUPLICATE_SUSPECT`).
4. **Formula Injection Sanitization (`app/services/exporter.py`)**:
   - Prevents OWASP CSV/Excel Formula Injection attacks by prefixing dangerous characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes (`'`).
5. **Interactive Frontend (`frontend/src/`)**:
   - Responsive multi-page application with dashboard metrics, drag-and-drop batch upload, full invoice review modal with inline editing, Recharts financial visualizations, and settings health check.

---

## 4. Why Open-Weight Models (Gemma) Matter Here

For freelance and small business tools, open-weight AI is not just a nice-to-have — it is a foundational product advantage:

1. **Zero Marginal Inference Cost**: Proprietary vision/multimodal APIs charge $0.01 to $0.05 per document. For a freelancer scanning hundreds of receipts a year, costs compound quickly. Gemma on Ollama runs at zero cost on local hardware.
2. **Absolute Data Sovereignty**: Invoices contain bank accounts, client addresses, tax numbers, and pricing strategies. Running Gemma on `localhost` ensures sensitive data never crosses the wire.
3. **Offline Reliability**: Freelancers working on planes, trains, or in cafes without reliable internet can still process receipts and prepare expense reports seamlessly.
4. **Customizability**: As an open model, Gemma's prompts can be tuned and quantized (e.g., 2B or 9B parameters) to fit any hardware constraint, from modest ultrabooks to high-end workstations.

---

## 5. Security & Privacy Highlights

- **Air-Gapped Local Inference**: Ollama processes documents locally at `http://localhost:11434`.
- **Zero Document Leakage in Logs**: Document text, invoice numbers, and client names are never written to server log streams.
- **OWASP Formula Injection Defense**: Prevents malicious spreadsheet macros from executing when exported files are opened in Microsoft Excel or Google Sheets.
- **Strict Input Validation**: Max 20MB file size limits, MIME type verification, and path traversal protection.

---

## 6. Testing & Quality Assurance

The codebase includes an automated test suite with **42 passing tests** across 8 test suites:

- `TestAIExtractionSchema`: Validates Pydantic extraction schemas and normalization.
- `TestAIResponseParsing`: Tests JSON extraction from markdown blocks, messy outputs, and error handling.
- `TestInvoiceValidator`: Mathematical tolerance, missing fields, invalid dates, currency validation, confidence scoring, and duplicate detection.
- `TestExportService`: CSV export, Excel `.xlsx` generation, and formula injection sanitization.
- `TestHealthEndpoints`: Service health and live Ollama AI connectivity.
- `TestDocumentAPI`: Document upload, list, retrieve, update, delete, and dashboard aggregations.
- `TestCurrencyHandling`: Multi-currency summary grouping.

All tests run locally in under 10 seconds without needing Ollama or external dependencies.

---

## 7. Known Limitations & Future Roadmap

### Current Limitations:
- Multi-page tables spanning across page breaks are concatenated; complex multi-page nested tables can occasionally lose cell alignment.
- Handwritten receipts require clean handwriting for Tesseract OCR; cursive script has a higher error rate.

### Roadmap for v0.2+:
- Multi-page document split-and-merge tool.
- Direct integration with open accounting tools (e.g., Ledger CLI, Beancount).
- Gemma fine-tuning on diverse open receipt datasets for even higher accuracy on low-contrast mobile phone receipt photos.
- Multi-language receipt extraction (Spanish, German, Japanese, French).

---

## 8. Quick Start Guide

### 1. Clone the repository
```bash
git clone https://github.com/your-username/invoicepilot-ai.git
cd invoicepilot-ai
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```
Access the application at:
- **Frontend**: `http://localhost:5173`
- **Backend API & Swagger Docs**: `http://localhost:8000/docs`

### 3. Run Locally (Without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest  # Run the 42 unit tests
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Optional: Enable Local Gemma Model via Ollama:**
```bash
ollama run gemma:2b
```

---

## 9. Conclusion

InvoicePilot AI proves that **open-weight AI models** can deliver enterprise-grade utility to independent workers without cloud subscriptions, proprietary lock-in, or privacy compromises.

*Check out the repository, run the sample invoices, and star the project on GitHub!*
