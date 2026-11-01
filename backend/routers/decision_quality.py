"""
backend/routers/decision_quality.py
===================================
Evidentia AI - Decision-Quality, Devil's Advocate & Four-Eyes Sign-Off Router.
Provides API endpoints for:
  - Devil's Advocate Counter-Case Dossier & Suppression Stress-Testing
  - Cognitive & Evidentiary Bias Alerts (Single Exhibit, Untested Alt, Monoculture)
  - Plain-Language Explanations for Non-Technical Officers
  - Two-Analyst Sign-Offs (Maker-Checker Protocol)
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import (
    Case, Evidence, Hypothesis, EvidenceAssessment,
    ChargesheetDraft, DecisionSignoff, Alert, User
)
from schemas import (
    DecisionSignoffOut, DecisionSignoffRequest, DecisionSignoffReviewRequest,
    DevilsAdvocateResponse, PlainLanguageExplanationResponse
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from decision_quality_engine import (
    build_devils_advocate_dossier,
    evaluate_bias_alerts,
    generate_plain_language_explanation,
    request_second_signoff,
    review_second_signoff
)
from routers.scoring import execute_scoring_run

logger = logging.getLogger("evidentia.decision_quality_router")

router = APIRouter(tags=["Decision-Quality & Devil's Advocate"])


# ==============================================================================
# 1. DEVIL'S-ADVOCATE COUNTER-CASE DOSSIER
# ==============================================================================

@router.get("/cases/{case_id}/devils-advocate", response_model=DevilsAdvocateResponse)
def get_devils_advocate_view(
    case_id: str,
    target_hypothesis_id: Optional[int] = Query(None, description="Optional target alternative hypothesis ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Constructs the Devil's Advocate analysis for the runner-up hypothesis using the exact
    same evidence dossier, identifies lead vulnerabilities, conducts suppression stress-tests,
    and synthesizes a defense challenge brief.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    dossier = build_devils_advocate_dossier(
        case_id=real_id,
        db=db,
        target_hypothesis_id=target_hypothesis_id
    )
    return dossier


# ==============================================================================
# 2. COGNITIVE & EVIDENTIARY BIAS ALERTS
# ==============================================================================

@router.get("/cases/{case_id}/bias-alerts")
def get_bias_alerts(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scans the case for:
      - Single-Exhibit Dependency (Fragility / Tower of Cards)
      - Untested Leading Alternative (Tunnel Vision / Premature Closure)
      - Source Type Monoculture (Corroboration Deficit)
    Returns newly created and existing active bias alerts.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    alerts = evaluate_bias_alerts(case_id=real_id, db=db)

    # Fetch all active bias alerts in the case
    active_bias_alerts = db.query(Alert).filter(
        Alert.case_id == real_id,
        Alert.rule_type.like("bias_%"),
        Alert.status.in_(["unread", "acknowledged", "snoozed"])
    ).order_by(desc(Alert.created_at)).all()

    return {
        "case_id": real_id,
        "total_active_bias_alerts": len(active_bias_alerts),
        "bias_alerts": [
            {
                "id": a.id,
                "rule_type": a.rule_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "linked_item_type": a.linked_item_type,
                "linked_item_id": a.linked_item_id,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in active_bias_alerts
        ]
    }


# ==============================================================================
# 3. PLAIN-LANGUAGE EXPLANATION PER HYPOTHESIS
# ==============================================================================

@router.get("/cases/{case_id}/hypotheses/{hypothesis_id}/plain-language", response_model=PlainLanguageExplanationResponse)
def get_hypothesis_plain_language_explanation(
    case_id: str,
    hypothesis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a plain-language, non-technical explanation for an investigating officer,
    summarizing verdict, primary drivers, vulnerabilities, and recommended next steps.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    hypo = db.query(Hypothesis).filter(
        Hypothesis.id == hypothesis_id,
        Hypothesis.case_id == real_id
    ).first()
    if not hypo:
        raise HTTPException(status_code=404, detail="Hypothesis not found.")

    scoring_res = execute_scoring_run(case_id=real_id, db=db, triggered_by="plain_language_request")

    target_hyp_dict = next(
        (h for h in scoring_res.get("hypotheses", []) if h.get("id") == hypothesis_id),
        {
            "id": hypo.id,
            "title": hypo.title,
            "combined_score": hypo.combined_score or hypo.support_score,
            "is_unknown": hypo.is_unknown
        }
    )

    explanation = generate_plain_language_explanation(
        hypothesis=target_hyp_dict,
        all_hypotheses=scoring_res.get("hypotheses", []),
        breakdowns=scoring_res.get("hypothesis_breakdowns", {}),
        critical_exhibits=scoring_res.get("critical_exhibits", [])
    )

    return explanation


# ==============================================================================
# 4. TWO-ANALYST SIGN-OFF WORKFLOW (FOUR-EYES PROTOCOL)
# ==============================================================================

@router.get("/cases/{case_id}/signoffs", response_model=List[DecisionSignoffOut])
def list_case_signoffs(
    case_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    item_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all decision sign-off records for the case with optional filters."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    query = db.query(DecisionSignoff).filter(DecisionSignoff.case_id == real_id)
    if status_filter:
        query = query.filter(DecisionSignoff.status == status_filter)
    if item_type:
        query = query.filter(DecisionSignoff.item_type == item_type)

    return query.order_by(desc(DecisionSignoff.requested_at)).all()


@router.post("/cases/{case_id}/signoffs/request", response_model=DecisionSignoffOut)
def create_signoff_request(
    case_id: str,
    payload: DecisionSignoffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyst submits a key classification or final report for second reviewer sign-off.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Analyst permissions required to request sign-off.")

    signoff = request_second_signoff(
        db=db,
        case_id=real_id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        item_summary=payload.item_summary,
        maker_user_id=current_user.id,
        maker_name=current_user.full_name
    )
    return signoff


@router.post("/cases/{case_id}/signoffs/{signoff_id}/review")
def review_signoff_endpoint(
    case_id: str,
    signoff_id: int,
    payload: DecisionSignoffReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Second analyst or reviewer signs off on a pending request.
    Enforces the Four-Eyes principle: Maker cannot sign off on own submission.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "review_case"):
        raise HTTPException(status_code=403, detail="Reviewer or Lead role required to execute sign-off.")

    try:
        result = review_second_signoff(
            db=db,
            case_id=real_id,
            signoff_id=signoff_id,
            checker_user_id=current_user.id,
            checker_name=current_user.full_name,
            checker_role=current_user.role,
            approved=payload.approved,
            review_notes=payload.review_notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

