"""
backend/routers/hypotheses.py
Competing Hypotheses & Evidence Assessment Matrix Router.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Case, Evidence, Hypothesis, EvidenceAssessment, User, EditLock
)
from schemas import (
    HypothesisCreate, HypothesisOut, HypothesisDetailOut,
    EvidenceAssessmentCreate, EvidenceAssessmentOut, AssessmentOverrideRequest
)
from auth import get_current_user, check_case_access
from scoring import calculate_three_layer_ach_scoring, CLASSIFICATION_CONFIG
from audit_engine import log_audit_event
from routers.common import resolve_case_id
from routers.cases import ensure_unknown_hypothesis
from collaboration import publish_collaboration_event, release_edit_lock
from datetime import datetime, timezone

router = APIRouter(tags=["Hypotheses & Evidence Assessments"])


def verify_quoted_source_line(quote: Optional[str], full_text: Optional[str]) -> str:
    """Verifies that a quoted source line actually exists in the exhibit text to eliminate AI hallucination."""
    if not quote or not full_text:
        return ""
    q = quote.strip().strip('"\'')
    if len(q) < 5:
        return ""
    if q.lower() in full_text.lower():
        return q
    if len(q) >= 20 and q[:20].lower() in full_text.lower():
        return q
    return ""


@router.get("/cases/{case_id}/hypotheses", response_model=List[HypothesisOut])
def get_hypotheses_for_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    
    ensure_unknown_hypothesis(real_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_id).order_by(Hypothesis.support_score.desc()).all()
    
    results = []
    for h in hypotheses:
        results.append(HypothesisOut(
            id=h.id,
            case_id=h.case_id,
            title=h.title,
            description=h.description,
            status=h.status,
            support_score=getattr(h, "combined_score", None) or h.support_score or 50.0,
            evidence_score=getattr(h, "evidence_score", None) or h.support_score or 50.0,
            background_score=getattr(h, "background_score", 0.0) or 0.0,
            combined_score=getattr(h, "combined_score", None) or h.support_score or 50.0,
            bayesian_lr_score=getattr(h, "bayesian_lr_score", None) or h.support_score or 50.0,
            bayesian_evidence_score=getattr(h, "bayesian_evidence_score", None) or h.support_score or 50.0,
            classic_ach_score=getattr(h, "classic_ach_score", None) or h.support_score or 50.0,
            classic_evidence_score=getattr(h, "classic_evidence_score", None) or h.support_score or 50.0,
            cumulative_lr=getattr(h, "cumulative_lr", 1.0) or 1.0,
            disconfirmation_penalty=h.disconfirmation_penalty or 0.0,
            relative_likelihood=getattr(h, "evidence_score", None) or h.support_score or 50.0,
            created_at=h.created_at,
            assessment_count=len(h.assessments) if h.assessments else 0,
            is_unknown=bool(getattr(h, "is_unknown", False)),
            lead_message=getattr(h, "lead_message", None)
        ))
    return results


@router.post("/cases/{case_id}/hypotheses", response_model=HypothesisOut)
def create_hypothesis(
    case_id: str,
    hyp: HypothesisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to add hypotheses.")
        
    db_hyp = Hypothesis(
        case_id=real_id,
        title=hyp.title,
        description=hyp.description,
        status=hyp.status or "Active",
        support_score=hyp.support_score or 50.0
    )
    db.add(db_hyp)
    db.commit()
    db.refresh(db_hyp)
    
    return HypothesisOut(
        id=db_hyp.id,
        case_id=db_hyp.case_id,
        title=db_hyp.title,
        description=db_hyp.description,
        status=db_hyp.status,
        support_score=db_hyp.support_score,
        disconfirmation_penalty=db_hyp.disconfirmation_penalty or 0.0,
        relative_likelihood=db_hyp.support_score,
        created_at=db_hyp.created_at,
        assessment_count=0
    )


@router.get("/hypotheses/{hypothesis_id}", response_model=HypothesisDetailOut)
def get_hypothesis(
    hypothesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    if not check_case_access(h.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
        
    assessments_out = []
    for a in h.assessments:
        ev = a.evidence
        assessments_out.append(EvidenceAssessmentOut(
            id=a.id,
            hypothesis_id=a.hypothesis_id,
            evidence_id=a.evidence_id,
            classification=a.classification,
            original_classification=a.original_classification or a.classification,
            analyst_override=bool(a.analyst_override),
            analyst_notes=a.analyst_notes,
            reason=a.reason,
            llm_confidence=a.llm_confidence,
            reliability=a.reliability,
            diagnosticity_weight=getattr(a, "computed_diagnosticity", 1.0) or 1.0,
            diagnosticity_category="Medium",
            quoted_source_line=a.quoted_source_line,
            computed_reliability=a.computed_reliability or a.reliability or 1.0,
            computed_diagnosticity=a.computed_diagnosticity or 1.0,
            final_contribution=a.final_contribution or 0.0,
            evidence_file_name=ev.file_name if ev else f"Evidence #{a.evidence_id}",
            evidence_file_type=ev.file_type if ev else "Document",
            evidence_type=ev.evidence_type if ev and ev.evidence_type else "document",
            finding_category=getattr(a, "finding_category", None),
            finding_name=getattr(a, "finding_name", None),
            likelihood_ratio=getattr(a, "likelihood_ratio", None),
            effective_lr=getattr(a, "effective_lr", None),
            is_exculpatory=bool(getattr(a, "is_exculpatory", False)),
            clearing_factor_note=getattr(a, "clearing_factor_note", None)
        ))
        
    comb_score = getattr(h, "combined_score", None) or h.support_score or 50.0
    ev_score = getattr(h, "evidence_score", None) or h.support_score or 50.0
    bg_score = getattr(h, "background_score", 0.0) or 0.0

    return HypothesisDetailOut(
        id=h.id,
        case_id=h.case_id,
        title=h.title,
        description=h.description,
        status=h.status,
        support_score=comb_score,
        evidence_score=ev_score,
        background_score=bg_score,
        combined_score=comb_score,
        bayesian_lr_score=getattr(h, "bayesian_lr_score", None) or comb_score,
        bayesian_evidence_score=getattr(h, "bayesian_evidence_score", None) or ev_score,
        classic_ach_score=getattr(h, "classic_ach_score", None) or comb_score,
        classic_evidence_score=getattr(h, "classic_evidence_score", None) or ev_score,
        cumulative_lr=getattr(h, "cumulative_lr", 1.0) or 1.0,
        disconfirmation_penalty=h.disconfirmation_penalty or 0.0,
        relative_likelihood=ev_score,
        created_at=h.created_at,
        assessment_count=len(h.assessments) if h.assessments else 0,
        assessments=assessments_out,
        is_unknown=bool(getattr(h, "is_unknown", False)),
        lead_message=getattr(h, "lead_message", None)
    )


@router.put("/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def update_hypothesis(
    hypothesis_id: int,
    hyp_update: HypothesisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    if not check_case_access(h.case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to edit hypotheses.")

    current_version = getattr(h, "version", 1) or 1

    # 1. Optimistic Concurrency Check
    if hyp_update.version is not None and hyp_update.version != current_version:
        log_audit_event(
            db=db,
            action_type="CONFLICT_REJECTED",
            target_type="hypothesis",
            target_id=str(h.id),
            description=f"Concurrent conflict on Hypothesis #{h.id}: User submitted v{hyp_update.version}, but current version is v{current_version}.",
            case_id=h.case_id,
            user_id=current_user.id,
            user_name=current_user.full_name,
            before_value=f"v{hyp_update.version}",
            after_value=f"v{current_version}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict",
                "message": f"Hypothesis #{h.id} was modified by another investigator while you were editing.",
                "item_type": "hypothesis",
                "item_id": str(h.id),
                "current_version": current_version,
                "submitted_version": hyp_update.version,
                "current_data": {
                    "id": h.id,
                    "title": h.title,
                    "description": h.description,
                    "status": h.status
                }
            }
        )

    # 2. Soft Edit Lock Check (rejects if actively held by another user)
    now = datetime.now(timezone.utc)
    active_lock = db.query(EditLock).filter(
        EditLock.case_id == h.case_id,
        EditLock.item_type == "hypothesis",
        EditLock.item_id == str(h.id),
        EditLock.expires_at > now,
        EditLock.user_id != current_user.id
    ).first()
    if active_lock:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "locked",
                "message": f"{active_lock.user_name} is currently editing this hypothesis.",
                "locked_by": active_lock.user_name,
                "user_role": active_lock.user_role,
                "expires_at": active_lock.expires_at.isoformat()
            }
        )

    # 3. Update fields and version in single transaction
    before_vals = f"title='{h.title}', status='{h.status}', desc='{h.description or ''}'"
    h.title = hyp_update.title
    h.description = hyp_update.description
    h.status = hyp_update.status or h.status
    h.version = current_version + 1
    after_vals = f"title='{h.title}', status='{h.status}', desc='{h.description or ''}'"

    # Transactional audit log in the same database transaction
    log_audit_event(
        db=db,
        action_type="HYPOTHESIS_UPDATE",
        target_type="hypothesis",
        target_id=str(h.id),
        description=f"Investigator {current_user.full_name} updated Hypothesis #{h.id} (v{h.version})",
        case_id=h.case_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        before_value=before_vals,
        after_value=after_vals,
        commit=False
    )
    db.commit()
    db.refresh(h)

    # Release caller's edit lock
    release_edit_lock(db, h.case_id, "hypothesis", str(h.id), current_user.id)

    # Publish change notification to case live event channel
    publish_collaboration_event(
        db=db,
        case_id=h.case_id,
        event_type="item.changed",
        item_type="hypothesis",
        item_id=str(h.id),
        version=h.version,
        user_id=current_user.id,
        user_name=current_user.full_name,
        summary=f"{current_user.full_name} updated Hypothesis #{h.id}: '{h.title}'",
        payload={
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "status": h.status,
            "version": h.version
        }
    )

    return h


@router.delete("/hypotheses/{hypothesis_id}")
def delete_hypothesis(
    hypothesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    if not check_case_access(h.case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to delete hypotheses.")
        
    db.delete(h)
    db.commit()
    return {"status": "success", "message": f"Hypothesis #{hypothesis_id} deleted"}


@router.post("/cases/{case_id}/assessments/override")
def analyst_override_assessment(
    case_id: str,
    data: AssessmentOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to override assessments.")

    assessment = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == data.hypothesis_id,
        EvidenceAssessment.evidence_id == data.evidence_id
    ).first()

    current_version = getattr(assessment, "version", 1) if assessment else 1

    # 1. Optimistic Concurrency Check
    if assessment and data.version is not None and data.version != current_version:
        log_audit_event(
            db=db,
            action_type="CONFLICT_REJECTED",
            target_type="evidence_assessment",
            target_id=str(assessment.id),
            description=f"Concurrent conflict on Assessment #{assessment.id}: User submitted v{data.version}, current is v{current_version}.",
            case_id=real_case_id,
            user_id=current_user.id,
            user_name=current_user.full_name,
            before_value=f"v{data.version}",
            after_value=f"v{current_version}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict",
                "message": f"Assessment for Exhibit #{data.evidence_id} was modified by another user.",
                "item_type": "evidence_assessment",
                "item_id": str(assessment.id),
                "current_version": current_version,
                "submitted_version": data.version,
                "current_data": {
                    "id": assessment.id,
                    "classification": assessment.classification,
                    "analyst_notes": assessment.analyst_notes
                }
            }
        )

    orig_val = "neutral"
    if not assessment:
        assessment = EvidenceAssessment(
            hypothesis_id=data.hypothesis_id,
            evidence_id=data.evidence_id,
            classification=data.classification.lower().strip() if data.classification else "neutral",
            original_classification="neutral",
            analyst_override=True,
            analyst_notes=data.analyst_notes,
            reason=f"Analyst Override: {data.analyst_notes}",
            llm_confidence=1.0,
            reliability=1.0,
            version=1
        )
        db.add(assessment)
    else:
        orig_val = assessment.original_classification or assessment.classification
        if not assessment.original_classification:
            assessment.original_classification = assessment.classification
        if data.classification:
            assessment.classification = data.classification.lower().strip()
        assessment.analyst_override = True
        assessment.analyst_notes = data.analyst_notes
        assessment.version = current_version + 1

    log_audit_event(
        db=db,
        action_type="ACH_OVERRIDE",
        target_type="evidence_assessment",
        target_id=str(assessment.id) if assessment.id else f"H{data.hypothesis_id}-E{data.evidence_id}",
        description=f"Investigator {current_user.full_name} ({current_user.role}) overrode matrix cell for Exhibit #{data.evidence_id} on Hypothesis #{data.hypothesis_id}: '{orig_val}' -> '{assessment.classification}'",
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        case_id=real_case_id,
        before_value=str(orig_val),
        after_value=str(assessment.classification),
        commit=False
    )
    db.commit()
    db.refresh(assessment)

    # Publish collaboration event
    publish_collaboration_event(
        db=db,
        case_id=real_case_id,
        event_type="item.changed",
        item_type="evidence_assessment",
        item_id=str(assessment.id),
        version=assessment.version,
        user_id=current_user.id,
        user_name=current_user.full_name,
        summary=f"{current_user.full_name} updated assessment for Exhibit #{data.evidence_id} on Hypothesis #{data.hypothesis_id}",
        payload={
            "id": assessment.id,
            "hypothesis_id": assessment.hypothesis_id,
            "evidence_id": assessment.evidence_id,
            "classification": assessment.classification,
            "version": assessment.version
        }
    )

    # Publish scores updated
    publish_collaboration_event(
        db=db,
        case_id=real_case_id,
        event_type="scores.updated",
        item_type="case_scoring",
        item_id=str(real_case_id),
        user_name=current_user.full_name,
        summary=f"Recalculating ACH matrix following assessment change on Exhibit #{data.evidence_id}."
    )

    return {
        "status": "success",
        "message": f"Analyst override applied to Exhibit #{data.evidence_id}",
        "assessment": {
            "id": assessment.id,
            "hypothesis_id": assessment.hypothesis_id,
            "evidence_id": assessment.evidence_id,
            "classification": assessment.classification,
            "original_classification": assessment.original_classification,
            "analyst_override": assessment.analyst_override,
            "analyst_notes": assessment.analyst_notes
        }
    }


@router.post("/cases/{case_id}/assessments/reset")
def analyst_reset_assessment(
    case_id: str,
    hypothesis_id: int,
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to reset assessments.")

    assessment = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == hypothesis_id,
        EvidenceAssessment.evidence_id == evidence_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.original_classification:
        assessment.classification = assessment.original_classification
    assessment.analyst_override = False
    assessment.analyst_notes = None

    db.commit()
    db.refresh(assessment)

    return {
        "status": "success",
        "message": "Assessment restored to AI baseline judgment",
        "classification": assessment.classification
    }

