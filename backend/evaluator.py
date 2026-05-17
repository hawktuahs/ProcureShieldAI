"""
Orchestrates the full evaluation pipeline for a single bidder.
Called from background tasks in main.py.
"""

import logging
from sqlmodel import Session, select
from models import Bidder, Criterion, CriterionEvaluation
from llm import evaluate_criterion, compute_overall_verdict

logger = logging.getLogger(__name__)


def _compute_risk_score(evaluations: list[dict], criteria: list) -> int:
    """
    Compute a 0-100 risk score for a bidder (higher = riskier).
    
    Formula:
    - Start at 0
    - Each mandatory FAIL: +15 points
    - Each mandatory NEEDS_REVIEW: +8 points  
    - Each optional FAIL: +4 points
    - Each optional NEEDS_REVIEW: +2 points
    - Low overall confidence (avg < 0.6): +10 points
    - Capped at 100
    """
    score = 0
    confidences = []

    for result, criterion in zip(evaluations, criteria):
        v = result.get("verdict", "needs_review")
        is_mandatory = criterion.is_mandatory
        conf = float(result.get("confidence", 0.5))
        confidences.append(conf)

        if v == "fail":
            score += 15 if is_mandatory else 4
        elif v == "needs_review":
            score += 8 if is_mandatory else 2

    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        if avg_conf < 0.6:
            score += 10

    return min(score, 100)


def run_bidder_evaluation(bidder_id: int, session: Session) -> None:
    """
    Evaluate all criteria for a bidder and persist results.
    Updates bidder.status, bidder.overall_verdict, and bidder.risk_score when done.
    """
    bidder = session.get(Bidder, bidder_id)
    if not bidder:
        logger.error(f"Bidder {bidder_id} not found")
        return

    criteria = session.exec(
        select(Criterion).where(Criterion.tender_id == bidder.tender_id)
    ).all()

    if not criteria:
        bidder.status = "evaluated"
        bidder.overall_verdict = "needs_review"
        bidder.overall_reasoning = "No criteria found for this tender."
        bidder.risk_score = 50
        session.add(bidder)
        session.commit()
        return

    evaluations = []
    for criterion in criteria:
        try:
            result = evaluate_criterion(
                criterion={
                    "criterion_type": criterion.criterion_type,
                    "description": criterion.description,
                    "is_mandatory": criterion.is_mandatory,
                    "threshold_value": criterion.threshold_value,
                },
                bidder_text=bidder.raw_text,
                bidder_name=bidder.name,
            )
        except Exception as e:
            logger.error(f"Criterion {criterion.id} eval failed: {e}")
            result = {
                "verdict": "needs_review",
                "confidence": 0.0,
                "extracted_value": None,
                "evidence_snippet": None,
                "reasoning": f"Evaluation failed: {str(e)[:200]}",
            }

        eval_record = CriterionEvaluation(
            bidder_id=bidder_id,
            criterion_id=criterion.id,
            verdict=result["verdict"],
            confidence=float(result.get("confidence", 0.0)),
            extracted_value=result.get("extracted_value"),
            evidence_snippet=result.get("evidence_snippet"),
            reasoning=result.get("reasoning", ""),
        )
        session.add(eval_record)
        session.commit()
        session.refresh(eval_record)
        evaluations.append(result)

    # Compute overall verdict
    criteria_dicts = [
        {"is_mandatory": c.is_mandatory, "description": c.description}
        for c in criteria
    ]
    overall_verdict, overall_reasoning = compute_overall_verdict(evaluations, criteria_dicts)

    # Compute risk score
    risk_score = _compute_risk_score(evaluations, list(criteria))

    bidder.overall_verdict = overall_verdict
    bidder.overall_reasoning = overall_reasoning
    bidder.risk_score = risk_score
    bidder.status = "evaluated"
    session.add(bidder)
    session.commit()
    logger.info(f"Bidder {bidder_id} evaluated → {overall_verdict} (risk={risk_score})")
