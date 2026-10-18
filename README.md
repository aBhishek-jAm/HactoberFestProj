# InvoicePilot AI 🧾⚡

**Private, local-first AI invoice & expense assistant for freelancers and small businesses.**

> Built for the **Hacktoberfest 2026 Open-Source AI Challenge: Side Hustle Track**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/Frontend-React%2019-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS v4](https://img.shields.io/badge/Styling-Tailwind%20v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Tests: 42 Passing](https://img.shields.io/badge/Tests-42%20Passing-success.svg)](backend/tests/)
[![AI Model: Gemma 2B](https://img.shields.io/badge/AI%20Model-Gemma%202B-8E75C4.svg?logo=google&logoColor=white)](https://ollama.com)

---

InvoicePilot AI automatically extracts, validates, and organizes financial data from invoices and receipts using a **local open-weight AI model** (Gemma via Ollama). 

**Zero cloud subscriptions. Zero API keys. Zero document leakage.** Your sensitive tax IDs, client contracts, and bank records never leave your machine. If Ollama is slow or unavailable, InvoicePilot automatically falls back to an instant regex-based heuristic extractor so processing **never fails or hangs**.

---

## 🎯 The Problem

Every month, millions of freelancers, contractors, and side hustlers face administrative exhaustion:
- ⏳ **Hours wasted**: 3–7 hours spent manually copying invoice dates, amounts, and tax numbers into spreadsheets.
- 💸 **Costly SaaS tools**: Commercial document processors charge $30–$100/mo or expensive per-page fees with enterprise lock-in.
- 🔒 **Confidentiality violations**: Uploading client NDAs, invoices, and bank numbers to proprietary cloud APIs exposes sensitive data.
- 🧮 **Unreliable AI math**: Generic chatbots hallucinate totals, invent line items, and fail tax arithmetic.

## 💡 The Solution

1. **Drop any invoice or receipt** (PDF, PNG, JPG) into the web interface.
2. **Dual-engine extraction** pulls vendor, invoice number, issue & due dates, currency, subtotal, tax, total, and individual line items.
3. **Deterministic math verification** validates `subtotal + tax - discount == total` with confidence scoring.
4. **Interactive review & inline edits** let you verify or modify any field in real time.
5. **Secure export** generates OWASP-sanitized CSV and styled Excel (`.xlsx`) spreadsheets ready for tax filing.

---

## ✨ Features

| Feature | Description |
|:---|:---|
| 📄 **Multi-Format Ingestion** | Native PDFs (PyMuPDF), scanned PDFs & PNG/JPG images (Tesseract OCR) |
| 🤖 **Local AI Extraction** | Gemma 2B running via Ollama extracts structured JSON via guided prompts |
| ⚡ **Zero-Fail Fallback Engine** | Deterministic regex extractor instantly activates if Ollama times out or is offline |
| 🛡️ **Transaction Safe** | State-isolated processing (`db.expire_all()`) guarantees zero DB deadlock or corrupt jobs |
| 🧮 **Deterministic Verification** | Subtotal, tax, and discount arithmetic verified with configurable tolerance (2%) |
| 🔍 **Confidence & Issue Flags** | Transparent 0.0–1.0 confidence score with actionable issue flags (e.g. `ARITHMETIC_MISMATCH`) |
| ✏️ **Full Interactive Review** | Edit vendor, amounts, dates, status, category, and line items in a clean modal UI |
| 📊 **Financial Dashboard** | Monthly spending trends, currency breakdowns, category distributions via Recharts |
| 💱 **Multi-Currency Support** | Seamlessly groups and totals mixed currencies (USD, INR, EUR, GBP, CAD, etc.) |
| 📥 **Formula-Safe Exports** | CSV and Excel (`.xlsx`) exports sanitized against OWASP spreadsheet injection (`=`, `+`, `-`, `@`) |
| 🌙 **Modern Glassmorphic UI** | Dark & light theme, drag-and-drop file upload, Sonner toast notifications |
| 🔒 **100% Private & Air-Gapped** | All processing is performed strictly on `localhost` — zero external network telemetry |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 InvoicePilot AI Web UI                      │
│     (React 19 + TypeScript + Vite + Tailwind CSS v4)        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST (Vite Proxy)
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (Python)                 │
│                                                             │
│  ┌────────────────────────┐    ┌─────────────────────────┐  │
│  │ Document Ingestion     │    │ AI Extraction Engine    │  │
│  │ • PyMuPDF (native text)│───►│ • Gemma 2B via Ollama   │  │
│  │ • Tesseract (OCR image)│    │ • 30s timeout guard     │  │
│  └────────────────────────┘    │ • Token bound (512 max) │  │
│                                └────────────┬────────────┘  │
│                                             │ (Fallback if   │
│                                             ▼  Ollama slow) │
│                                ┌─────────────────────────┐  │
│                                │ Heuristic Regex Engine  │  │
│                                │ • Deterministic fields  │  │
│                                │ • Line-item parsing     │  │
│                                └────────────┬────────────┘  │
│                                             │               │
│  ┌────────────────────────┐    ┌────────────▼────────────┐  │
│  │ Deterministic Validator│◄───┤ Transaction Isolation   │  │
│  │ • Subtotal + Tax check │    │ • db.expire_all()       │  │
│  │ • Date sanity check    │    │ • Auto-rollback safety  │  │
│  │ • Duplicate detection  │    └─────────────────────────┘  │
│  └───────────┬────────────┘                                 │
│              │                                              │
│  ┌───────────▼────────────┐    ┌─────────────────────────┐  │
│  │ SQLite Database        │    │ Export Service          │  │
│  │ • SQLAlchemy Models    │───►│ • CSV (OWASP sanitized) │  │
│  │ • Processing jobs      │    │ • Excel OpenPyXL (.xlsx)│  │
│  └────────────────────────┘    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**:
1. **Upload**: User drops a document into the UI (`POST /api/documents/upload`).
2. **Text Extraction**: PyMuPDF extracts native text in milliseconds (or Tesseract OCR for images).
3. **Extraction**: Gemma 2B parses structured JSON. If Ollama takes >30s or is offline, the deterministic heuristic extractor automatically parses all fields without delay.
4. **Validation**: Arithmetic checks, line-item sums, and duplicate detection compute a confidence score.
5. **Persistence**: Clean data is committed to SQLite with re-upload overwrite protection.
6. **Review & Export**: User reviews/edits fields on the web UI and downloads clean CSV/Excel files.

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** & **npm**
- **Ollama** ([download here](https://ollama.com)) — *Optional; InvoicePilot includes full regex fallback*
- **Tesseract OCR** — *Optional; only needed for scanned receipt photos*

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/aBhishek-jAm/HactoberFestProj.git
cd HactoberFestProj
cp .env.example .env
```

---

### Step 2: (Optional) Start Ollama AI

```bash
# Pull the lightweight, fast Gemma 2B model (~1.6 GB)
ollama pull gemma:2b

# Start the Ollama server (keep running in background)
ollama serve
```

> **Note**: Don't have Ollama installed? No problem! InvoicePilot will automatically run with its built-in heuristic pattern matcher. All fields and line items will still be extracted accurately.

---

### Step 3: Start the Backend

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**On Linux / macOS:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be live at:
- **API Root**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

### Step 4: Start the Frontend

In a new terminal window:

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** in your browser. The Vite development server automatically proxies API calls to the backend on port 8000.

---

### Step 5: Test with Pre-built Sample Invoices

We include 4 realistic synthetic invoices in the `demo_samples/` folder:

| File | Type | Currency | Description |
|:---|:---|:---|:---|
| `sample_invoice_01_acme_design.pdf` | PDF | USD | Consulting invoice with 4 line items ($4,546.50 total) |
| `sample_invoice_02_global_tech_gst.pdf` | PDF | INR | Tech software license with 18% GST (₹1,00,300 total) |
| `sample_receipt_03_cloudstack_pro.png` | PNG | USD | Monthly cloud hosting receipt ($149.00 total) |
| `sample_receipt_04_cafe_meeting.png` | PNG | USD | Client coffee meeting receipt with tip ($28.89 total) |

Drag and drop any of these files into `http://localhost:5173/upload` to test the full pipeline!

You can also re-generate synthetic samples anytime:
```bash
python scripts/generate_sample_documents.py
```

---

### Step 6: (Optional) Run with Docker

```bash
# Ensure Ollama is running on your host machine first
docker-compose up --build
```

- Web UI: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`

---

## 📁 Repository Structure

```
HactoberFestProj/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application, route handlers, error handling
│   │   ├── config.py            # Pydantic Settings loaded from environment/.env
│   │   ├── database.py          # SQLite engine & session factory
│   │   ├── models.py            # SQLAlchemy models (Document, Invoice, LineItem, ProcessingJob)
│   │   ├── schemas.py           # Pydantic schemas (Extraction, DocumentResponse, DashboardSummary)
│   │   └── services/
│   │       ├── document_processor.py  # PyMuPDF text & Tesseract OCR extraction
│   │       ├── ai_extractor.py        # Ollama Gemma 2B extraction + heuristic fallback
│   │       ├── validator.py           # Deterministic math, dates, and confidence scoring
│   │       └── exporter.py            # Formula-safe CSV and OpenPyXL Excel export
│   ├── tests/
│   │   ├── test_main.py         # 42 unit and integration tests (100% passing)
│   │   └── fixtures/            # Test document fixtures
│   ├── requirements.txt         # Pinned Python dependencies
│   └── Dockerfile
├── demo_samples/                # 4 ready-to-test synthetic invoices & receipts
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.tsx       # Sidebar navigation, header, theme toggle
│   │   │   └── ui.tsx           # Radix UI primitives & custom components
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Summary metrics & Recharts visualizations
│   │   │   ├── Upload.tsx       # Drag-and-drop batch upload with react-dropzone
│   │   │   ├── Invoices.tsx     # Filterable and searchable invoice list
│   │   │   ├── InvoiceDetail.tsx# Review modal with live inline field editing
│   │   │   ├── Reports.tsx      # Expense reports by category and currency
│   │   │   └── Settings.tsx     # System status, AI diagnostics, and privacy controls
│   │   ├── lib/
│   │   │   ├── api.ts           # Typed API client with error handling
│   │   │   └── utils.ts         # Formatting utilities and currency helpers
│   │   ├── App.tsx              # React router configuration
│   │   └── main.tsx             # Application bootstrap
│   ├── package.json             # React 19, Vite, Tailwind v4 dependencies
│   └── Dockerfile
├── scripts/
│   └── generate_sample_documents.py  # PyMuPDF + Pillow synthetic document generator
├── docker-compose.yml           # Multi-container orchestration
├── .env.example                 # Documented environment configuration template
├── LICENSE                      # MIT License
├── SUBMISSION.md                # Hacktoberfest 2026 official submission report
└── README.md                    # Project documentation
```

---

## 🔌 API Endpoints Reference

All endpoints return JSON responses with standard HTTP status codes.

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/health` | Backend and database health status |
| `GET` | `/api/health/ai` | Ollama connectivity and loaded model verification |
| `POST` | `/api/documents/upload` | Upload one or multiple documents (multipart/form-data) |
| `GET` | `/api/documents` | List uploaded documents with status/search filtering |
| `GET` | `/api/documents/{id}` | Retrieve full invoice details, line items, and job status |
| `PATCH` | `/api/documents/{id}` | Update invoice fields (vendor, amounts, category, status) |
| `DELETE` | `/api/documents/{id}` | Delete document, associated invoice, and disk file |
| `POST` | `/api/documents/{id}/process` | Trigger re-processing of an uploaded document |
| `POST` | `/api/documents/{id}/retry` | Retry processing after a failure or update |
| `GET` | `/api/dashboard/summary` | Aggregated dashboard stats, currency groups, and monthly trends |
| `GET` | `/api/reports/expenses` | Filtered expense reports grouped by category and date |
| `GET` | `/api/exports/csv` | Download sanitized CSV export of processed invoices |
| `GET` | `/api/exports/xlsx` | Download styled Excel workbook with summary sheet |

---

## 🧪 Automated Testing

InvoicePilot AI features a comprehensive test suite of **42 automated unit and integration tests** built with `pytest`:

```bash
cd backend
pytest tests/ -v
```

### Test Coverage Highlights:
- **AI Response Parsing**: Clean JSON, markdown codeblock parsing (` ```json `), defensive regex repair on truncated outputs.
- **Deterministic Math Validation**: Tolerance thresholds, subtotal + tax = total verification, line-item sum consistency.
- **Date & Currency Validation**: Date format enforcement, issue vs due date comparison, ISO currency checks.
- **Duplicate Detection**: Identifies matching vendor + invoice number pairs.
- **OWASP Formula Injection Defense**: Asserts formula prefixes (`=`, `+`, `-`, `@`, `\t`) are escaped with `'` in CSV and XLSX exports.
- **API Endpoint Lifecycles**: Upload, processing job lifecycle, status polling, update PATCH, and DELETE operations.
- **Multi-Currency Aggregations**: Tests dashboard summary grouping across USD, INR, EUR.

```text
============================== test session starts ==============================
platform win32 -- Python 3.14 / 3.12 -- pytest-9.1.1
collected 42 items

tests\test_main.py ..........................................            [100%]

======================== 42 passed, 1 warning in 9.94s ========================
```

---

## ⚙️ Configuration Reference

Configure settings in your `.env` file (copied from `.env.example`):

| Variable | Default | Description |
|:---|:---|:---|
| `BACKEND_HOST` | `0.0.0.0` | Backend bind address |
| `BACKEND_PORT` | `8000` | Backend port |
| `DATABASE_URL` | `sqlite:///./invoicepilot.db` | SQLAlchemy SQLite database connection string |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins for frontend client |
| `UPLOAD_DIR` | `./uploads` | Storage directory for uploaded documents |
| `MAX_FILE_SIZE_MB` | `20` | Maximum upload file size in megabytes |
| `ALLOWED_EXTENSIONS`| `pdf,png,jpg,jpeg` | Permitted document file extensions |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `gemma:2b` | Ollama model identifier (`gemma:2b`, `phi3:mini`) |
| `OLLAMA_TIMEOUT` | `30` | Seconds before falling back to the heuristic extractor |
| `OLLAMA_CONTEXT_LENGTH` | `2048` | Context window size in tokens |
| `OLLAMA_NUM_PREDICT` | `512` | Max token limit per AI response |
| `DEMO_MODE` | `false` | When true, skips Ollama and uses heuristic engine directly |
| `ARITHMETIC_TOLERANCE` | `0.02` | Permitted rounding difference (2%) for math checks |
| `MAX_RETRIES` | `1` | Number of AI attempts before activating heuristic engine |
| `LOG_LEVEL` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`) |

---

## 🔒 Security & Privacy Guarantees

1. **Local Model Execution**: Invoices are processed exclusively on `localhost` via Ollama. No data is ever transmitted to commercial third-party APIs (OpenAI, Anthropic, Google Cloud).
2. **OWASP Formula Injection Defense**: When exporting CSV or Excel files, any value beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` is escaped with a leading single quote (`'`), neutralizing spreadsheet formula execution attacks.
3. **Log Sanitization**: Raw document text, invoice totals, client names, and tax numbers are strictly barred from log output.
4. **Filesystem Hardening**: Uploaded files receive cryptographically random UUID names to prevent path traversal attacks (`../../etc/passwd`).
5. **Session Isolation**: Background processing jobs use explicit database session refresh mechanisms (`db.expire_all()`) and atomic commits to eliminate dirty reads and lock contention.

---

## 🌐 Why Open-Weight Models (Gemma) Beat Cloud APIs for Side Hustles

| Attribute | Cloud AI APIs (GPT-4, Claude) | Open-Weight Gemma (InvoicePilot AI) |
|:---|:---|:---|
| **Cost** | Per-token / per-document charge | **$0.00** — 100% free forever |
| **Privacy** | Uploads customer & tax data to remote servers | **Air-gapped** on user machine |
| **Client NDAs** | Often prohibited by freelance contracts | **Fully compliant** with zero data transfer |
| **Offline Work** | Fails without active internet | **Full functionality** on flights, trains, cafes |
| **Vendor Lock-in**| Subject to API deprecations & price hikes | **Open weights** you own and control |

---

## 🛠️ Troubleshooting

| Issue | Resolution |
|:---|:---|
| **Frontend displays "Cannot connect to backend"** | Ensure the backend is running (`uvicorn app.main:app --port 8000`) and CORS matches in `.env`. |
| **Document stays in "processing" state** | The backend includes a 30s timeout guard. If Ollama is slow, it automatically falls back to regex heuristics within 30s. |
| **"Cannot connect to Ollama" in Settings** | Run `ollama serve` in a terminal, or set `DEMO_MODE=true` in `.env` to skip Ollama. |
| **Ollama "Model not found"** | Run `ollama pull gemma:2b` to download the recommended model. |
| **Image OCR not extracting text** | Install Tesseract OCR: Windows (`winget install tesseract`), macOS (`brew install tesseract`), Linux (`sudo apt install tesseract-ocr`). |
| **Database locked / Stale data** | Stop the backend, delete `backend/invoicepilot.db`, and restart to recreate clean tables. |

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository: `https://github.com/aBhishek-jAm/HactoberFestProj.git`
2. Create a descriptive feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: Add your feature'`
4. Ensure all tests pass: `cd backend && pytest`
5. Push to your branch: `git push origin feature/your-feature`
6. Open a Pull Request on GitHub.

---

## 📝 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

*Built with ❤️ for Hacktoberfest 2026 — Empowering independent workers with private, local AI.*
