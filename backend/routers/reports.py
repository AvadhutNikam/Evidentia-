"""
backend/routers/reports.py
Forensic Dossier, Court-Admissible PDF & Report Export Router.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Case, Evidence, Entity, Event, Hypothesis,
    Contradiction, CustodyLog, SourceCitation, EvidenceAssessment, User
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id

router = APIRouter(tags=["Case Reports & Dossier Export"])
logger = logging.getLogger("evidentia.reports")


@router.get("/cases/{case_id}/reports/pdf")
def export_case_pdf_report(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates and returns an authoritative, court-admissible vector PDF dossier.
    Includes:
    - Cover page with official insignia & 'decision support, not a conclusion' notice
    - Case summary & exhibit inventory with SHA-256 hashes and Sec 65B certification
    - Entities, relationships, and chronological timeline
    - Heuer ACH competing hypotheses with normalized scores & per-exhibit breakdown
    - Detected contradictions & testimonial conflicts
    - Heuer Step 6 Sensitivity analysis & critical pivot exhibits
    - Analyst overrides & rationales
    - Chain-of-custody summary & Merkle cryptographic audit ledger extract
    - Appendix of cited quotes with source locations
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    try:
        from report_generator import generate_case_pdf_report
        pdf_bytes = generate_case_pdf_report(real_case_id, db)
    except Exception as e:
        logger.error(f"Error generating PDF dossier for case {real_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF dossier: {str(e)}")

    # Record the export action in the tamper-evident Merkle audit ledger
    try:
        from audit_engine import log_audit_event
        log_audit_event(
            db=db,
            action_type="REPORT_EXPORT",
            target_type="case",
            target_id=str(real_case_id),
            description=f"Exported official PDF forensic dossier for Case #{real_case_id} ({len(pdf_bytes):,} bytes).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception as e:
        logger.warning(f"Could not log audit event for PDF export: {e}")

    safe_title = "".join(c for c in case.title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"Evidentia_Case_{real_case_id}_{safe_title[:30]}_Dossier.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get("/cases/{case_id}/reports/docket-data")
def get_case_docket_data(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the comprehensive compiled docket structure for client-side
    preview, verification, and interactive report rendering.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    evidence_list = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    entities = db.query(Entity).filter(Entity.case_id == real_case_id).all()
    events = db.query(Event).filter(Event.case_id == real_case_id).order_by(Event.timestamp.asc()).all()
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    contradictions = db.query(Contradiction).filter(Contradiction.case_id == real_case_id).all()
    custody_logs = db.query(CustodyLog).filter(CustodyLog.case_id == real_case_id).order_by(CustodyLog.timestamp.desc()).all()
    citations = db.query(SourceCitation).filter(SourceCitation.case_id == real_case_id).all()
    overrides = db.query(EvidenceAssessment).filter(EvidenceAssessment.analyst_override == True).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()

    from audit_engine import verify_audit_chain
    from scoring import calculate_three_layer_ach_scoring
    scoring_run = calculate_three_layer_ach_scoring(real_case_id, db)
    audit_chain = verify_audit_chain(db, case_id=real_case_id)

    return {
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "created_by": case.created_by,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "location": getattr(case, 'location', 'Crime Scene'),
            "victim": getattr(case, 'victim', 'N/A'),
            "priority": getattr(case, 'priority', 'High')
        },
        "stats": {
            "evidence_count": len(evidence_list),
            "entity_count": len(entities),
            "timeline_count": len(events),
            "hypothesis_count": len(hypotheses),
            "contradiction_count": len(contradictions),
            "citation_count": len(citations),
            "override_count": len(overrides)
        },
        "evidence": [
            {
                "id": ev.id,
                "file_name": ev.file_name,
                "evidence_type": ev.evidence_type,
                "file_hash": ev.file_hash,
                "hash_verified": ev.hash_verified,
                "sec_65b_certificate_present": ev.sec_65b_certificate_present,
                "chain_of_custody_complete": ev.chain_of_custody_complete,
                "source": ev.source
            } for ev in evidence_list
        ],
        "entities": [
            {
                "id": ent.id,
                "name": ent.name,
                "type": ent.type,
                "confidence": ent.confidence,
                "source_quote": getattr(ent, 'source_quote', None)
            } for ent in entities
        ],
        "events": [
            {
                "id": ev.id,
                "title": ev.title,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "description": ev.description,
                "location": ev.location,
                "evidence_id": ev.evidence_id
            } for ev in events
        ],
        "hypotheses": scoring_run.get("hypotheses", []),
        "breakdowns": scoring_run.get("hypothesis_breakdowns", {}),
        "robustness": scoring_run.get("robustness_ranges", {}),
        "contradictions": [
            {
                "id": c.id,
                "statement_a": c.statement_a,
                "statement_b": c.statement_b,
                "conflict_type": getattr(c, 'conflict_type', 'testimonial_conflict'),
                "severity": getattr(c, 'severity', 'high')
            } for c in contradictions
        ],
        "audit_chain": audit_chain
    }

