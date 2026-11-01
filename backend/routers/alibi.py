"""
backend/routers/alibi.py
================================================================================
EVIDENTIA AI - ALIBI VERIFICATION WORKFLOW ROUTER
================================================================================
REST API endpoints for defense alibi claim management, multi-segment verification,
electronic corroboration (CDR, CCTV, Banking), line-by-line statement comparison,
interrogation confrontation questions, and statutory chargesheet refutation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from database import get_db
from models import (
    Case, CasePerson, Hypothesis, InterviewStatement,
    AlibiClaim, AlibiSegment, AlibiCheck, StatementComparison,
    InvestigationTask, User
)
from schemas import (
    AlibiClaimCreate, AlibiClaimOut, AlibiClaimDetailOut,
    AlibiSegmentCreate, AlibiSegmentOut,
    AlibiCheckCreate, AlibiCheckUpdate, AlibiCheckOut,
    StatementComparisonOut, StatementComparisonReviewRequest,
    AlibiVerdictRequest
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from audit_engine import log_audit_event
from alibi_engine import (
    haversine_distance_km, check_travel_feasibility,
    calculate_crime_window_coverage, generate_verification_tasks,
    run_automatic_cdr_check, roll_up_alibi_status,
    compare_statement_line_by_line, generate_confrontation_questions,
    generate_chargesheet_refutation
)

router = APIRouter(tags=["alibi"])


# ==============================================================================
# ALIBI CLAIMS
# ==============================================================================

@router.post("/cases/{case_id}/alibis", response_model=AlibiClaimDetailOut, status_code=status.HTTP_201_CREATED)
def create_alibi_claim(
    case_id: str,
    payload: AlibiClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records a formal defense alibi claim by or on behalf of an accused person.
    Creates initial segments and associates source interview statements.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    # Check existing active claims for this suspect - if any exist, increment version
    existing = db.query(AlibiClaim).filter(
        AlibiClaim.case_id == real_id,
        AlibiClaim.suspect_name == payload.suspect_name,
        AlibiClaim.is_current == True
    ).first()

    next_version = 1
    if existing:
        existing.is_current = False
        next_version = existing.version + 1

    claim = AlibiClaim(
        case_id=real_id,
        person_id=payload.person_id,
        suspect_name=payload.suspect_name,
        hypothesis_id=payload.hypothesis_id,
        claim_text=payload.claim_text,
        source_statement_id=payload.source_statement_id,
        source_citation=payload.source_citation,
        version=next_version,
        raised_at=payload.raised_at or datetime.now(timezone.utc),
        status="open",
        is_current=True
    )
    db.add(claim)
    db.flush()

    # Add initial segments
    for idx, seg_data in enumerate(payload.segments, start=1):
        seg = AlibiSegment(
            claim_id=claim.id,
            segment_order=seg_data.segment_order or idx,
            start_time=seg_data.start_time,
            end_time=seg_data.end_time,
            time_uncertainty_mins=seg_data.time_uncertainty_mins,
            claimed_place_name=seg_data.claimed_place_name,
            latitude=seg_data.latitude,
            longitude=seg_data.longitude,
            radius_meters=seg_data.radius_meters,
            activity=seg_data.activity,
            travel_mode=seg_data.travel_mode,
            vouching_persons=seg_data.vouching_persons,
            notes=seg_data.notes,
            status="unverified"
        )
        db.add(seg)

    db.commit()
    db.refresh(claim)

    log_audit_event(
        db=db,
        case_id=real_id,
        user_name=current_user.full_name or current_user.email,
        user_role=current_user.role,
        action_type="ALIBI_CLAIM_RECORDED",
        target_type="alibi_claim",
        target_id=str(claim.id),
        description=f"Recorded Alibi Claim (v{next_version}) for accused {claim.suspect_name}: '{claim.claim_text[:80]}...'"
    )

    return get_alibi_claim_details(case_id=str(real_id), claim_id=claim.id, db=db, current_user=current_user)


@router.get("/cases/{case_id}/alibis", response_model=List[AlibiClaimOut])
def list_alibi_claims(
    case_id: str,
    suspect_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists defense alibi claims on file for a case with optional suspect and status filtering."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    query = db.query(AlibiClaim).filter(AlibiClaim.case_id == real_id)
    if current_only:
        query = query.filter(AlibiClaim.is_current == True)
    if suspect_name:
        query = query.filter(AlibiClaim.suspect_name.ilike(f"%{suspect_name}%"))
    if status_filter:
        query = query.filter(AlibiClaim.status == status_filter)

    claims = query.order_by(AlibiClaim.created_at.desc()).all()

    result = []
    for c in claims:
        out = AlibiClaimOut.from_orm(c)
        out.segments_count = len(c.segments)
        out.checks_count = len(c.checks)
        result.append(out)

    return result


@router.get("/cases/{case_id}/alibis/{claim_id}", response_model=AlibiClaimDetailOut)
def get_alibi_claim_details(
    case_id: str,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns full investigative detail of an alibi claim, including segments,
    checks, statement comparisons, crime window coverage analysis, and travel feasibility.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    claim = db.query(AlibiClaim).filter(
        AlibiClaim.id == claim_id,
        AlibiClaim.case_id == real_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Alibi claim {claim_id} not found.")

    case = db.query(Case).filter(Case.id == real_id).first()

    # Calculate coverage
    coverage_report = calculate_crime_window_coverage(case, claim.segments)

    # Calculate travel feasibility between consecutive segments
    travel_reports = []
    sorted_segs = sorted(claim.segments, key=lambda s: s.start_time)
    for i in range(len(sorted_segs) - 1):
        report = check_travel_feasibility(sorted_segs[i], sorted_segs[i + 1])
        travel_reports.append(report)

    out = AlibiClaimDetailOut.from_orm(claim)
    out.segments_count = len(claim.segments)
    out.checks_count = len(claim.checks)
    out.coverage_report = coverage_report
    out.travel_feasibility_reports = travel_reports

    return out


# ==============================================================================
# SEGMENTS MANAGEMENT
# ==============================================================================

@router.post("/cases/{case_id}/alibis/{claim_id}/segments", response_model=AlibiSegmentOut, status_code=status.HTTP_201_CREATED)
def add_alibi_segment(
    case_id: str,
    claim_id: int,
    payload: AlibiSegmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adds a new discrete spatiotemporal segment to an existing alibi claim."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    claim = db.query(AlibiClaim).filter(AlibiClaim.id == claim_id, AlibiClaim.case_id == real_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    seg = AlibiSegment(
        claim_id=claim.id,
        segment_order=payload.segment_order,
        start_time=payload.start_time,
        end_time=payload.end_time,
        time_uncertainty_mins=payload.time_uncertainty_mins,
        claimed_place_name=payload.claimed_place_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        activity=payload.activity,
        travel_mode=payload.travel_mode,
        vouching_persons=payload.vouching_persons,
        notes=payload.notes,
        status="unverified"
    )
    db.add(seg)
    db.commit()
    db.refresh(seg)

    return seg


@router.delete("/cases/{case_id}/alibis/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alibi_segment(
    case_id: str,
    segment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Removes an alibi segment and its dependent checks."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    seg = db.query(AlibiSegment).filter(AlibiSegment.id == segment_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found.")

    claim = seg.claim
    if claim.case_id != real_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to segment.")

    db.delete(seg)
    db.commit()
    return None


# ==============================================================================
# VERIFICATION CHECKS & TASK DISPATCH
# ==============================================================================

@router.post("/cases/{case_id}/alibis/{claim_id}/generate-tasks", response_model=List[AlibiCheckOut])
def trigger_alibi_task_generation(
    case_id: str,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-generates required electronic, ocular, and vehicular verification checks
    for an alibi claim and dispatches linked InvestigationTask entries.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    claim = db.query(AlibiClaim).filter(AlibiClaim.id == claim_id, AlibiClaim.case_id == real_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    user_name = current_user.full_name or current_user.email
    checks = generate_verification_tasks(
        claim_id=claim_id,
        user_id=current_user.id,
        user_name=user_name,
        db=db
    )
    return checks


@router.post("/cases/{case_id}/alibis/checks/{check_id}/run-auto-check")
def execute_auto_check(
    case_id: str,
    check_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes automated electronic check (CDR tower dump, banking) for an alibi check item."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    check = db.query(AlibiCheck).filter(AlibiCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail=f"Check {check_id} not found.")

    if check.source_type == "cdr_tower":
        res = run_automatic_cdr_check(check_id=check_id, db=db)
        # Roll up status
        roll_up_alibi_status(claim_id=check.claim_id, db=db)
        return res
    else:
        return {
            "check_id": check.id,
            "result": "pending",
            "message": f"Source type '{check.source_type}' requires manual forensic artifact attachment or subpoena response intake."
        }


@router.patch("/cases/{case_id}/alibis/checks/{check_id}", response_model=AlibiCheckOut)
def record_check_result(
    case_id: str,
    check_id: int,
    payload: AlibiCheckUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records investigator verification result (confirmed, contradicted, inconclusive),
    links supporting exhibits, logs clock offset drift, and triggers status roll-up.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    check = db.query(AlibiCheck).filter(AlibiCheck.id == check_id).first()
    if not check:
        raise HTTPException(status_code=404, detail=f"Check {check_id} not found.")

    if payload.status:
        check.status = payload.status
    if payload.result:
        check.result = payload.result
        check.verified_by_id = current_user.id
        check.verified_by_name = current_user.full_name or current_user.email
        check.verified_at = datetime.now(timezone.utc)
    if payload.unlocatable_reason is not None:
        check.unlocatable_reason = payload.unlocatable_reason
    if payload.supporting_evidence_ids is not None:
        check.supporting_evidence_ids = payload.supporting_evidence_ids
    if payload.supporting_citations is not None:
        check.supporting_citations = payload.supporting_citations
    if payload.clock_offset_seconds is not None:
        check.clock_offset_seconds = payload.clock_offset_seconds
    if payload.explanation is not None:
        check.explanation = payload.explanation

    db.commit()

    # Re-evaluate claim status roll-up
    roll_up_alibi_status(claim_id=check.claim_id, db=db)
    db.refresh(check)

    log_audit_event(
        db=db,
        case_id=real_id,
        user_name=current_user.full_name or current_user.email,
        user_role=current_user.role,
        action_type="ALIBI_CHECK_VERIFIED",
        target_type="alibi_check",
        target_id=str(check.id),
        description=f"Recorded verification result '{check.result}' for check #{check.id} ({check.source_type}). Explanation: {check.explanation or 'None'}"
    )

    return check


# ==============================================================================
# OFFICER VERDICT & STATEMENT COMPARISON
# ==============================================================================

@router.post("/cases/{case_id}/alibis/{claim_id}/verdict", response_model=AlibiClaimDetailOut)
def record_alibi_verdict(
    case_id: str,
    claim_id: int,
    payload: AlibiVerdictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Investigating Officer or Lead Analyst formal sign-off on defense alibi plea.
    Updates suspect profile prior score and logs immutable audit chain entry.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    claim = db.query(AlibiClaim).filter(AlibiClaim.id == claim_id, AlibiClaim.case_id == real_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    claim.final_verdict = payload.final_verdict
    claim.verdict_reason = payload.verdict_reason
    claim.verdict_by_user_id = current_user.id
    claim.verdict_by_name = current_user.full_name or current_user.email
    claim.verdict_at = datetime.now(timezone.utc)
    claim.status = payload.final_verdict

    # Re-trigger prior synchronization
    roll_up_alibi_status(claim_id=claim.id, db=db)

    log_audit_event(
        db=db,
        case_id=real_id,
        user_name=current_user.full_name or current_user.email,
        user_role=current_user.role,
        action_type="ALIBI_VERDICT_CONFIRMED",
        target_type="alibi_claim",
        target_id=str(claim.id),
        description=f"Formal sign-off on Alibi Plea for {claim.suspect_name}: Verdict '{claim.final_verdict}'. Reason: {claim.verdict_reason}"
    )

    return get_alibi_claim_details(case_id=str(real_id), claim_id=claim.id, db=db, current_user=current_user)


@router.post("/cases/{case_id}/alibis/{claim_id}/compare-statement", response_model=List[StatementComparisonOut])
def compare_statement(
    case_id: str,
    claim_id: int,
    statement_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes line-by-line statement assertion extraction and candidate evidence matching.
    """
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    claim = db.query(AlibiClaim).filter(AlibiClaim.id == claim_id, AlibiClaim.case_id == real_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")

    comparisons = compare_statement_line_by_line(statement_id=statement_id, claim_id=claim_id, db=db)
    return comparisons


@router.patch("/cases/{case_id}/alibis/comparisons/{comparison_id}", response_model=StatementComparisonOut)
def review_statement_comparison(
    case_id: str,
    comparison_id: int,
    payload: StatementComparisonReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirms or overrides an automated line-by-line statement assertion result."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    comp = db.query(StatementComparison).filter(StatementComparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Comparison {comparison_id} not found.")

    comp.result = payload.result
    if payload.reasoning:
        comp.reasoning = payload.reasoning
    comp.review_state = payload.review_state
    comp.reviewed_by_id = current_user.id
    comp.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comp)

    return comp


@router.get("/cases/{case_id}/alibis/{claim_id}/confrontation-questions")
def get_confrontation_questions(
    case_id: str,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates structured interrogation confrontation questions formulated from contradicted alibi claims."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    questions = generate_confrontation_questions(claim_id=claim_id, db=db)
    return {"claim_id": claim_id, "questions": questions}


@router.get("/cases/{case_id}/alibis/{claim_id}/chargesheet-refutation")
def get_chargesheet_refutation(
    case_id: str,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assembles a court-ready Chapter: 'Refutation of Alibi' under Section 193 BNSS / Section 173 CrPC."""
    real_id = resolve_case_id(case_id, db)
    check_case_access(real_id, current_user, db)

    refutation = generate_chargesheet_refutation(claim_id=claim_id, db=db)
    return refutation

