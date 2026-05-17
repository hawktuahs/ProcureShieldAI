# ProcureShield AI

**AI-Powered Tender Evaluation and Eligibility Analysis for Government Procurement**
AI for Bharat Hackathon 2025

---

## What It Does

Upload a government tender PDF → the system automatically extracts all eligibility criteria, scope of work, required documents, contacts, and itemised BOQ using a local LLM. Upload bidder submission PDFs → the system evaluates each bidder criterion-by-criterion, assigns pass/fail/needs-review verdicts with evidence citations and confidence scores, and produces a downloadable PDF audit report. Human reviewers can override any AI verdict through a review panel — overrides are cryptographically logged and auto-recalculate the overall verdict.

---

## Architecture

```
Frontend (Next.js 14)  ←→  Backend (FastAPI)  ←→  Ollama (local LLM)
                                   ↓
                             SQLite (SQLModel)
```

### Key Technical Features

| Feature | Description |
|---------|-------------|
| **Markdown Table Parsing** | pdfplumber converts PDF tables into Markdown format so the local LLM can accurately read structured data (specs, BOQ, checklists) |
| **Multi-Pass Extraction** | Long documents are split on page boundaries into optimal 6k-char chunks with overlap — ensuring nothing is missed |
| **Hallucination Guards** | All prompts enforce strict `--- PAGE N ---` marker-based citation with verbatim source text — no guessing |
| **Dynamic Confidence Scoring** | Bidder evaluation uses a calibrated 0.0–1.0 scale based on evidence quality, not a flat default |
| **Human-in-the-Loop** | Manual overrides lock confidence to 100% and are visually distinguished with blue "Reviewed" badges |
| **Cryptographic Audit Trail** | SHA-256 hashed, immutable event log for every AI decision and human override |

### LLM Provider

The system defaults to **Ollama (llama3.1:8b)** — completely free and local. To swap to a paid API, set the `LLM_PROVIDER` environment variable before starting the backend:

| Provider | Env vars needed |
|----------|----------------|
| Ollama (default) | `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=llama3.1:8b` |
| Google Gemini | `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=AIza...` |
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-...`, `OPENAI_MODEL=gpt-4o` |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) installed and running
- **Tesseract OCR** (required for scanned PDFs like most real government tenders):
  - **Windows**: Download installer from https://github.com/UB-Mannheim/tesseract/wiki — install to the default path (`C:\Program Files\Tesseract-OCR\`) and the app auto-detects it
  - **Linux**: `sudo apt install tesseract-ocr`
  - **macOS**: `brew install tesseract`

> **Note**: `poppler` / `pdf2image` are no longer required. PyMuPDF (`pymupdf`) handles PDF rendering internally with no system binaries needed.

---

## Quick Start

### Option 1: One-Click Launch (Windows)

```
Double-click start.bat
```

This automatically checks Ollama, starts the backend, builds and starts the frontend, and opens the browser.

### Option 2: Manual Setup

#### 1. Pull the Ollama model

```bash
ollama serve          # start Ollama (keep this terminal open)
ollama pull llama3.1:8b
```

#### 2. Backend setup

```bash
cd backend
pip install -r requirements.txt
python main.py        # runs on http://localhost:8000
```

#### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev           # runs on http://localhost:3000
```

---

## Demo Flow (for judges)

1. Open `http://localhost:3000`
2. Click **Upload Tender** → upload any government tender PDF
3. Wait ~30–90 seconds → criteria extracted, status turns green
4. Click **View Tender** → see the split workspace (PDF viewer + AI analysis)
5. Browse tabs: **Overview**, **Documents**, **Items & Qty**, **Scope of Work**, **Eligibility**, **Contacts**
6. Click any **👁 pg.N** badge → PDF viewer jumps to the source page with the relevant quote highlighted
7. Use **Ask AI** tab → ask natural language questions about the tender (e.g., "When is the last day to file for bid?")
8. Scroll down → **Upload Bidder Document** → evaluation runs automatically
9. Click **View Full Audit Matrix** on a bidder card → see criterion-by-criterion verdicts with evidence
10. Click **Review** on any criterion → override verdict → confidence auto-locks to 100%, blue "Reviewed" badge appears
11. Click **Compare All** from the tender page → charts + matrix view comparing all bidders
12. Go to **Reports** → download the full comparative evaluation as a professional PDF

---

## AI Analysis Sections

| Section | What It Extracts |
|---------|-----------------|
| **Overview** | Tender title, type, published date, bid deadline, EMD amount, location, evaluation method |
| **Documents** | All physical/digital certificates, forms, and declarations the bidder must submit |
| **Items & Qty** | Itemised Bill of Quantities with specs, delivery location, and quantities |
| **Scope of Work** | What the bidder must supply/deliver/install, with technical requirements |
| **Eligibility** | Financial, technical, compliance criteria (including clauses like Option/Denial) with thresholds |
| **Contacts** | Tender issuing authority, contact details, consignee addresses |

---

## Confidence Thresholds

| Confidence | Behaviour |
|-----------|-----------|
| ≥ 75% | AI commits to pass/fail verdict |
| 40–75% | Escalated to `needs_review` regardless of pass/fail |
| < 40% | `needs_review` with "low confidence" flag |

Configurable via environment variables:
- `CONFIDENCE_REVIEW_THRESHOLD` (default: `0.75`)
- `CONFIDENCE_LOW_THRESHOLD` (default: `0.40`)

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | LLM provider status + OCR availability |
| POST | `/api/tenders/upload` | Upload tender PDF |
| GET | `/api/tenders` | List all tenders with metadata |
| GET | `/api/tenders/{id}` | Tender + criteria + analysis |
| GET | `/api/tenders/{id}/status` | Processing status (for polling) |
| POST | `/api/tenders/{id}/reanalyze` | Re-run AI analysis |
| POST | `/api/tenders/{id}/reextract-overview` | Re-extract overview section |
| POST | `/api/tenders/{id}/source-proof` | Get source proof for a page |
| POST | `/api/tenders/{id}/bidders/upload` | Upload bidder PDF |
| GET | `/api/tenders/{id}/bidders` | List bidders |
| GET | `/api/tenders/{id}/bidders/{bid_id}` | Bidder + evaluations |
| PATCH | `/api/evaluations/{id}/review` | Submit human review |
| GET | `/api/tenders/{id}/report` | Download PDF report |
| GET | `/api/tenders/{id}/compare` | Matrix comparison data |
| POST | `/api/tenders/{id}/ask` | Ask a question about the tender |
| GET | `/api/tenders/{id}/audit` | View audit trail |

---

## Project Structure

```
ProcureShieldAI/
├── backend/
│   ├── main.py              # FastAPI routes + background tasks
│   ├── models.py            # SQLModel DB models
│   ├── database.py          # DB setup
│   ├── pdf_parser.py        # Text extraction (pdfplumber → PyMuPDF → OCR)
│   ├── llm.py               # Pluggable LLM layer + all extraction prompts
│   ├── evaluator.py         # Criterion evaluation pipeline
│   ├── source_locator.py    # Source proof locator for PDF provenance
│   ├── audit.py             # SHA-256 cryptographic audit trail
│   ├── report_generator.py  # ReportLab PDF export
│   ├── requirements.txt
│   └── uploads/             # Uploaded files
├── frontend/
│   ├── app/
│   │   ├── page.tsx                               # Dashboard
│   │   ├── tender/[id]/page.tsx                   # Tender detail + split workspace
│   │   ├── tender/[id]/compare/page.tsx           # Matrix comparison + charts
│   │   ├── evaluation/[tenderId]/[bidderId]/page.tsx  # Bidder evaluation
│   │   ├── reports/page.tsx                       # Reports download page
│   │   ├── settings/page.tsx                      # LLM provider configuration
│   │   └── help/page.tsx                          # Platform guide
│   ├── components/
│   │   ├── TenderAnalysisView.tsx   # Full 8-tab analysis view
│   │   ├── SplitWorkspace.tsx       # PDF viewer + analysis side-by-side
│   │   ├── SourceProofModal.tsx     # Source evidence overlay
│   │   ├── FileUpload.tsx           # Drag-and-drop upload
│   │   ├── CriterionCard.tsx        # Criterion display with confidence
│   │   ├── BidderSummaryCard.tsx    # Bidder verdict card
│   │   ├── ReviewPanel.tsx          # Human override panel
│   │   ├── AuditLogViewer.tsx       # Audit trail viewer
│   │   ├── SidebarNav.tsx           # Navigation sidebar
│   │   ├── OllamaAlert.tsx          # LLM health status
│   │   ├── VerdictBadge.tsx         # Pass/Fail/Review badges
│   │   └── ConfidenceBar.tsx        # Visual confidence indicator
│   └── lib/api.ts                   # API client + TypeScript types
├── sample_data/
│   └── create_sample_pdfs.py
├── start.bat                        # One-click Windows launcher
└── README.md
```

---

## Non-Negotiables (Per Problem Statement)

- **Every verdict is explainable**: which criterion, which document text, what value, why the decision
- **No silent disqualification**: ambiguous or low-confidence cases always go to `needs_review`
- **Scanned PDF support**: pdfplumber first with Markdown table conversion; automatic OCR fallback via Tesseract
- **Full audit trail**: exported PDF logs every AI decision + any human override with SHA-256 hash and timestamp
- **Human-in-the-loop**: reviewer can override any verdict; overall verdict auto-recalculates; confidence locks to 100%

---

Built for AI for Bharat Hackathon 2025 — Government Procurement Challenge
