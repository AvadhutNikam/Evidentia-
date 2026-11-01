"""
backend/routers/cases.py
Case Docket Management & Membership Router.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Case, CaseMember, User, Hypothesis, Entity, Event, StatutoryDeadlineRule
from schemas import (
    CaseCreate, CaseOut, CaseMemberOut, CaseMemberAddRequest,
    EntityOut, EventOut, CaseProcedureUpdate, StatutoryDeadlineRuleOut,
    StatutoryDeadlineRuleUpdate, EvidenceChecklistResponse
)
from auth import (
    get_current_user, check_case_access, get_user_accessible_case_ids
)
from config import UNKNOWN_HYPOTHESIS_TITLE
from routers.common import resolve_case_id
from procedure_engine import (
    recalculate_case_deadlines, evaluate_evidence_checklist,
    ensure_comprehensive_statutory_rules
)
from alerts_engine import check_statutory_deadlines
from collaboration import publish_collaboration_event
from audit_engine import log_audit_event

router = APIRouter(tags=["Case Dockets & Membership"])


def ensure_unknown_hypothesis(case_id: int, db: Session) -> Hypothesis:
    """Ensures Unknown / Alternative Hypothesis exists for Bayesian calibration."""
    unknown = db.query(Hypothesis).filter(
        Hypothesis.case_id == case_id,
        (Hypothesis.is_unknown == True) | (Hypothesis.title == UNKNOWN_HYPOTHESIS_TITLE)
    ).first()

    if not unknown:
        unknown = Hypothesis(
            case_id=case_id,
            title=UNKNOWN_HYPOTHESIS_TITLE,
            description="Perpetrator is an unknown individual or alternative explanation not currently listed among known suspects.",
            is_unknown=True,
            status="Active",
            version=1
        )
        db.add(unknown)
        db.commit()
        db.refresh(unknown)
    else:
        if not unknown.is_unknown:
            unknown.is_unknown = True
            db.commit()
            db.refresh(unknown)

    return unknown


@router.post("/cases", response_model=CaseOut)
def create_case(case: CaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can register new cases.")
    db_case = Case(
        title=case.title,
        description=case.description,
        status=case.status or "Active",
        created_by=current_user.full_name,
        is_demo=bool(case.is_demo),
        fir_number=case.fir_number,
        fir_date=case.fir_date,
        incident_date=case.incident_date,
        arrest_date=case.arrest_date,
        remand_date=case.remand_date,
        offence_section=case.offence_section,
        statutory_time_limit_days=case.statutory_time_limit_days or 90
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    # Automatically add creator as lead investigator
    m = CaseMember(case_id=db_case.id, user_id=current_user.id, case_role="lead_investigator", added_by="Case Creation")
    db.add(m)
    db.commit()

    ensure_unknown_hypothesis(db_case.id, db)
    recalculate_case_deadlines(db_case.id, db)
    return db_case


@router.get("/cases", response_model=List[CaseOut])
def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible_ids = get_user_accessible_case_ids(current_user, db)
    if accessible_ids is not None:
        return db.query(Case).filter(Case.id.in_(accessible_ids)).all()
    return db.query(Case).all()


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: str, case_update: CaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to modify this case.")
    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.title = case_update.title
    case.description = case_update.description
    case.status = case_update.status or case.status
    if case_update.is_demo is not None:
        case.is_demo = bool(case_update.is_demo)
    if case_update.fir_number is not None:
        case.fir_number = case_update.fir_number
    if case_update.fir_date is not None:
        case.fir_date = case_update.fir_date
    if case_update.incident_date is not None:
        case.incident_date = case_update.incident_date
    if case_update.arrest_date is not None:
        case.arrest_date = case_update.arrest_date
    if case_update.remand_date is not None:
        case.remand_date = case_update.remand_date
    if case_update.offence_section is not None:
        case.offence_section = case_update.offence_section
    if case_update.statutory_time_limit_days is not None:
        case.statutory_time_limit_days = case_update.statutory_time_limit_days
        
    db.commit()
    db.refresh(case)

    # Recalculate statutory deadlines when procedural dates are updated
    recalculate_case_deadlines(real_id, db)
    check_statutory_deadlines(real_id, db)

    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="item.changed",
        item_type="case",
        item_id=str(real_id),
        summary=f"{current_user.full_name} updated case particulars & procedural dates",
        payload={"id": real_id, "title": case.title, "offence_section": case.offence_section}
    )

    return case


@router.patch("/cases/{case_id}/procedure", response_model=CaseOut)
def update_case_procedure(
    case_id: str,
    update: CaseProcedureUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates legal procedure dates (arrest, remand, FIR) and offence section.
    Synchronizes statutory deadlines and triggers legal warnings.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: You are not permitted to modify this case.")
        
    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    changes = []
    if update.fir_number is not None:
        case.fir_number = update.fir_number
        changes.append(f"FIR #{update.fir_number}")
    if update.fir_date is not None:
        case.fir_date = update.fir_date
        changes.append("FIR Date")
    if update.incident_date is not None:
        case.incident_date = update.incident_date
        changes.append("Incident Date")
    if update.arrest_date is not None:
        case.arrest_date = update.arrest_date
        changes.append("Arrest Date")
    if update.remand_date is not None:
        case.remand_date = update.remand_date
        changes.append("Remand Date")
    if update.offence_section is not None:
        case.offence_section = update.offence_section
        changes.append(f"Offence Section '{update.offence_section}'")
    if update.statutory_time_limit_days is not None:
        case.statutory_time_limit_days = update.statutory_time_limit_days
        changes.append(f"Statutory Limit {update.statutory_time_limit_days}d")

    db.commit()
    db.refresh(case)

    # Recalculate deadlines & check compliance
    recalculate_case_deadlines(real_id, db)
    check_statutory_deadlines(real_id, db)

    log_audit_event(
        db=db,
        action_type="PROCEDURE_DATES_UPDATED",
        target_type="case",
        target_id=str(real_id),
        description=f"Investigator {current_user.full_name} updated legal procedure parameters: {', '.join(changes) if changes else 'No changes'}.",
        case_id=real_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        commit=True
    )

    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="item.changed",
        item_type="case_procedure",
        item_id=str(real_id),
        summary=f"{current_user.full_name} updated procedural dates: {', '.join(changes)}",
        payload={"case_id": real_id, "offence_section": case.offence_section}
    )

    return case


@router.get("/cases/{case_id}/evidence-checklist", response_model=EvidenceChecklistResponse)
def get_case_evidence_checklist(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns standard forensic evidentiary checklist for the case's offence type.
    Flags expected exhibits that are missing to prevent fatal court trial defects.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        return evaluate_evidence_checklist(real_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/statutory-rules", response_model=List[StatutoryDeadlineRuleOut])
def list_statutory_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the legal expert-reviewed statutory deadline rules table.
    Enforces transparent legal references and prevents hardcoding in application logic.
    """
    ensure_comprehensive_statutory_rules(db)
    return db.query(StatutoryDeadlineRule).order_by(StatutoryDeadlineRule.limit_days.asc()).all()


@router.patch("/statutory-rules/{rule_id}", response_model=StatutoryDeadlineRuleOut)
def update_statutory_rule(
    rule_id: int,
    data: StatutoryDeadlineRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows Admin or Legal Advisor to update legal expert comments and statutory rule parameters.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Administrator can modify statutory rules.")

    rule = db.query(StatutoryDeadlineRule).filter(StatutoryDeadlineRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    if data.statute_name is not None:
        rule.statute_name = data.statute_name
    if data.section_reference is not None:
        rule.section_reference = data.section_reference
    if data.offence_category is not None:
        rule.offence_category = data.offence_category
    if data.limit_days is not None:
        rule.limit_days = data.limit_days
    if data.trigger_event is not None:
        rule.trigger_event = data.trigger_event
    if data.description is not None:
        rule.description = data.description
    if data.procedure_name is not None:
        rule.procedure_name = data.procedure_name
    if data.is_reviewed_by_expert is not None:
        rule.is_reviewed_by_expert = data.is_reviewed_by_expert
    if data.expert_reviewer is not None:
        rule.expert_reviewer = data.expert_reviewer
    if data.legal_notes is not None:
        rule.legal_notes = data.legal_notes

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/cases/{case_id}")
def delete_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "delete_case"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' cannot delete cases.")
    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Statutory Legal Hold Protection
    if getattr(case, "is_legal_hold", False):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Cannot delete Case #{real_id}: Active Legal Hold is in effect. Reason: '{case.legal_hold_reason or 'Statutory Evidentiary Preservation Order'}'. Destruction or deletion is prohibited by law."
        )

    db.delete(case)
    db.commit()
    return {"message": f"Case #{real_id} deleted successfully"}


@router.get("/cases/{case_id}/members", response_model=List[CaseMemberOut])
def get_case_members(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
        
    members = db.query(CaseMember).filter(CaseMember.case_id == real_id).all()
    results = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        results.append(CaseMemberOut(
            id=m.id,
            case_id=m.case_id,
            user_id=m.user_id,
            case_role=m.case_role or (u.role if u else "analyst"),
            user_name=u.full_name if u else "Unknown User",
            user_email=u.email if u else "",
            added_at=m.added_at,
            added_by=m.added_by
        ))
    return results


@router.post("/cases/{case_id}/members", response_model=CaseMemberOut)
def add_case_member(case_id: str, req: CaseMemberAddRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can add case members.")
        
    user_to_add = None
    if req.user_id:
        user_to_add = db.query(User).filter(User.id == req.user_id).first()
    elif req.email:
        user_to_add = db.query(User).filter(User.email == req.email.lower().strip()).first()
        
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found to add to case.")
        
    existing = db.query(CaseMember).filter(CaseMember.case_id == real_id, CaseMember.user_id == user_to_add.id).first()
    if existing:
        existing.case_role = req.case_role or existing.case_role or user_to_add.role
        db.commit()
        db.refresh(existing)
        return CaseMemberOut(
            id=existing.id,
            case_id=existing.case_id,
            user_id=existing.user_id,
            case_role=existing.case_role,
            user_name=user_to_add.full_name,
            user_email=user_to_add.email,
            added_at=existing.added_at,
            added_by=existing.added_by
        )
        
    new_m = CaseMember(
        case_id=real_id,
        user_id=user_to_add.id,
        case_role=req.case_role or user_to_add.role,
        added_by=current_user.full_name
    )
    db.add(new_m)
    db.commit()
    db.refresh(new_m)
    return CaseMemberOut(
        id=new_m.id,
        case_id=new_m.case_id,
        user_id=new_m.user_id,
        case_role=new_m.case_role,
        user_name=user_to_add.full_name,
        user_email=user_to_add.email,
        added_at=new_m.added_at,
        added_by=new_m.added_by
    )


@router.delete("/cases/{case_id}/members/{user_id}")
def remove_case_member(case_id: str, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can remove case members.")
        
    m = db.query(CaseMember).filter(CaseMember.case_id == real_id, CaseMember.user_id == user_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership record not found.")
        
    db.delete(m)
    db.commit()
    return {"status": "success", "message": f"User #{user_id} removed from case #{real_id}"}


@router.get("/cases/{case_id}/entities", response_model=List[EntityOut])
def get_entities(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(Entity).filter(Entity.case_id == real_id).all()


@router.get("/cases/{case_id}/events", response_model=List[EventOut])
def get_events(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(Event).filter(Event.case_id == real_id).all()

