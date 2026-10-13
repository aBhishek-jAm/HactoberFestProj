# InvoicePilot AI 🧾⚡

**AI-powered invoice and receipt processing for freelancers and small businesses.**

> Built for the Hacktoberfest 2026 Open-Source AI Challenge: Side Hustle

InvoicePilot AI extracts, validates, and organizes financial data from invoices and receipts using a **local open-weight AI model** (Gemma via Ollama). No paid API keys required — your documents stay on your machine.

---

## 🎯 Problem

Freelancers, consultants, and small business owners spend hours manually copying invoice data into spreadsheets. This is:
- **Repetitive** — every invoice has the same fields
- **Error-prone** — typos in amounts, wrong dates, missed entries
- **Time-consuming** — especially during tax season

## 💡 Solution

Upload a PDF, PNG, or JPG invoice → InvoicePilot extracts vendor, amounts, dates, line items, and categories using AI → Review and correct the results → Export clean data to CSV or Excel.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Multi-format upload** | PDF, PNG, JPG with drag-and-drop |
| 🤖 **AI extraction** | Gemma model via Ollama extracts structured data |
| ✅ **Validation** | Arithmetic checks, date validation, duplicate detection |
| ✏️ **Human review** | Edit any field before exporting |
| 📊 **Dashboard** | Expense trends, category breakdown, recent activity |
| 📈 **Reports** | Expense reports by category, date range, currency |
| 📥 **Export** | CSV and XLSX with formatted summary sheets |
| 🌙 **Dark mode** | Full light/dark theme support |
| 🔒 **Privacy** | Local inference, no external API calls |
| 🏷️ **Categorization** | AI-suggested expense categories with manual override |

---

## 🏗️ Architecture

```
┌─────────────────┐     REST API      ┌──────────────────┐
│   React + TS    │ ◄──────────────► │   FastAPI (Py)   │
│   Tailwind CSS  │                   │   SQLAlchemy     │
│   Recharts      │                   │   Pydantic       │
└─────────────────┘                   └────────┬─────────┘
                                               │
                           ┌───────────────────┼───────────────────┐
                           ▼                   ▼                   ▼
                    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                    │   PyMuPDF    │   │  Tesseract   │   │   Ollama     │
                    │  (PDF text)  │   │   (OCR)      │   │  (Gemma AI)  │
                    └──────────────┘   └──────────────┘   └──────────────┘
```

**Data flow**: Upload → Text Extraction (PyMuPDF/OCR) → AI Extraction (Gemma) → Validation → SQLite → Review → Export

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Ollama** ([download](https://ollama.com))
- **Tesseract OCR** ([install guide](https://github.com/tesseract-ocr/tesseract#installing-tesseract))

### 1. Clone & setup

```bash
git clone https://github.com/your-username/invoicepilot-ai.git
cd invoicepilot-ai
cp .env.example .env
```

### 2. Install & pull the AI model

```bash
# Install Ollama from https://ollama.com, then:
ollama pull gemma3:4b
ollama serve  # Keep this running
```

> **No GPU?** Gemma 3 4B runs on CPU too — just slower. Use `gemma3:1b` for faster CPU inference by setting `OLLAMA_MODEL=gemma3:1b` in your `.env`.

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:5173** — the frontend proxies API calls to the backend automatically.

### 5. Try the demo samples

We've included ready-to-test synthetic documents in the `demo_samples/` directory:
- `demo_samples/sample_invoice_01_acme_design.pdf` — Consulting services invoice (USD)
- `demo_samples/sample_invoice_02_global_tech_gst.pdf` — International GST invoice (INR)
- `demo_samples/sample_receipt_03_cloudstack_pro.png` — SaaS subscription receipt (USD)
- `demo_samples/sample_receipt_04_cafe_meeting.png` — Business meeting cafe receipt (USD)

Simply drag and drop any of these files into the **Upload** page to see InvoicePilot AI in action!

### 6. (Optional) Docker

```bash
# Make sure Ollama is running on your host
docker-compose up --build
```

---

## 📁 Project Structure

```
invoicepilot-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + all routes
│   │   ├── config.py            # Environment-based config
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py            # ORM models (Document, Invoice, LineItem)
│   │   ├── schemas.py           # Pydantic schemas + AI extraction schema
│   │   └── services/
│   │       ├── document_processor.py  # PDF + OCR extraction
│   │       ├── ai_extractor.py        # Ollama/Gemma integration
│   │       ├── validator.py           # Arithmetic + business rule checks
│   │       └── exporter.py            # CSV + XLSX export
│   ├── tests/
│   │   ├── test_main.py         # Unit + API tests (42 passing tests)
│   │   └── fixtures/            # Synthetic test fixtures
│   ├── requirements.txt
│   └── Dockerfile
├── demo_samples/                # Ready-to-upload sample PDFs & PNG receipts
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui.tsx           # Reusable UI components
│   │   │   └── Layout.tsx       # Sidebar + header layout
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Stats + charts
│   │   │   ├── Upload.tsx       # Drag-and-drop upload
│   │   │   ├── Invoices.tsx     # Searchable invoice list
│   │   │   ├── InvoiceDetail.tsx # Edit + review form
│   │   │   ├── Reports.tsx      # Expense reports
│   │   │   └── Settings.tsx     # AI config + privacy info
│   │   ├── lib/
│   │   │   ├── api.ts           # Typed API client
│   │   │   └── utils.ts         # Formatters + helpers
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   └── generate_sample_documents.py  # Synthetic document generator
├── docker-compose.yml
├── .env.example
├── LICENSE                      # MIT License
├── SUBMISSION.md                # Hacktoberfest 2026 submission writeup
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend health check |
| `GET` | `/api/health/ai` | AI model status + connection info |
| `POST` | `/api/documents/upload` | Upload files (multipart) |
| `GET` | `/api/documents` | List documents (with search/filter) |
| `GET` | `/api/documents/{id}` | Get document + extracted data |
| `PATCH` | `/api/documents/{id}` | Update invoice fields |
| `DELETE` | `/api/documents/{id}` | Delete document + data + file |
| `POST` | `/api/documents/{id}/process` | Trigger processing |
| `POST` | `/api/documents/{id}/retry` | Retry failed extraction |
| `GET` | `/api/dashboard/summary` | Dashboard statistics |
| `GET` | `/api/reports/expenses` | Expense report data |
| `GET` | `/api/exports/csv` | Export invoices as CSV |
| `GET` | `/api/exports/xlsx` | Export invoices as XLSX |

All endpoints return consistent JSON error responses: `{"detail": "error message"}`.

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests run **without Ollama** — AI calls are mocked. The test suite covers:
- AI response parsing (clean JSON, markdown fences, malformed output)
- Pydantic schema validation (negative amounts, invalid statuses)
- Arithmetic validation (subtotal + tax - discount = total)
- Date validation and currency code checks
- Duplicate invoice detection
- Formula injection protection for exports
- All API endpoints (CRUD, dashboard, exports)
- Multi-currency grouping

---

## ⚙️ Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gemma3:4b` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_TIMEOUT` | `120` | Max seconds per AI call |
| `OLLAMA_CONTEXT_LENGTH` | `8192` | Model context window |
| `MAX_FILE_SIZE_MB` | `20` | Upload size limit |
| `DEMO_MODE` | `false` | Run with simulated AI output |
| `ARITHMETIC_TOLERANCE` | `0.02` | Tolerance for rounding (2%) |
| `MAX_RETRIES` | `3` | AI extraction retry attempts |

---

## 🔒 Privacy & Security

- **Local inference**: Documents are processed by Ollama running on your machine
- **No external APIs**: No data is sent to OpenAI, Google Cloud, or any third party
- **Randomized filenames**: Uploaded files are stored with UUID filenames
- **Path traversal protection**: File paths are validated before read/write
- **Formula injection protection**: Export data is sanitized against spreadsheet injection
- **No telemetry**: No analytics, tracking, or usage data collection
- **Input validation**: File type, size, and content are validated server-side

> **Note**: Local inference does not automatically guarantee full offline operation. Tesseract OCR, fonts, and the application itself may require network access during setup. Configure dependencies appropriately for air-gapped environments.

---

## 🌐 Why Open-Weight AI?

InvoicePilot uses **Gemma** (Google's open-weight model) instead of proprietary APIs like GPT-4 or Claude:

| Aspect | Proprietary APIs | Open-Weight (Gemma + Ollama) |
|--------|-----------------|------------------------------|
| **Cost** | Per-token billing | Free after download |
| **Privacy** | Data sent to third party | Fully local processing |
| **Availability** | Requires internet | Works offline |
| **Customization** | Limited | Fine-tune for niche formats |
| **Vendor lock-in** | Yes | No |

This approach reduces dependence on paid inference services and supports local data processing. Users can also fine-tune or swap models for niche invoice formats (medical billing, international trade, etc.).

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to Ollama" | Ensure `ollama serve` is running |
| "Model not found" | Run `ollama pull gemma3:4b` |
| Slow extraction | Use a smaller model (`gemma3:1b`) or enable GPU |
| OCR failures | Install Tesseract: `apt install tesseract-ocr` (Linux) or `brew install tesseract` (Mac) |
| CORS errors | Check `CORS_ORIGINS` in `.env` matches your frontend URL |
| Import errors | Run `pip install -r requirements.txt` in the backend directory |

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

Built with ❤️ for Hacktoberfest 2026
