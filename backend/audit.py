"""
audit.py — Append-only, SHA-256 hash-chained audit event logger.

Every recorded event produces a row in the AuditLog table where:
    hash = SHA256( payload_json + "|" + previous_hash )

This allows any observer to verify the full chain has not been tampered with
by re-computing all hashes from the first row forward.
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

import models

logger = logging.getLogger(__name__)

# Event type constants
EV_TENDER_UPLOADED    = "TENDER_UPLOADED"
EV_TENDER_ANALYZED    = "TENDER_ANALYZED"
EV_TENDER_REANALYZED  = "TENDER_REANALYZED"
EV_BIDDER_UPLOADED    = "BIDDER_UPLOADED"
EV_BIDDER_EVALUATED   = "BIDDER_EVALUATED"
EV_VERDICT_OVERRIDDEN = "VERDICT_OVERRIDDEN"


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _get_last_hash(session: Session, tender_id: Optional[int]) -> Optional[str]:
    """Fetch the hash of the most recent AuditLog row for this tender."""
    stmt = (
        select(models.AuditLog)
        .where(models.AuditLog.tender_id == tender_id)
        .order_by(models.AuditLog.id.desc())  # type: ignore[attr-defined]
    )
    last = session.exec(stmt).first()
    return last.hash if last else None


def log_event(
    session: Session,
    event_type: str,
    payload: dict,
    tender_id: Optional[int] = None,
    bidder_id: Optional[int] = None,
    evaluation_id: Optional[int] = None,
    actor: str = "SYSTEM",
    actor_type: str = "system",
) -> models.AuditLog:
    """
    Append a new audit event to the chain. Returns the created AuditLog row.
    Thread-safe within a single SQLite connection; for multi-process, use Postgres + row locking.
    """
    try:
        payload_json = json.dumps(payload, default=str, ensure_ascii=False)
        previous_hash = _get_last_hash(session, tender_id)
        chain_input = payload_json + "|" + (previous_hash or "GENESIS")
        event_hash = _sha256(chain_input)

        entry = models.AuditLog(
            tender_id=tender_id,
            bidder_id=bidder_id,
            evaluation_id=evaluation_id,
            event_type=event_type,
            actor=actor,
            actor_type=actor_type,
            payload_json=payload_json,
            timestamp=datetime.utcnow(),
            previous_hash=previous_hash,
            hash=event_hash,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
    except Exception as e:
        logger.warning(f"Audit log failed (non-fatal): {e}")
        # Audit logging must NEVER break the main workflow
        # Just return a dummy object if it fails
        return models.AuditLog(event_type=event_type, payload_json="{}", hash="ERROR")


def verify_chain(session: Session, tender_id: int) -> dict:
    """
    Verify the complete audit chain for a tender.
    Returns {"valid": bool, "event_count": int, "first_hash": str, "last_hash": str, "broken_at": int|None}
    """
    stmt = (
        select(models.AuditLog)
        .where(models.AuditLog.tender_id == tender_id)
        .order_by(models.AuditLog.id)  # type: ignore[attr-defined]
    )
    events = session.exec(stmt).all()
    if not events:
        return {"valid": True, "event_count": 0, "first_hash": None, "last_hash": None, "broken_at": None}

    broken_at = None
    prev_hash = None

    for ev in events:
        expected_prev = prev_hash  # None on first event
        chain_input = ev.payload_json + "|" + (expected_prev or "GENESIS")
        expected_hash = _sha256(chain_input)

        if ev.hash != expected_hash or ev.previous_hash != expected_prev:
            broken_at = ev.id
            break

        prev_hash = ev.hash

    return {
        "valid": broken_at is None,
        "event_count": len(events),
        "first_hash": events[0].hash if events else None,
        "last_hash": events[-1].hash if events else None,
        "broken_at": broken_at,
    }
