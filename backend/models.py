from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Tender(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    filename: str
    raw_text: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = "processing"  # processing | ready | error
    extraction_method: str = "digital"  # digital | ocr
    page_count: int = 0  # total pages in the PDF


class Criterion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tender_id: int = Field(foreign_key="tender.id")
    criterion_type: str  # financial | technical | compliance | documentation
    description: str
    is_mandatory: bool = True
    threshold_value: Optional[str] = None
    extraction_confidence: float
    raw_source_text: str
    source_page: Optional[int] = None           # 1-indexed page number where criterion was found
    source_bbox_json: Optional[str] = None      # JSON: {"x0":..., "y0":..., "x1":..., "y1":...}


class Bidder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tender_id: int = Field(foreign_key="tender.id")
    name: str
    filename: str
    raw_text: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = "processing"  # processing | evaluated | error
    overall_verdict: Optional[str] = None  # eligible | not_eligible | needs_review
    overall_reasoning: Optional[str] = None
    extraction_method: str = "digital"  # digital | ocr
    risk_score: Optional[int] = None  # 0-100, higher = more risky


class TenderAnalysis(SQLModel, table=True):
    """Stores the full structured AI analysis of a tender document."""
    id: Optional[int] = Field(default=None, primary_key=True)
    tender_id: int = Field(foreign_key="tender.id", unique=True)
    documents_json: Optional[str] = None   # JSON: submission checklist
    scope_json: Optional[str] = None       # JSON: scope of work items
    eligibility_json: Optional[str] = None # JSON: eligibility requirements
    contacts_json: Optional[str] = None    # JSON: contact details
    overview_json: Optional[str] = None    # JSON: tender overview / metadata
    items_json: Optional[str] = None       # JSON: items & quantities
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CriterionEvaluation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bidder_id: int = Field(foreign_key="bidder.id")
    criterion_id: int = Field(foreign_key="criterion.id")
    verdict: str  # pass | fail | needs_review
    confidence: float
    extracted_value: Optional[str] = None
    evidence_snippet: Optional[str] = None
    reasoning: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    # Human review fields
    human_verdict: Optional[str] = None
    human_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class AuditLog(SQLModel, table=True):
    """
    Append-only, SHA-256 hash-chained audit event log.
    Every state change produces a new row where hash = SHA256(event_data + previous_hash).
    This creates a tamper-evident chain that can be verified on-demand.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    tender_id: Optional[int] = Field(default=None, foreign_key="tender.id")
    bidder_id: Optional[int] = Field(default=None, foreign_key="bidder.id")
    evaluation_id: Optional[int] = None  # not a FK to avoid circular deps
    event_type: str  # TENDER_UPLOADED | TENDER_ANALYZED | BIDDER_UPLOADED | BIDDER_EVALUATED | VERDICT_OVERRIDDEN | REANALYZED
    actor: str = "SYSTEM"       # SYSTEM or reviewer name
    actor_type: str = "system"  # system | human
    payload_json: str           # JSON string of all relevant fields
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    previous_hash: Optional[str] = None  # SHA-256 of the previous log row
    hash: str = ""              # SHA-256 of (payload_json + previous_hash)
