# ProcureShield AI

**AI-Based Tender Evaluation and Eligibility Analysis for Government Procurement**
CRPF / AI for Bharat Hackathon 2024

---

## What It Does

Upload a government tender PDF → the system automatically extracts all eligibility criteria using a local LLM. Upload bidder submission PDFs → the system evaluates each bidder criterion-by-criterion, assigns pass/fail/needs-review verdicts with evidence citations, and produces a downloadable PDF audit report. Human reviewers can override any AI verdict through a review panel.

---

## Architecture

```
Frontend (Next.js 14)  ←→  Backend (FastAPI)  ←→  Ollama (local LLM)
                                   ↓
                             SQLite (SQLModel)
```

### LLM Provider

The system defaults to **Ollama (llama3.1:8b)** — completely free and local. To swap to a paid API, set the `LLM_PROVIDER` environment variable before starting the backend:

| Provider | Env vars needed |
|----------|----------------|
| Ollama (default) | `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=llama3.1:8b` |
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=sk-...`, `OPENAI_MODEL=gpt-4o` |
| Anthropic | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=sk-ant-...`, `ANTHROPIC_MODEL=claude-sonnet-4-6` |

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

## Setup

### 1. Pull the Ollama model

```bash
ollama serve          # start Ollama (keep this terminal open)
ollama pull llama3.1:8b
```

### 2. Backend setup

```bash
cd tender-eval/backend
pip install -r requirements.txt
python main.py        # runs on http://localhost:8000
```

### 3. Frontend setup

```bash
cd tender-eval/frontend
npm install
npm run dev           # runs on http://localhost:3000
```

### 4. Generate sample PDFs (for demo)

```bash
cd tender-eval
pip install reportlab   # if not already installed
python sample_data/create_sample_pdfs.py
```

This creates:
- `sample_data/sample_tender.pdf` — CRPF construction tender with 8 criteria
- `sample_data/sample_bidder_1.pdf` — Clearly eligible (Sharma Construction)
- `sample_data/sample_bidder_2.pdf` — Not eligible (fails turnover, ISO, EPF/ESIC)
- `sample_data/sample_bidder_3.pdf` — Needs review (ambiguous turnover, expiring cert, CPWD class issue)

---

## Demo Flow (for judges)

1. Open `http://localhost:3000`
2. Click **Upload New Tender** → upload `sample_tender.pdf`
3. Wait ~30 seconds → "8 criteria extracted" appears
4. Click **View Tender** → see criteria grouped by type with confidence scores
5. Upload `sample_bidder_1.pdf` → wait → **Eligible** green badge
6. Upload `sample_bidder_2.pdf` → wait → **Not Eligible** red badge
7. Upload `sample_bidder_3.pdf` → wait → **Needs Review** amber badge
8. Click **View** on bidder 3 → criterion-by-criterion table with reasoning and evidence
9. Click **Review** on an ambiguous criterion → override verdict → badge updates instantly
10. Click **Compare All** → full matrix view of all bidders vs all criteria
11. Click **Export Full Report (PDF)** → download a professional PDF with complete audit trail

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
| GET | `/api/health` | LLM provider status |
| POST | `/api/tenders/upload` | Upload tender PDF |
| GET | `/api/tenders` | List all tenders |
| GET | `/api/tenders/{id}` | Tender + criteria |
| GET | `/api/tenders/{id}/status` | Processing status (for polling) |
| POST | `/api/tenders/{id}/bidders/upload` | Upload bidder PDF |
| GET | `/api/tenders/{id}/bidders` | List bidders |
| GET | `/api/tenders/{id}/bidders/{bid_id}` | Bidder + evaluations |
| PATCH | `/api/evaluations/{id}/review` | Submit human review |
| GET | `/api/tenders/{id}/report` | Download PDF report |
| GET | `/api/tenders/{id}/compare` | Matrix comparison data |

---

## Project Structure

```
tender-eval/
├── backend/
│   ├── main.py              # FastAPI routes
│   ├── models.py            # SQLModel DB models
│   ├── database.py          # DB setup
│   ├── pdf_parser.py        # Text extraction (digital + OCR)
│   ├── llm.py               # Pluggable LLM layer (Ollama / OpenAI / Anthropic)
│   ├── evaluator.py         # Criterion evaluation pipeline
│   ├── report_generator.py  # ReportLab PDF export
│   ├── requirements.txt
│   └── uploads/             # Uploaded files
├── frontend/
│   ├── app/
│   │   ├── page.tsx                               # Dashboard
│   │   ├── tender/[id]/page.tsx                   # Tender detail + bidder upload
│   │   ├── tender/[id]/compare/page.tsx           # Matrix comparison
│   │   └── evaluation/[tenderId]/[bidderId]/page.tsx  # Bidder evaluation
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── CriterionCard.tsx
│   │   ├── BidderSummaryCard.tsx
│   │   ├── VerdictBadge.tsx
│   │   ├── ConfidenceBar.tsx
│   │   ├── ReviewPanel.tsx
│   │   └── OllamaAlert.tsx
│   └── lib/api.ts
└── sample_data/
    ├── sample_tender.txt / .pdf
    ├── sample_bidder_1.txt / .pdf
    ├── sample_bidder_2.txt / .pdf
    ├── sample_bidder_3.txt / .pdf
    └── create_sample_pdfs.py
```

---

## Non-Negotiables (Per Problem Statement)

- **Every verdict is explainable**: which criterion, which document text, what value, why the decision
- **No silent disqualification**: ambiguous or low-confidence cases always go to `needs_review`
- **Scanned PDF support**: pdfplumber first; automatic OCR fallback via Tesseract
- **Full audit trail**: exported PDF logs every AI decision + any human override with timestamp
- **Human-in-the-loop**: reviewer can override any verdict; overall verdict auto-recalculates

---

Built for AI for Bharat Hackathon 2024 — CRPF Procurement Challenge
