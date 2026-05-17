import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel
import json as _json
from sqlmodel import Session, select

import audit
import database
import models
from database import get_session
from evaluator import run_bidder_evaluation
from llm import extract_criteria_from_tender, compute_overall_verdict, get_provider, analyze_tender_full, extract_overview_section, extract_items_section, answer_question
from pdf_parser import extract_text
from report_generator import generate_report
from source_locator import locate_source, render_page_image, get_pdf_page_count

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Backend initialized with Gemini provider
app = FastAPI(title="TenderEval AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
        "http://localhost:3002", "http://127.0.0.1:3002"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    database.create_db_and_tables()


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    try:
        provider = get_provider()
        provider_name = provider.name
        ollama_ok = True
        ollama_error = None
    except Exception as e:
        provider_name = "unknown"
        ollama_ok = False
        ollama_error = str(e)

    # Check OCR availability
    from pdf_parser import FITZ_AVAILABLE, TESSERACT_AVAILABLE, PDFPLUMBER_AVAILABLE
    ocr_ready = FITZ_AVAILABLE and TESSERACT_AVAILABLE
    ocr_status = []
    if not FITZ_AVAILABLE:
        ocr_status.append("pymupdf not installed (pip install pymupdf)")
    if not TESSERACT_AVAILABLE:
        ocr_status.append(
            "pytesseract/Pillow not installed, or Tesseract OCR engine not found. "
            "Windows: https://github.com/UB-Mannheim/tesseract/wiki | Linux: sudo apt install tesseract-ocr"
        )
    if not PDFPLUMBER_AVAILABLE:
        ocr_status.append("pdfplumber not installed (pip install pdfplumber)")

    return {
        "status": "ok",
        "provider": provider_name,
        "ollama_ready": ollama_ok,
        "ollama_error": ollama_error,
        "ocr_ready": ocr_ready,
        "ocr_issues": ocr_status,
        "fitz_available": FITZ_AVAILABLE,
        "tesseract_available": TESSERACT_AVAILABLE,
    }


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def _process_tender_background(tender_id: int):
    """Extract criteria + full analysis from tender in background."""
    import json as _json
    with Session(database.engine) as session:
        tender = session.get(models.Tender, tender_id)
        if not tender:
            return
        try:
            # 1. Full structured analysis (Documents, Scope, Eligibility, Contacts, Criteria)
            # We consolidated these to reduce API requests and improve context
            analysis = analyze_tender_full(tender.raw_text)
            
            # 2. Extract criteria for bidder evaluation from multiple sections
            # We combine eligibility and scope items to form a comprehensive criteria list
            criteria_to_add = []
            
            # Combine from 'eligibility'
            for c in analysis.get("eligibility", []):
                criteria_to_add.append({"raw": c, "type": c.get("criterion_type") or "compliance"})
            
            # Combine from 'scope_of_work' - these are often technical specifications
            for s in analysis.get("scope_of_work", []):
                criteria_to_add.append({"raw": s, "type": "technical"})

            for item in criteria_to_add:
                c = item["raw"]
                ctype = item["type"]
                # Handle cases where LLM might return a string instead of a dict
                if isinstance(c, str):
                    desc = c
                    is_man = True
                    thresh = None
                    src_txt = ""
                    src_pg = None
                elif isinstance(c, dict):
                    desc = c.get("title", "")
                    summary = c.get("summary", "")
                    if summary:
                        desc = f"{desc}: {summary}" if desc else summary
                    
                    is_man = bool(c.get("is_mandatory", True))
                    thresh = c.get("threshold_value")
                    src_txt = str(c.get("source_text", ""))[:1000] # Increased limit
                    src_pg = c.get("source_page")
                else:
                    continue

                criterion = models.Criterion(
                    tender_id=tender_id,
                    criterion_type=ctype,
                    description=desc,
                    is_mandatory=is_man,
                    threshold_value=thresh,
                    extraction_confidence=0.9,
                    raw_source_text=src_txt,
                    source_page=src_pg,
                )
                session.add(criterion)

            # 3. Save full structured analysis
            existing = session.exec(
                select(models.TenderAnalysis).where(models.TenderAnalysis.tender_id == tender_id)
            ).first()
            if existing:
                existing.documents_json   = _json.dumps(analysis.get("documents", []))
                existing.scope_json       = _json.dumps(analysis.get("scope_of_work", []))
                existing.eligibility_json = _json.dumps(analysis.get("eligibility", []))
                existing.contacts_json    = _json.dumps(analysis.get("contacts", []))
                existing.overview_json    = _json.dumps(analysis.get("overview", {}))
                existing.items_json       = _json.dumps(analysis.get("items", []))
                session.add(existing)
            else:
                ta = models.TenderAnalysis(
                    tender_id=tender_id,
                    documents_json   = _json.dumps(analysis.get("documents", [])),
                    scope_json       = _json.dumps(analysis.get("scope_of_work", [])),
                    eligibility_json = _json.dumps(analysis.get("eligibility", [])),
                    contacts_json    = _json.dumps(analysis.get("contacts", [])),
                    overview_json    = _json.dumps(analysis.get("overview", {})),
                    items_json       = _json.dumps(analysis.get("items", [])),
                )
                session.add(ta)

            tender.status = "ready"
            session.add(tender)
            session.commit()
            logger.info(f"Tender {tender_id}: {len(criteria_to_add)} criteria + full analysis done (Consolidated)")
            audit.log_event(session, audit.EV_TENDER_ANALYZED, {
                "tender_id": tender_id, "tender_name": tender.name,
                "criteria_count": len(criteria_to_add),
                "sections": ["documents", "scope_of_work", "eligibility", "contacts", "items", "overview"],
            }, tender_id=tender_id)
        except Exception as e:
            logger.error(f"Tender {tender_id} processing failed: {e}")
            tender.status = "error"
            session.add(tender)
            session.commit()


def _reanalyze_background(tender_id: int):
    """Re-run only the structured analysis (keeps existing criteria). Used for re-analyse requests."""
    with Session(database.engine) as session:
        tender = session.get(models.Tender, tender_id)
        if not tender:
            return
        try:
            analysis = analyze_tender_full(tender.raw_text)
            ta = session.exec(
                select(models.TenderAnalysis).where(models.TenderAnalysis.tender_id == tender_id)
            ).first()
            if ta:
                ta.documents_json   = _json.dumps(analysis.get("documents", []))
                ta.scope_json       = _json.dumps(analysis.get("scope_of_work", []))
                ta.eligibility_json = _json.dumps(analysis.get("eligibility", []))
                ta.contacts_json    = _json.dumps(analysis.get("contacts", []))
                ta.overview_json    = _json.dumps(analysis.get("overview", {}))
                ta.items_json       = _json.dumps(analysis.get("items", []))
                session.add(ta)
            else:
                ta = models.TenderAnalysis(
                    tender_id=tender_id,
                    documents_json   = _json.dumps(analysis.get("documents", [])),
                    scope_json       = _json.dumps(analysis.get("scope_of_work", [])),
                    eligibility_json = _json.dumps(analysis.get("eligibility", [])),
                    contacts_json    = _json.dumps(analysis.get("contacts", [])),
                    overview_json    = _json.dumps(analysis.get("overview", {})),
                    items_json       = _json.dumps(analysis.get("items", [])),
                )
                session.add(ta)
            tender.status = "ready"
            session.add(tender)
            session.commit()
            logger.info(f"Tender {tender_id}: re-analysis complete")
            audit.log_event(session, audit.EV_TENDER_REANALYZED,
                {"tender_id": tender_id, "tender_name": tender.name},
                tender_id=tender_id)
        except Exception as e:
            logger.error(f"Tender {tender_id} re-analysis failed: {e}")
            tender.status = "ready"
            session.add(tender)
            session.commit()


def _process_bidder_background(bidder_id: int):
    """Evaluate bidder in background."""
    with Session(database.engine) as session:
        try:
            run_bidder_evaluation(bidder_id, session)
            bidder = session.get(models.Bidder, bidder_id)
            if bidder:
                audit.log_event(session, audit.EV_BIDDER_EVALUATED, {
                    "bidder_id": bidder_id, "bidder_name": bidder.name,
                    "verdict": bidder.overall_verdict, "risk_score": bidder.risk_score,
                }, tender_id=bidder.tender_id, bidder_id=bidder_id)
        except Exception as e:
            logger.error(f"Bidder {bidder_id} evaluation failed: {e}")
            bidder = session.get(models.Bidder, bidder_id)
            if bidder:
                bidder.status = "error"
                session.add(bidder)
                session.commit()


# ---------------------------------------------------------------------------
# Tenders
# ---------------------------------------------------------------------------

@app.post("/api/tenders/upload")
async def upload_tender(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        raw_text, method, page_count = extract_text(filepath)
    except Exception as e:
        raise HTTPException(422, f"Could not extract text from file: {e}")

    tender_name = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").title()
    tender = models.Tender(
        name=tender_name,
        filename=unique_name,
        raw_text=raw_text,
        extraction_method=method,
        page_count=page_count,
        status="processing",
    )
    session.add(tender)
    session.commit()
    session.refresh(tender)

    audit.log_event(session, audit.EV_TENDER_UPLOADED, {
        "tender_id": tender.id, "tender_name": tender.name,
        "filename": file.filename, "extraction_method": method,
        "page_count": page_count,
    }, tender_id=tender.id)

    background_tasks.add_task(_process_tender_background, tender.id)

    return {"tender_id": tender.id, "name": tender.name, "status": tender.status}


@app.get("/api/tenders")
def list_tenders(session: Session = Depends(get_session)):
    tenders = session.exec(select(models.Tender)).all()
    result = []
    for t in tenders:
        criterion_count = len(session.exec(
            select(models.Criterion).where(models.Criterion.tender_id == t.id)
        ).all())
        bidder_count = len(session.exec(
            select(models.Bidder).where(models.Bidder.tender_id == t.id)
        ).all())
        # Pull overview metadata from TenderAnalysis if available
        analysis = session.exec(
            select(models.TenderAnalysis).where(models.TenderAnalysis.tender_id == t.id)
        ).first()
        overview = {}
        items = []
        if analysis:
            if analysis.overview_json:
                try:
                    overview = _json.loads(analysis.overview_json)
                except Exception:
                    pass
            if analysis.items_json:
                try:
                    items = _json.loads(analysis.items_json)
                except Exception:
                    pass

        result.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "upload_time": t.upload_time.isoformat(),
            "criterion_count": criterion_count,
            "bidder_count": bidder_count,
            "extraction_method": t.extraction_method,
            "tender_type": overview.get("tender_type"),
            "bid_opening_date": overview.get("bid_opening_date"),
            "emd_fee_amount": overview.get("emd_fee_amount"),
            "work_description": overview.get("work_description"),
            "location": overview.get("location"),
            "total_quantity": overview.get("total_quantity") or (items[0].get("quantity") if items else None),
            "quantity_unit": overview.get("quantity_unit") or (items[0].get("quantity_unit") if items else None),
        })
    return result



@app.get("/api/tenders/{tender_id}")
def get_tender(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    criteria = session.exec(
        select(models.Criterion).where(models.Criterion.tender_id == tender_id)
    ).all()
    return {
        "id": tender.id,
        "name": tender.name,
        "status": tender.status,
        "upload_time": tender.upload_time.isoformat(),
        "extraction_method": tender.extraction_method,
        "criteria_count": len(criteria),
        "criteria": criteria,
    }

@app.get("/api/tenders/{tender_id}/file")
def get_tender_file(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    filepath = os.path.join(UPLOAD_DIR, tender.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found on disk")
    return FileResponse(filepath, media_type="application/pdf", content_disposition_type="inline")


@app.post("/api/tenders/{tender_id}/reextract-overview")
def reextract_overview(tender_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Re-run the overview extraction for an existing tender (useful after LLM prompt improvements)."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    background_tasks.add_task(_reextract_overview_background, tender_id)
    return {"status": "queued", "tender_id": tender_id}

def _reextract_overview_background(tender_id: int):
    """Re-extract just the overview section for a single tender."""
    with Session(database.engine) as session:
        tender = session.get(models.Tender, tender_id)
        if not tender:
            return
        try:
            from llm import extract_overview_section
            overview = extract_overview_section(tender.raw_text)
            ta = session.exec(
                select(models.TenderAnalysis).where(models.TenderAnalysis.tender_id == tender_id)
            ).first()
            if ta:
                ta.overview_json = _json.dumps(overview)
                session.add(ta)
                session.commit()
                logger.info(f"Re-extracted overview for tender {tender_id}: {overview.get('bid_opening_date')}")
        except Exception as e:
            logger.error(f"Overview re-extraction failed for tender {tender_id}: {e}")


@app.get("/api/tenders/{tender_id}/analysis")
def get_tender_analysis(tender_id: int, session: Session = Depends(get_session)):
    """Return the full structured AI analysis of the tender (4 sections)."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    ta = session.exec(
        select(models.TenderAnalysis).where(models.TenderAnalysis.tender_id == tender_id)
    ).first()
    if not ta:
        return {
            "tender_id": tender_id,
            "tender_status": tender.status,
            "overview": {},
            "documents": [],
            "scope_of_work": [],
            "eligibility": [],
            "contacts": [],
            "items": [],
            "generated_at": None,
        }
    return {
        "tender_id": tender_id,
        "tender_status": tender.status,
        "overview":      _json.loads(ta.overview_json    or "{}"),
        "documents":     _json.loads(ta.documents_json   or "[]"),
        "scope_of_work": _json.loads(ta.scope_json       or "[]"),
        "eligibility":   _json.loads(ta.eligibility_json or "[]"),
        "contacts":      _json.loads(ta.contacts_json    or "[]"),
        "items":         _json.loads(ta.items_json       or "[]"),
        "generated_at":  ta.generated_at.isoformat() if ta.generated_at else None,
    }


# ---------------------------------------------------------------------------
# Source provenance endpoints
# ---------------------------------------------------------------------------

@app.get("/api/tenders/{tender_id}/page/{page_num}/image")
def get_page_image(
    tender_id: int,
    page_num: int,
    highlight_x0: Optional[float] = None,
    highlight_y0: Optional[float] = None,
    highlight_x1: Optional[float] = None,
    highlight_y1: Optional[float] = None,
    session: Session = Depends(get_session),
):
    """Render a PDF page as a PNG image with optional highlight rectangle."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")

    filepath = os.path.join(UPLOAD_DIR, tender.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "PDF file not found on disk")

    highlight_bbox = None
    if all(v is not None for v in [highlight_x0, highlight_y0, highlight_x1, highlight_y1]):
        highlight_bbox = {"x0": highlight_x0, "y0": highlight_y0, "x1": highlight_x1, "y1": highlight_y1}

    try:
        img_bytes = render_page_image(filepath, page_num, zoom=2.0, highlight_bbox=highlight_bbox)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to render page: {e}")

    return Response(content=img_bytes, media_type="image/png")


class SourceProofRequest(BaseModel):
    source_text: str
    page_hint: Optional[int] = None


@app.post("/api/tenders/{tender_id}/source-proof")
def get_source_proof(
    tender_id: int,
    body: SourceProofRequest,
    session: Session = Depends(get_session),
):
    """Locate source text in the PDF and return page + bounding box for highlighting."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")

    filepath = os.path.join(UPLOAD_DIR, tender.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "PDF file not found on disk")

    result = locate_source(filepath, body.source_text, page_hint=body.page_hint)

    # Build image URL with highlight params
    image_url = f"/api/tenders/{tender_id}/page/{result['page']}/image"
    if result.get("bbox"):
        b = result["bbox"]
        image_url += f"?highlight_x0={b['x0']}&highlight_y0={b['y0']}&highlight_x1={b['x1']}&highlight_y1={b['y1']}"

    return {
        "page": result["page"],
        "bbox": result.get("bbox"),
        "confidence": result["confidence"],
        "found": result["found"],
        "image_url": image_url,
        "page_count": tender.page_count,
    }


@app.post("/api/tenders/{tender_id}/reanalyze")
async def reanalyze_tender(
    tender_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Re-run full AI analysis (documents, scope, eligibility, contacts, overview, items).
    Existing evaluation criteria and bidder evaluations are preserved."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    if tender.status == "processing":
        raise HTTPException(400, "Tender is already being processed")

    tender.status = "processing"
    session.add(tender)
    session.commit()

    background_tasks.add_task(_reanalyze_background, tender_id)
    return {"status": "reanalyzing", "tender_id": tender_id}


@app.get("/api/tenders/{tender_id}/status")
def get_tender_status(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    bidders = session.exec(
        select(models.Bidder).where(models.Bidder.tender_id == tender_id)
    ).all()
    criterion_count = len(session.exec(
        select(models.Criterion).where(models.Criterion.tender_id == tender_id)
    ).all())
    return {
        "tender_id": tender_id,
        "tender_status": tender.status,
        "criterion_count": criterion_count,
        "bidders": [
            {
                "id": b.id,
                "name": b.name,
                "status": b.status,
                "overall_verdict": b.overall_verdict,
            }
            for b in bidders
        ],
    }


# ---------------------------------------------------------------------------
# Bidders
# ---------------------------------------------------------------------------

@app.post("/api/tenders/{tender_id}/bidders/upload")
async def upload_bidder(
    tender_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    if tender.status != "ready":
        raise HTTPException(400, "Tender criteria not yet extracted. Wait for tender status=ready.")

    if not file.filename:
        raise HTTPException(400, "No file provided")

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        raw_text, method, _ = extract_text(filepath)
    except Exception as e:
        raise HTTPException(422, f"Could not extract text: {e}")

    bidder_name = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").title()
    bidder = models.Bidder(
        tender_id=tender_id,
        name=bidder_name,
        filename=unique_name,
        raw_text=raw_text,
        extraction_method=method,
        status="processing",
    )
    session.add(bidder)
    session.commit()
    session.refresh(bidder)

    audit.log_event(session, audit.EV_BIDDER_UPLOADED, {
        "bidder_id": bidder.id, "bidder_name": bidder.name,
        "filename": file.filename, "extraction_method": method,
    }, tender_id=tender.id, bidder_id=bidder.id)

    background_tasks.add_task(_process_bidder_background, bidder.id)

    return {"bidder_id": bidder.id, "name": bidder.name, "status": bidder.status}


@app.get("/api/tenders/{tender_id}/bidders")
def list_bidders(tender_id: int, session: Session = Depends(get_session)):
    bidders = session.exec(
        select(models.Bidder).where(models.Bidder.tender_id == tender_id)
    ).all()
    result = []
    for b in bidders:
        evals = session.exec(
            select(models.CriterionEvaluation).where(
                models.CriterionEvaluation.bidder_id == b.id
            )
        ).all()
        total = len(evals)
        passed = sum(1 for e in evals if (e.human_verdict or e.verdict) == "pass")
        failed = sum(1 for e in evals if (e.human_verdict or e.verdict) == "fail")
        review = total - passed - failed
        match_score = round(passed / total * 100) if total > 0 else None
        result.append({
            "id": b.id,
            "name": b.name,
            "status": b.status,
            "overall_verdict": b.overall_verdict,
            "overall_reasoning": b.overall_reasoning,
            "upload_time": b.upload_time.isoformat(),
            "extraction_method": b.extraction_method,
            "criteria_total": total,
            "criteria_pass": passed,
            "criteria_fail": failed,
            "criteria_review": review,
            "match_score": match_score,
            "risk_score": b.risk_score,
        })
    return result


@app.get("/api/tenders/{tender_id}/bidders/{bidder_id}")
def get_bidder(tender_id: int, bidder_id: int, session: Session = Depends(get_session)):
    bidder = session.get(models.Bidder, bidder_id)
    if not bidder or bidder.tender_id != tender_id:
        raise HTTPException(404, "Bidder not found")

    criteria = session.exec(
        select(models.Criterion).where(models.Criterion.tender_id == tender_id)
    ).all()
    evaluations = session.exec(
        select(models.CriterionEvaluation).where(
            models.CriterionEvaluation.bidder_id == bidder_id
        )
    ).all()
    eval_by_criterion = {e.criterion_id: e for e in evaluations}

    criteria_evals = []
    for c in criteria:
        e = eval_by_criterion.get(c.id)
        criteria_evals.append({
            "criterion": {
                "id": c.id,
                "criterion_type": c.criterion_type,
                "description": c.description,
                "is_mandatory": c.is_mandatory,
                "threshold_value": c.threshold_value,
                "extraction_confidence": c.extraction_confidence,
                "raw_source_text": c.raw_source_text,
            },
            "evaluation": {
                "id": e.id if e else None,
                "verdict": e.verdict if e else None,
                "confidence": e.confidence if e else None,
                "extracted_value": e.extracted_value if e else None,
                "evidence_snippet": e.evidence_snippet if e else None,
                "reasoning": e.reasoning if e else None,
                "evaluated_at": e.evaluated_at.isoformat() if e else None,
                "human_verdict": e.human_verdict if e else None,
                "human_note": e.human_note if e else None,
                "reviewed_by": e.reviewed_by if e else None,
                "reviewed_at": e.reviewed_at.isoformat() if (e and e.reviewed_at) else None,
            } if e else None,
        })

    return {
        "id": bidder.id,
        "tender_id": bidder.tender_id,
        "name": bidder.name,
        "status": bidder.status,
        "overall_verdict": bidder.overall_verdict,
        "overall_reasoning": bidder.overall_reasoning,
        "upload_time": bidder.upload_time.isoformat(),
        "extraction_method": bidder.extraction_method,
        "risk_score": bidder.risk_score,
        "criteria_evaluations": criteria_evals,
    }

@app.get("/api/tenders/{tender_id}/bidders/{bidder_id}/file")
def get_bidder_file(tender_id: int, bidder_id: int, session: Session = Depends(get_session)):
    bidder = session.get(models.Bidder, bidder_id)
    if not bidder or bidder.tender_id != tender_id:
        raise HTTPException(404, "Bidder not found")
    filepath = os.path.join(UPLOAD_DIR, bidder.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found on disk")
    return FileResponse(filepath, media_type="application/pdf", content_disposition_type="inline")



# ---------------------------------------------------------------------------
# Human review
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    human_verdict: str  # pass | fail | needs_review
    human_note: Optional[str] = None
    reviewed_by: Optional[str] = "Reviewer"


@app.patch("/api/evaluations/{evaluation_id}/review")
def review_evaluation(
    evaluation_id: int,
    body: ReviewRequest,
    session: Session = Depends(get_session),
):
    eval_rec = session.get(models.CriterionEvaluation, evaluation_id)
    if not eval_rec:
        raise HTTPException(404, "Evaluation not found")

    if body.human_verdict not in ("pass", "fail", "needs_review"):
        raise HTTPException(400, "human_verdict must be pass, fail, or needs_review")

    eval_rec.human_verdict = body.human_verdict
    eval_rec.human_note = body.human_note
    eval_rec.reviewed_by = body.reviewed_by
    eval_rec.reviewed_at = datetime.utcnow()
    # A human override implies 100% confidence in the new verdict
    eval_rec.confidence = 1.0
    session.add(eval_rec)
    session.commit()

    # Recompute overall bidder verdict
    bidder = session.get(models.Bidder, eval_rec.bidder_id)
    if bidder:
        all_evals = session.exec(
            select(models.CriterionEvaluation).where(
                models.CriterionEvaluation.bidder_id == bidder.id
            )
        ).all()
        criteria = session.exec(
            select(models.Criterion).where(models.Criterion.tender_id == bidder.tender_id)
        ).all()
        eval_dicts = [
            {
                "verdict": e.verdict,
                "human_verdict": e.human_verdict,
            }
            for e in all_evals
        ]
        criteria_dicts = [{"is_mandatory": c.is_mandatory, "description": c.description} for c in criteria]
        new_verdict, new_reasoning = compute_overall_verdict(eval_dicts, criteria_dicts)
        bidder.overall_verdict = new_verdict
        bidder.overall_reasoning = new_reasoning
        session.add(bidder)
        session.commit()

        audit.log_event(session, audit.EV_VERDICT_OVERRIDDEN, {
            "evaluation_id": evaluation_id, "criterion_id": eval_rec.criterion_id,
            "bidder_id": bidder.id, "bidder_name": bidder.name,
            "human_verdict": body.human_verdict, "human_note": body.human_note,
            "reviewed_by": body.reviewed_by, "updated_overall_verdict": new_verdict
        }, tender_id=bidder.tender_id, bidder_id=bidder.id, evaluation_id=evaluation_id, actor=body.reviewed_by or "Reviewer", actor_type="human")

    return {
        "evaluation_id": evaluation_id,
        "human_verdict": eval_rec.human_verdict,
        "updated_overall_verdict": bidder.overall_verdict if bidder else None,
    }

# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

@app.get("/api/tenders/{tender_id}/audit")
def get_audit_trail(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
        
    events = session.exec(
        select(models.AuditLog).where(models.AuditLog.tender_id == tender_id).order_by(models.AuditLog.id)
    ).all()
    
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor": e.actor,
            "actor_type": e.actor_type,
            "payload": _json.loads(e.payload_json),
            "timestamp": e.timestamp.isoformat(),
            "hash": e.hash,
        }
        for e in events
    ]

@app.get("/api/tenders/{tender_id}/audit/verify")
def verify_audit_trail(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
        
    return audit.verify_chain(session, tender_id)


# ---------------------------------------------------------------------------
# Report export
# ---------------------------------------------------------------------------

@app.get("/api/tenders/{tender_id}/report")
def export_report(tender_id: int, session: Session = Depends(get_session)):
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")

    criteria = session.exec(
        select(models.Criterion).where(models.Criterion.tender_id == tender_id)
    ).all()
    bidders = session.exec(
        select(models.Bidder).where(models.Bidder.tender_id == tender_id)
    ).all()

    evaluations_by_bidder: dict[int, list[dict]] = {}
    for bidder in bidders:
        evals = session.exec(
            select(models.CriterionEvaluation).where(
                models.CriterionEvaluation.bidder_id == bidder.id
            )
        ).all()
        evaluations_by_bidder[bidder.id] = [
            {
                "id": e.id,
                "criterion_id": e.criterion_id,
                "bidder_id": e.bidder_id,
                "verdict": e.verdict,
                "confidence": e.confidence,
                "extracted_value": e.extracted_value,
                "evidence_snippet": e.evidence_snippet,
                "reasoning": e.reasoning,
                "evaluated_at": e.evaluated_at,
                "human_verdict": e.human_verdict,
                "human_note": e.human_note,
                "reviewed_by": e.reviewed_by,
                "reviewed_at": e.reviewed_at,
            }
            for e in evals
        ]

    tender_dict = {
        "id": tender.id,
        "name": tender.name,
        "upload_time": tender.upload_time,
        "status": tender.status,
    }
    criteria_dicts = [
        {
            "id": c.id,
            "criterion_type": c.criterion_type,
            "description": c.description,
            "is_mandatory": c.is_mandatory,
            "threshold_value": c.threshold_value,
            "extraction_confidence": c.extraction_confidence,
        }
        for c in criteria
    ]
    bidder_dicts = [
        {
            "id": b.id,
            "name": b.name,
            "overall_verdict": b.overall_verdict,
            "overall_reasoning": b.overall_reasoning,
            "status": b.status,
        }
        for b in bidders
    ]

    pdf_bytes = generate_report(tender_dict, criteria_dicts, bidder_dicts, evaluations_by_bidder)
    safe_name = tender.name.replace(" ", "_")[:40]

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="TenderEval_{safe_name}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Compare view data
# ---------------------------------------------------------------------------

@app.get("/api/tenders/{tender_id}/compare")
def get_compare_data(tender_id: int, session: Session = Depends(get_session)):
    """Returns all data needed for the matrix comparison view."""
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")

    criteria = session.exec(
        select(models.Criterion).where(models.Criterion.tender_id == tender_id)
    ).all()
    bidders = session.exec(
        select(models.Bidder).where(models.Bidder.tender_id == tender_id)
    ).all()

    matrix = []
    for bidder in bidders:
        evals = session.exec(
            select(models.CriterionEvaluation).where(
                models.CriterionEvaluation.bidder_id == bidder.id
            )
        ).all()
        eval_by_criterion = {e.criterion_id: e for e in evals}
        row = {
            "bidder_id": bidder.id,
            "bidder_name": bidder.name,
            "overall_verdict": bidder.overall_verdict,
            "status": bidder.status,
            "criteria": {},
        }
        for c in criteria:
            e = eval_by_criterion.get(c.id)
            row["criteria"][c.id] = {
                "verdict": e.verdict if e else None,
                "human_verdict": e.human_verdict if e else None,
                "confidence": e.confidence if e else None,
                "evaluation_id": e.id if e else None,
            }
        
        # Add risk score to the row
        row["risk_score"] = bidder.risk_score
        
        matrix.append(row)

    return {
        "tender": {"id": tender.id, "name": tender.name, "status": tender.status},
        "criteria": [
            {
                "id": c.id,
                "description": c.description,
                "criterion_type": c.criterion_type,
                "is_mandatory": c.is_mandatory,
                "threshold_value": c.threshold_value,
            }
            for c in criteria
        ],
        "matrix": matrix,
    }


# ---------------------------------------------------------------------------
# Follow-up Q&A
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


@app.post("/api/tenders/{tender_id}/ask")
def ask_tender(
    tender_id: int,
    body: AskRequest,
    session: Session = Depends(get_session),
):
    """Answer a free-form question about a tender document using the LLM."""
    if not body.question or not body.question.strip():
        raise HTTPException(400, "question must not be empty")
    tender = session.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(404, "Tender not found")
    if tender.status != "ready":
        raise HTTPException(400, "Tender is still processing — please try again shortly")
    try:
        answer = answer_question(tender.raw_text, body.question.strip())
        return {"question": body.question.strip(), "answer": answer}
    except Exception as e:
        raise HTTPException(503, f"LLM error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
