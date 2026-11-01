"""
backend/routers/case_file.py
============================
Unified API Router for Police-Shaped Case File Architecture (5 Tabs):
1. Particulars: Police station, IO/Supervisor, Court, Next Hearing, Consistency Checks.
2. People: Case Persons, Encrypted PII, Accused Status History, Per-Accused Clocks, Statement Improvements.
3. Documents: Document Type Registry, Typed Panchnamas & Memos, Gap Engine.
4. Diary: Section 192 BNSS Case Diary, Auto-Draft from Audit Trail, Digital Signing & Lock.
5. Sections: BNS/IPC Sections Register, Elements Proof Checklist, Recalculation.
"""

import json
import re
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import (
    Case, Evidence, AuditLog, User, PoliceStationLookup, CasePerson,
    AccusedStatusHistory, PersonStatement, DocumentTypeDefinition,
    CaseDiaryEntry, CaseSection, SectionElement, CaseDeadline
)
from schemas import (
    CaseParticularsUpdate, PoliceStationLookupOut,
    CasePersonCreate, CasePersonUpdate, CasePersonOut,
    AccusedStatusHistoryCreate, AccusedStatusHistoryOut,
    PersonStatementCreate, PersonStatementOut,
    DocumentTypeDefinitionOut, TypedDocumentUpdate, DocumentGapReportOut,
    CaseDiaryEntryCreate, CaseDiaryEntryUpdate, CaseDiaryEntryOut,
    CaseSectionCreate, CaseSectionUpdate, CaseSectionOut, SectionElementOut,
    FIRImportRequest, FIRImportResponseOut
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from security_encryption import encrypt_field, decrypt_field
from procedure_engine import recalculate_case_deadlines
from collaboration import publish_collaboration_event
from audit_engine import log_audit_event
from police_case_file_engine import (
    ensure_document_type_definitions,
    ensure_police_station_lookups,
    evaluate_document_completeness,
    generate_case_diary_auto_draft,
    digitally_sign_diary_entry,
    analyze_person_statement_improvements,
    sync_case_sections_from_offence_text,
    recalculate_sections_statutory_impact,
    get_per_accused_statutory_clocks,
    PENAL_SECTIONS_DATABASE
)

router = APIRouter(tags=["Police Case File Architecture"])


# ==============================================================================
# TAB 1: PARTICULARS & CONSISTENCY CHECKS
# ==============================================================================

@router.get("/police-stations", response_model=List[PoliceStationLookupOut])
def get_police_stations_directory(db: Session = Depends(get_db)):
    """Returns directory of standard police stations and districts."""
    ensure_police_station_lookups(db)
    return db.query(PoliceStationLookup).order_by(PoliceStationLookup.district, PoliceStationLookup.name).all()


@router.get("/cases/{case_id}/particulars")
def get_case_particulars_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns case header particulars, officer roles, court hearing details,
    per-accused custody status, and consistency check warnings.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to case particulars.")

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Consistency Checks (Warnings, not blocking errors)
    warnings = []
    if case.incident_date and case.fir_date and case.fir_date < case.incident_date:
        warnings.append("FIR registration date is recorded as earlier than the incident occurrence date.")
    if case.arrest_date and case.incident_date and case.arrest_date < case.incident_date:
        warnings.append("Arrest date is recorded as earlier than the incident occurrence date.")
    if case.arrest_date and case.remand_date and case.remand_date < case.arrest_date:
        warnings.append("Remand date is recorded as prior to the initial arrest date.")
    if not case.crime_number:
        warnings.append("Formal Crime Number (CR No.) is not yet assigned by the police station.")
    if not case.investigating_officer_name and not case.investigating_officer_id:
        warnings.append("No Investigating Officer (IO) is currently assigned to this docket.")

    # Accused clocks
    accused_clocks = get_per_accused_statutory_clocks(real_id, db)

    return {
        "case_id": case.id,
        "title": case.title,
        "fir_number": case.fir_number,
        "crime_number": case.crime_number,
        "police_station": case.police_station,
        "district": case.district,
        "state": case.state or "Maharashtra",
        "investigating_officer_id": case.investigating_officer_id,
        "investigating_officer_name": case.investigating_officer_name or (case.investigating_officer.full_name if case.investigating_officer_id and hasattr(case, 'investigating_officer') else None),
        "supervising_officer_id": case.supervising_officer_id,
        "supervising_officer_name": case.supervising_officer_name,
        "court_name": case.court_name,
        "next_hearing_date": case.next_hearing_date.isoformat() if case.next_hearing_date else None,
        "next_hearing_purpose": case.next_hearing_purpose,
        "bail_status": case.bail_status or "None",
        "custody_status": case.custody_status or "Under Investigation",
        "case_stage": case.case_stage or "under_investigation",
        "fir_date": case.fir_date.isoformat() if case.fir_date else None,
        "incident_date": case.incident_date.isoformat() if case.incident_date else None,
        "arrest_date": case.arrest_date.isoformat() if case.arrest_date else None,
        "remand_date": case.remand_date.isoformat() if case.remand_date else None,
        "offence_section": case.offence_section,
        "statutory_time_limit_days": case.statutory_time_limit_days or 90,
        "version": case.version,
        "consistency_warnings": warnings,
        "per_accused_clocks": accused_clocks
    }


@router.patch("/cases/{case_id}/particulars")
def update_case_particulars_endpoint(
    case_id: str,
    payload: CaseParticularsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates case particulars with optimistic concurrency check,
    writes before/after diff to audit logs, and synchronizes statutory deadlines.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to edit case particulars.")

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Optimistic concurrency check
    if payload.expected_version is not None and payload.expected_version != case.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict detected. Case particulars modified by another officer. Current version: {case.version}."
        )

    changes = []
    update_data = payload.dict(exclude_unset=True)
    update_data.pop("expected_version", None)

    for field, new_val in update_data.items():
        old_val = getattr(case, field, None)
        if old_val != new_val:
            setattr(case, field, new_val)
            changes.append(f"{field}: '{old_val}' -> '{new_val}'")

    if changes:
        case.version += 1
        case.updated_at = datetime.now(timezone.utc)

        # Record audit log
        log_audit_event(
            db=db,
            action_type="CASE_PARTICULARS_UPDATED",
            target_type="case",
            target_id=str(case.id),
            description=f"Updated particulars: {'; '.join(changes[:5])}",
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            user_role=current_user.role,
            case_id=case.id,
            commit=False
        )

        # Synchronize court hearing deadline if updated
        if "next_hearing_date" in update_data and case.next_hearing_date:
            hearing_deadline = db.query(CaseDeadline).filter(
                CaseDeadline.case_id == case.id,
                CaseDeadline.title.like("Court Hearing%")
            ).first()

            hearing_title = f"Court Hearing ({case.court_name or 'Trial Court'}): {case.next_hearing_purpose or 'Scheduled Proceedings'}"
            if hearing_deadline:
                hearing_deadline.due_date = case.next_hearing_date
                hearing_deadline.title = hearing_title
            else:
                db.add(CaseDeadline(
                    case_id=case.id,
                    title=hearing_title,
                    due_date=case.next_hearing_date,
                    status="pending"
                ))

        db.commit()
        db.refresh(case)

        # Broadcast live update
        publish_collaboration_event(
            db=db,
            case_id=case.id,
            event_type="case_particulars_updated",
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            payload={"version": case.version, "changes": changes}
        )

    return {"message": "Case particulars updated successfully.", "version": case.version, "changes_count": len(changes)}


# ==============================================================================
# TAB 2: PEOPLE REGISTER, ACCUSED CLOCKS & STATEMENTS
# ==============================================================================

@router.get("/cases/{case_id}/persons", response_model=List[CasePersonOut])
def list_case_persons_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lists all persons registered on the case.
    Contact info and address are decrypted for Lead IO / Admin, and masked for reviewers.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    can_view_pii = current_user.role in ["admin", "lead_investigator"]
    persons = db.query(CasePerson).filter(CasePerson.case_id == real_id).order_by(CasePerson.role, CasePerson.name).all()

    result = []
    for p in persons:
        # Decrypt or mask contact info
        contact = decrypt_field(p.contact_info) if p.contact_info else None
        address = decrypt_field(p.address) if p.address else None
        if not can_view_pii:
            contact = "[RESTRICTED - INVESTIGATOR CLEARANCE REQUIRED]" if contact else None
            address = "[RESTRICTED - PII WITNESS PROTECTION]" if address else None

        statements_count = db.query(PersonStatement).filter(PersonStatement.person_id == p.id).count()

        latest_status = None
        if p.role == "accused":
            latest_rec = db.query(AccusedStatusHistory).filter(
                AccusedStatusHistory.person_id == p.id
            ).order_by(AccusedStatusHistory.status_date.desc()).first()
            if latest_rec:
                latest_status = latest_rec.status

        result.append(CasePersonOut(
            id=p.id,
            case_id=p.case_id,
            name=p.name,
            aliases=p.aliases,
            role=p.role,
            father_or_spouse_name=p.father_or_spouse_name,
            age=p.age,
            gender=p.gender,
            contact_info=contact,
            address=address,
            is_important=p.is_important,
            linked_entity_id=p.linked_entity_id,
            notes=p.notes,
            statements_count=statements_count,
            latest_status=latest_status,
            created_at=p.created_at
        ))

    return result


@router.post("/cases/{case_id}/persons", response_model=CasePersonOut)
def create_case_person_endpoint(
    case_id: str,
    payload: CasePersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adds a new person to the master police register with encrypted PII."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to add persons.")

    encrypted_contact = encrypt_field(payload.contact_info) if payload.contact_info else None
    encrypted_address = encrypt_field(payload.address) if payload.address else None

    person = CasePerson(
        case_id=real_id,
        name=payload.name.strip(),
        aliases=payload.aliases.strip() if payload.aliases else None,
        role=payload.role,
        father_or_spouse_name=payload.father_or_spouse_name,
        age=payload.age,
        gender=payload.gender,
        contact_info=encrypted_contact,
        address=encrypted_address,
        is_important=payload.is_important or False,
        linked_entity_id=payload.linked_entity_id,
        notes=payload.notes
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    # If role is accused, seed initial status record
    if person.role == "accused":
        db.add(AccusedStatusHistory(
            case_id=real_id,
            person_id=person.id,
            status="not_identified" if "unknown" in person.name.lower() else "arrested",
            status_date=datetime.now(timezone.utc),
            order_reference="Initial FIR Docket Accused Entry"
        ))
        db.commit()

    return CasePersonOut(
        id=person.id,
        case_id=person.case_id,
        name=person.name,
        aliases=person.aliases,
        role=person.role,
        father_or_spouse_name=person.father_or_spouse_name,
        age=person.age,
        gender=person.gender,
        contact_info=payload.contact_info,
        address=payload.address,
        is_important=person.is_important,
        linked_entity_id=person.linked_entity_id,
        notes=person.notes,
        statements_count=0,
        latest_status="arrested" if person.role == "accused" else None,
        created_at=person.created_at
    )


@router.get("/cases/{case_id}/accused-clocks")
def get_accused_clocks_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns statutory default-bail and custody remand clocks calculated per accused individual."""
    real_id = resolve_case_id(case_id, db)
    return get_per_accused_statutory_clocks(real_id, db)


@router.post("/cases/{case_id}/accused-status", response_model=AccusedStatusHistoryOut)
def record_accused_status_endpoint(
    case_id: str,
    payload: AccusedStatusHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Records a change in custody or bail status for an accused."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to log accused status.")

    person = db.query(CasePerson).filter(CasePerson.id == payload.person_id, CasePerson.case_id == real_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Accused person record not found.")

    rec = AccusedStatusHistory(
        case_id=real_id,
        person_id=payload.person_id,
        status=payload.status,
        status_date=payload.status_date,
        order_reference=payload.order_reference,
        custody_days_served=payload.custody_days_served or 0,
        remand_expiry_date=payload.remand_expiry_date,
        statutory_filing_deadline=payload.statutory_filing_deadline,
        notes=payload.notes
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Recalculate statutory deadlines
    recalculate_case_deadlines(real_id, db)

    return AccusedStatusHistoryOut(
        id=rec.id,
        case_id=rec.case_id,
        person_id=rec.person_id,
        person_name=person.name,
        status=rec.status,
        status_date=rec.status_date,
        order_reference=rec.order_reference,
        custody_days_served=rec.custody_days_served,
        remand_expiry_date=rec.remand_expiry_date,
        statutory_filing_deadline=rec.statutory_filing_deadline,
        notes=rec.notes,
        created_at=rec.created_at
    )


@router.get("/cases/{case_id}/person-statements", response_model=List[PersonStatementOut])
def list_person_statements_endpoint(
    case_id: str,
    person_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists recorded witness & accused statements."""
    real_id = resolve_case_id(case_id, db)
    query = db.query(PersonStatement).filter(PersonStatement.case_id == real_id)
    if person_id:
        query = query.filter(PersonStatement.person_id == person_id)

    statements = query.order_by(PersonStatement.statement_date.desc()).all()
    results = []
    for s in statements:
        p_name = s.person.name if s.person else None
        results.append(PersonStatementOut(
            id=s.id,
            case_id=s.case_id,
            person_id=s.person_id,
            person_name=p_name,
            statement_type=s.statement_type,
            status=s.status,
            statement_date=s.statement_date,
            statement_time=s.statement_time,
            place=s.place,
            recorded_by=s.recorded_by,
            language=s.language,
            read_over_and_signed=s.read_over_and_signed,
            magistrate_name=s.magistrate_name,
            linked_evidence_id=s.linked_evidence_id,
            linked_interview_id=s.linked_interview_id,
            statement_text=s.statement_text,
            key_claims=s.key_claims,
            notes=s.notes,
            created_at=s.created_at
        ))
    return results


@router.post("/cases/{case_id}/person-statements", response_model=PersonStatementOut)
def record_person_statement_endpoint(
    case_id: str,
    payload: PersonStatementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Logs a new statement under Section 180 BNSS / 161 CrPC or Section 183 BNSS / 164 CrPC."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to log statements.")

    person = db.query(CasePerson).filter(CasePerson.id == payload.person_id, CasePerson.case_id == real_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person record not found.")

    st = PersonStatement(
        case_id=real_id,
        person_id=payload.person_id,
        statement_type=payload.statement_type,
        status=payload.status,
        statement_date=payload.statement_date,
        statement_time=payload.statement_time,
        place=payload.place,
        recorded_by=payload.recorded_by or current_user.full_name or current_user.email,
        language=payload.language or "Marathi",
        read_over_and_signed=payload.read_over_and_signed if payload.read_over_and_signed is not None else True,
        magistrate_name=payload.magistrate_name,
        linked_evidence_id=payload.linked_evidence_id,
        linked_interview_id=payload.linked_interview_id,
        statement_text=payload.statement_text,
        key_claims=payload.key_claims,
        notes=payload.notes
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    return PersonStatementOut(
        id=st.id,
        case_id=st.case_id,
        person_id=st.person_id,
        person_name=person.name,
        statement_type=st.statement_type,
        status=st.status,
        statement_date=st.statement_date,
        statement_time=st.statement_time,
        place=st.place,
        recorded_by=st.recorded_by,
        language=st.language,
        read_over_and_signed=st.read_over_and_signed,
        magistrate_name=st.magistrate_name,
        linked_evidence_id=st.linked_evidence_id,
        linked_interview_id=st.linked_interview_id,
        statement_text=st.statement_text,
        key_claims=st.key_claims,
        notes=st.notes,
        created_at=st.created_at
    )


@router.get("/cases/{case_id}/persons/{person_id}/statement-improvements")
def get_statement_improvements_endpoint(
    case_id: str,
    person_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compares statements by the same person across dates to flag additions and omissions."""
    real_id = resolve_case_id(case_id, db)
    return analyze_person_statement_improvements(real_id, person_id, db)


# ==============================================================================
# TAB 3: TYPED DOCUMENTS & GAP ENGINE
# ==============================================================================

@router.get("/document-types", response_model=List[DocumentTypeDefinitionOut])
def get_document_type_definitions(db: Session = Depends(get_db)):
    """Returns registry of 10 standard police document schemas."""
    ensure_document_type_definitions(db)
    docs = db.query(DocumentTypeDefinition).order_by(DocumentTypeDefinition.category, DocumentTypeDefinition.label).all()
    out = []
    for d in docs:
        fields = json.loads(d.required_fields_json) if d.required_fields_json else []
        out.append(DocumentTypeDefinitionOut(
            id=d.id,
            code=d.code,
            label=d.label,
            legal_provision=d.legal_provision,
            category=d.category,
            required_fields=fields,
            standard_guidance=d.standard_guidance
        ))
    return out


@router.get("/cases/{case_id}/typed-documents")
def list_typed_documents_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all exhibits with their assigned document type, structured details, and completeness gap analysis."""
    real_id = resolve_case_id(case_id, db)
    ensure_document_type_definitions(db)

    ev_list = db.query(Evidence).filter(
        Evidence.case_id == real_id,
        Evidence.is_deleted == False
    ).order_by(Evidence.id.asc()).all()

    results = []
    for ev in ev_list:
        doc_type = ev.document_type or "unclassified"
        details_dict = {}
        if ev.type_details:
            try:
                details_dict = json.loads(ev.type_details)
            except Exception:
                pass

        gap_report = evaluate_document_completeness(doc_type, details_dict, db)

        results.append({
            "evidence_id": ev.id,
            "file_name": ev.file_name,
            "evidence_type": ev.evidence_type,
            "document_type": doc_type,
            "type_details": details_dict,
            "completeness_pct": gap_report["completeness_pct"],
            "is_complete": gap_report["is_complete"],
            "missing_required_fields": gap_report["missing_required_fields"],
            "gap_reasons": gap_report["gap_reasons"],
            "legal_guidance": gap_report["legal_guidance"],
            "upload_date": ev.upload_date.isoformat() if ev.upload_date else None
        })

    return results


@router.patch("/cases/{case_id}/evidence/{evidence_id}/typed-document")
def update_typed_document_endpoint(
    case_id: str,
    evidence_id: int,
    payload: TypedDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assigns or updates structured details for an exhibit (e.g. Seizure Memo, Panchnama, Arrest Memo),
    computes completeness, and adjusts exhibit reliability.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Unauthorized to classify documents.")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.case_id == real_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Exhibit not found.")

    ev.document_type = payload.document_type
    ev.type_details = json.dumps(payload.type_details)

    # Evaluate completeness
    gap_report = evaluate_document_completeness(payload.document_type, payload.type_details, db)

    db.commit()
    db.refresh(ev)

    return {
        "evidence_id": ev.id,
        "document_type": ev.document_type,
        "completeness_pct": gap_report["completeness_pct"],
        "is_complete": gap_report["is_complete"],
        "missing_required_fields": gap_report["missing_required_fields"],
        "gap_reasons": gap_report["gap_reasons"],
        "message": f"Exhibit #{ev.id} structured as {payload.document_type} ({gap_report['completeness_pct']}% complete)."
    }


# ==============================================================================
# TAB 4: CASE DIARY (ROZNAMCHA - Section 192 BNSS / 172 CrPC)
# ==============================================================================

@router.get("/cases/{case_id}/diary", response_model=List[CaseDiaryEntryOut])
def list_case_diary_entries_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all daily investigation diary entries for the case."""
    real_id = resolve_case_id(case_id, db)
    entries = db.query(CaseDiaryEntry).filter(
        CaseDiaryEntry.case_id == real_id
    ).order_by(CaseDiaryEntry.entry_date.desc(), CaseDiaryEntry.serial_number.asc()).all()

    out = []
    for e in entries:
        out.append(CaseDiaryEntryOut(
            id=e.id,
            case_id=e.case_id,
            entry_date=e.entry_date,
            serial_number=e.serial_number,
            time_from=e.time_from,
            time_to=e.time_to,
            place=e.place,
            officer_id=e.officer_id,
            officer_name=e.officer_name,
            activities=e.activities,
            persons_examined=json.loads(e.persons_examined_json) if e.persons_examined_json else [],
            places_visited=json.loads(e.places_visited_json) if e.places_visited_json else [],
            items_seized=json.loads(e.items_seized_json) if e.items_seized_json else [],
            instructions_given=e.instructions_given,
            next_steps=e.next_steps,
            status=e.status,
            signature_timestamp=e.signature_timestamp,
            signature_hash=e.signature_hash,
            supervisor_notes=e.supervisor_notes,
            created_at=e.created_at,
            updated_at=e.updated_at
        ))
    return out


@router.get("/cases/{case_id}/diary/auto-draft")
def get_case_diary_auto_draft_endpoint(
    case_id: str,
    entry_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-drafts daily investigation diary entry by querying audit logs, evidence, and statements."""
    real_id = resolve_case_id(case_id, db)
    parsed_date = date.fromisoformat(entry_date) if entry_date else date.today()
    return generate_case_diary_auto_draft(real_id, parsed_date, current_user, db)


@router.post("/cases/{case_id}/diary", response_model=CaseDiaryEntryOut)
def create_case_diary_entry_endpoint(
    case_id: str,
    payload: CaseDiaryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new Case Diary (Roznamcha) draft entry."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to create diary entries.")

    entry = CaseDiaryEntry(
        case_id=real_id,
        entry_date=payload.entry_date,
        serial_number=payload.serial_number or 1,
        time_from=payload.time_from,
        time_to=payload.time_to,
        place=payload.place,
        officer_id=current_user.id,
        officer_name=payload.officer_name or current_user.full_name or current_user.email,
        activities=payload.activities,
        persons_examined_json=payload.persons_examined_json,
        places_visited_json=payload.places_visited_json,
        items_seized_json=payload.items_seized_json,
        instructions_given=payload.instructions_given,
        next_steps=payload.next_steps,
        status="draft",
        parent_entry_id=payload.parent_entry_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return CaseDiaryEntryOut(
        id=entry.id,
        case_id=entry.case_id,
        entry_date=entry.entry_date,
        serial_number=entry.serial_number,
        time_from=entry.time_from,
        time_to=entry.time_to,
        place=entry.place,
        officer_id=entry.officer_id,
        officer_name=entry.officer_name,
        activities=entry.activities,
        persons_examined=json.loads(entry.persons_examined_json) if entry.persons_examined_json else [],
        places_visited=json.loads(entry.places_visited_json) if entry.places_visited_json else [],
        items_seized=json.loads(entry.items_seized_json) if entry.items_seized_json else [],
        instructions_given=entry.instructions_given,
        next_steps=entry.next_steps,
        status=entry.status,
        created_at=entry.created_at,
        updated_at=entry.updated_at
    )


@router.post("/cases/{case_id}/diary/{entry_id}/sign", response_model=CaseDiaryEntryOut)
def sign_case_diary_entry_endpoint(
    case_id: str,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Digitally signs and locks a diary entry. Creates tamper-evident SHA-256 hash."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to sign diary entries.")

    entry = db.query(CaseDiaryEntry).filter(CaseDiaryEntry.id == entry_id, CaseDiaryEntry.case_id == real_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found.")

    try:
        signed_entry = digitally_sign_diary_entry(entry, current_user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CaseDiaryEntryOut(
        id=signed_entry.id,
        case_id=signed_entry.case_id,
        entry_date=signed_entry.entry_date,
        serial_number=signed_entry.serial_number,
        time_from=signed_entry.time_from,
        time_to=signed_entry.time_to,
        place=signed_entry.place,
        officer_id=signed_entry.officer_id,
        officer_name=signed_entry.officer_name,
        activities=signed_entry.activities,
        persons_examined=json.loads(signed_entry.persons_examined_json) if signed_entry.persons_examined_json else [],
        places_visited=json.loads(signed_entry.places_visited_json) if signed_entry.places_visited_json else [],
        items_seized=json.loads(signed_entry.items_seized_json) if signed_entry.items_seized_json else [],
        instructions_given=signed_entry.instructions_given,
        next_steps=signed_entry.next_steps,
        status=signed_entry.status,
        signature_timestamp=signed_entry.signature_timestamp,
        signature_hash=signed_entry.signature_hash,
        supervisor_notes=signed_entry.supervisor_notes,
        created_at=signed_entry.created_at,
        updated_at=signed_entry.updated_at
    )


# ==============================================================================
# TAB 5: SECTIONS ADDED / DROPPED & ELEMENTS PROOF MATRIX
# ==============================================================================

@router.get("/cases/{case_id}/sections", response_model=List[CaseSectionOut])
def list_case_sections_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists active and proposed penal sections with element proof matrix."""
    real_id = resolve_case_id(case_id, db)
    sync_case_sections_from_offence_text(real_id, db)
    sections = db.query(CaseSection).filter(CaseSection.case_id == real_id).order_by(CaseSection.id.asc()).all()

    out = []
    for s in sections:
        elements_out = []
        for e in s.elements:
            ev_ids = json.loads(e.supporting_evidence_ids) if e.supporting_evidence_ids else []
            elements_out.append(SectionElementOut(
                id=e.id,
                case_section_id=e.case_section_id,
                element_text=e.element_text,
                supporting_evidence_ids=ev_ids,
                status=e.status,
                notes=e.notes
            ))
        out.append(CaseSectionOut(
            id=s.id,
            case_id=s.case_id,
            act=s.act,
            section_code=s.section_code,
            description=s.description,
            punishment_tier=s.punishment_tier,
            status=s.status,
            reason=s.reason,
            deciding_officer=s.deciding_officer,
            effective_date=s.effective_date,
            supervisor_approval=s.supervisor_approval,
            supervisor_notes=s.supervisor_notes,
            court_informed_date=s.court_informed_date,
            court_intimation_memo=s.court_intimation_memo,
            elements=elements_out,
            created_at=s.created_at
        ))
    return out


@router.post("/cases/{case_id}/sections", response_model=CaseSectionOut)
def add_case_section_endpoint(
    case_id: str,
    payload: CaseSectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adds a newly proposed or added penal section. Recalculates statutory time limit."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized to alter penal sections.")

    sec = CaseSection(
        case_id=real_id,
        act=payload.act,
        section_code=payload.section_code,
        description=payload.description,
        punishment_tier=payload.punishment_tier or "life_or_death_over_10_years",
        status=payload.status or "added",
        reason=payload.reason,
        deciding_officer=payload.deciding_officer or current_user.full_name or current_user.email,
        effective_date=datetime.now(timezone.utc),
        supervisor_approval=True,
        court_informed_date=payload.court_informed_date,
        court_intimation_memo=payload.court_intimation_memo
    )
    db.add(sec)
    db.commit()
    db.refresh(sec)

    # Recalculate 60 vs 90 days statutory limit
    recalculate_sections_statutory_impact(real_id, db)

    return CaseSectionOut(
        id=sec.id,
        case_id=sec.case_id,
        act=sec.act,
        section_code=sec.section_code,
        description=sec.description,
        punishment_tier=sec.punishment_tier,
        status=sec.status,
        reason=sec.reason,
        deciding_officer=sec.deciding_officer,
        effective_date=sec.effective_date,
        supervisor_approval=sec.supervisor_approval,
        court_informed_date=sec.court_informed_date,
        court_intimation_memo=sec.court_intimation_memo,
        elements=[],
        created_at=sec.created_at
    )


@router.patch("/cases/{case_id}/sections/{section_id}")
def update_case_section_endpoint(
    case_id: str,
    section_id: int,
    payload: CaseSectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates section status (added, dropped), supervisor approval, and court intimation memo."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Unauthorized.")

    sec = db.query(CaseSection).filter(CaseSection.id == section_id, CaseSection.case_id == real_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found.")

    if payload.status:
        sec.status = payload.status
    if payload.reason:
        sec.reason = payload.reason
    if payload.supervisor_approval is not None:
        sec.supervisor_approval = payload.supervisor_approval
    if payload.supervisor_notes:
        sec.supervisor_notes = payload.supervisor_notes
    if payload.court_informed_date:
        sec.court_informed_date = payload.court_informed_date
    if payload.court_intimation_memo:
        sec.court_intimation_memo = payload.court_intimation_memo

    db.commit()

    # Recalculate statutory limit
    recalc = recalculate_sections_statutory_impact(real_id, db)

    return {"message": f"Section {sec.section_code} updated.", "recalculation": recalc}


# ==============================================================================
# FIR IMPORT ENGINE (REDUCE TYPING)
# ==============================================================================

@router.post("/cases/{case_id}/fir-import", response_model=FIRImportResponseOut)
def import_fir_text_endpoint(
    case_id: str,
    payload: FIRImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parses pasted or OCR'd FIR copy. Extracts Header, Complainant, Accused, Sections,
    Incident Date, and pre-populates the case docket.
    """
    real_id = resolve_case_id(case_id, db)
    text = payload.fir_text

    # Extraction regexes
    fir_match = re.search(r"(?:FIR\s*(?:No\.?|Number)|First\s*Information\s*Report\s*No\.?)[:\s]+([A-Z0-9\/\-]+)", text, re.IGNORECASE)
    ps_match = re.search(r"(?:Police\s*Station|P\.S\.)[:\s]+([A-Za-z\s]+?)(?:District|,|\n)", text, re.IGNORECASE)
    dist_match = re.search(r"(?:District|Dist\.)[:\s]+([A-Za-z\s]+?)(?:State|,|\n)", text, re.IGNORECASE)
    complainant_match = re.search(r"(?:Complainant|Informant|Name\s*of\s*Complainant)[:\s]+([A-Za-z\s]+?)(?:Age|S\/o|W\/o|Address|,|\n)", text, re.IGNORECASE)
    accused_matches = re.findall(r"(?:Accused|Suspect)(?:\s*(?:No\.?\s*\d|Name))?[:\s]+([A-Za-z\s]+?)(?:Age|S\/o|W\/o|Address|,|\n)", text, re.IGNORECASE)

    extracted_sections = []
    for s_code in ["302", "307", "376", "392", "420", "120B", "34", "103", "109", "64", "309", "318", "61"]:
        if re.search(rf"\b{s_code}\b", text):
            extracted_sections.append(s_code)

    resp = FIRImportResponseOut(
        fir_number=fir_match.group(1).strip() if fir_match else None,
        police_station=ps_match.group(1).strip() if ps_match else None,
        district=dist_match.group(1).strip() if dist_match else None,
        complainant_name=complainant_match.group(1).strip() if complainant_match else None,
        accused_names=[a.strip() for a in accused_matches if len(a.strip()) > 2],
        sections=list(set(extracted_sections)),
        brief_facts=text[:300] + ("..." if len(text) > 300 else "")
    )

    if payload.auto_save and check_case_access(real_id, current_user, db, "edit_case"):
        case = db.query(Case).filter(Case.id == real_id).first()
        if case:
            if resp.fir_number and not case.fir_number:
                case.fir_number = resp.fir_number
            if resp.police_station and not case.police_station:
                case.police_station = resp.police_station
            if resp.district and not case.district:
                case.district = resp.district
            db.commit()

        # Seed Complainant if found
        if resp.complainant_name:
            exists = db.query(CasePerson).filter(CasePerson.case_id == real_id, CasePerson.name == resp.complainant_name).first()
            if not exists:
                db.add(CasePerson(case_id=real_id, name=resp.complainant_name, role="complainant", is_important=True))

        # Seed Accused if found
        for acc in resp.accused_names:
            exists = db.query(CasePerson).filter(CasePerson.case_id == real_id, CasePerson.name == acc).first()
            if not exists:
                db.add(CasePerson(case_id=real_id, name=acc, role="accused", is_important=True))

        db.commit()

    return resp
