"""
backend/routers/telecom_financial.py
Telecommunications (CDR / Tower-Dump) and Forensic Financial Analytics Router.

Endpoints:
- GET /cases/{case_id}/cdr/analytics: Comprehensive telecom analytics (co-location, common contacts, burner numbers, impossible travel).
- POST /cases/{case_id}/cdr/import: Ingest CDR or Tower Dump (CSV / Excel).
- GET /cases/{case_id}/cdr/records: Paginated and filterable CDR records.
- GET /cases/{case_id}/cdr/co-locations: Detect handsets in the same cell sector at the same time.
- GET /cases/{case_id}/cdr/common-contacts: Identify bridge conspirators shared across suspects.
- GET /cases/{case_id}/cdr/short-lived: Discover burner SIM cards active for brief windows.
- GET /cases/{case_id}/cdr/impossible-travel: Flag physical velocity anomalies between tower hits.
- POST /cases/{case_id}/financial/import: Ingest bank account statement (CSV / Excel).
- GET /cases/{case_id}/financial/transactions: Paginated bank statement ledger.
- GET /cases/{case_id}/financial/money-flow: Directed money-flow graph, smurfing/structuring, and rapid layering alerts.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models import Case, User, CDRRecord, BankTransaction
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from schemas import (
    CDRRecordOut,
    BankTransactionOut,
    CoLocationEventOut,
    CommonContactOut,
    ShortLivedNumberOut,
    ImpossibleTravelOut,
    CDRAnalyticsOverviewOut,
    MoneyFlowAnalysisOut
)
from cdr_financial_engine import (
    parse_and_store_cdr,
    parse_and_store_bank_statement,
    analyze_co_location,
    analyze_common_contacts,
    analyze_short_lived_numbers,
    analyze_impossible_travel,
    analyze_money_flow,
    run_live_cdr_and_financial_analytics
)
from audit_engine import log_audit_event

router = APIRouter(tags=["CDR & Financial Analytics"])
logger = logging.getLogger("evidentia.telecom_financial")


# ==============================================================================
# CDR ANALYTICS ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/cdr/analytics", response_model=CDRAnalyticsOverviewOut)
def get_cdr_analytics_overview(
    case_id: Any,
    window_minutes: int = Query(15, ge=1, le=120, description="Co-location time window in minutes"),
    speed_threshold: float = Query(160.0, ge=50.0, description="Impossible travel speed threshold in km/h"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns an aggregated telecommunications intelligence package:
    - Co-location events linking handsets in identical cell sectors
    - Common contact bridge numbers
    - Short-lived / burner SIM candidates
    - Velocity impossible travel alerts
    - Sample records with line citations
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    records = db.query(CDRRecord).filter(CDRRecord.case_id == real_case_id).order_by(CDRRecord.call_datetime.desc()).all()
    total_recs = len(records)
    unique_callers = len(set(r.calling_number for r in records))
    unique_towers = len(set(r.cell_id for r in records))

    colocations = analyze_co_location(real_case_id, db, window_minutes=window_minutes)
    common_contacts = analyze_common_contacts(real_case_id, db)
    burners = analyze_short_lived_numbers(real_case_id, db)
    impossible_travel = analyze_impossible_travel(real_case_id, db, speed_threshold_kmh=speed_threshold)

    return {
        "case_id": real_case_id,
        "total_records": total_recs,
        "unique_callers": unique_callers,
        "unique_towers": unique_towers,
        "co_location_events": colocations,
        "common_contacts": common_contacts,
        "short_lived_numbers": burners,
        "impossible_travel": impossible_travel,
        "records_sample": records[:50]
    }


@router.post("/cases/{case_id}/cdr/import")
async def import_cdr_file(
    case_id: Any,
    file: UploadFile = File(...),
    evidence_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parses and stores CDR or Tower-Dump CSV or Excel files (.xlsx).
    Every single row is mapped to its exact line number and stored with normalization.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=403, detail="Permission denied to add evidence to this case.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        res = parse_and_store_cdr(
            file_content=content,
            file_name=file.filename or "uploaded_cdr.csv",
            case_id=real_case_id,
            evidence_id=evidence_id,
            db=db
        )

        user_ident = getattr(current_user, "full_name", None) or getattr(current_user, "email", str(current_user.id))
        log_audit_event(
            db=db,
            action_type="CDR_FILE_IMPORTED",
            target_type="cdr_records",
            target_id=str(evidence_id or "batch"),
            description=f"Imported {res.get('parsed_records', 0)} CDR rows from '{file.filename}' by {user_ident}.",
            user_id=current_user.id,
            user_name=user_ident,
            user_role=getattr(current_user, "role", "analyst"),
            case_id=real_case_id
        )

        # Automated Live Analytics: co-location, common-contacts, burner numbers, impossible travel, and watchlists
        try:
            live_res = run_live_cdr_and_financial_analytics(
                case_id=real_case_id,
                db=db,
                file_name=file.filename or "uploaded_cdr.csv",
                user_id=current_user.id
            )
            res["live_analysis"] = live_res
        except Exception as lae:
            logger.warning(f"Automated live analysis notice: {lae}")

        # Real-time Cross-Case Matching across permitted cases
        try:
            from cross_case_engine import match_exhibit_cross_case_realtime
            match_exhibit_cross_case_realtime(
                evidence_id=evidence_id,
                user=current_user,
                db=db,
                case_id=real_case_id,
                file_name=file.filename
            )
        except Exception as cce:
            logger.warning(f"[CDRImport] Real-time cross-case match notice: {cce}")

        return res
    except Exception as e:
        logger.exception("Failed to parse CDR file")
        raise HTTPException(status_code=400, detail=f"Failed to parse CDR file: {str(e)}")


@router.get("/cases/{case_id}/cdr/records", response_model=List[CDRRecordOut])
def get_cdr_records(
    case_id: Any,
    calling_number: Optional[str] = Query(None),
    called_number: Optional[str] = Query(None),
    cell_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves paginated and filtered telecom CDR records with file row citations."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    query = db.query(CDRRecord).filter(CDRRecord.case_id == real_case_id)
    if calling_number:
        query = query.filter(CDRRecord.calling_number.like(f"%{calling_number}%"))
    if called_number:
        query = query.filter(CDRRecord.called_number.like(f"%{called_number}%"))
    if cell_id:
        query = query.filter(CDRRecord.cell_id == cell_id)

    records = query.order_by(CDRRecord.call_datetime.asc()).offset(offset).limit(limit).all()
    return records


@router.get("/cases/{case_id}/cdr/co-locations", response_model=List[CoLocationEventOut])
def get_cdr_co_locations(
    case_id: Any,
    window_minutes: int = Query(15, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detects co-location instances where two distinct handsets hit the same sector within a time delta."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    events = analyze_co_location(real_case_id, db, window_minutes=window_minutes)
    return events


@router.get("/cases/{case_id}/cdr/common-contacts", response_model=List[CommonContactOut])
def get_cdr_common_contacts(
    case_id: Any,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Identifies common third-party contacts dialed by or calling two or more suspect handsets."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    contacts = analyze_common_contacts(real_case_id, db)
    return contacts


@router.get("/cases/{case_id}/cdr/short-lived", response_model=List[ShortLivedNumberOut])
def get_cdr_short_lived_numbers(
    case_id: Any,
    max_hours: float = Query(72.0, ge=1.0),
    max_calls: int = Query(25, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Discovers disposable / burner SIM cards active for brief periods that subsequently went silent."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    burners = analyze_short_lived_numbers(real_case_id, db, max_lifetime_hours=max_hours, max_calls=max_calls)
    return burners


@router.get("/cases/{case_id}/cdr/impossible-travel", response_model=List[ImpossibleTravelOut])
def get_cdr_impossible_travel(
    case_id: Any,
    speed_threshold: float = Query(160.0, ge=50.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Flags geographic velocity anomalies indicating SIM cloning, spoofing, or dual handsets."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    anomalies = analyze_impossible_travel(real_case_id, db, speed_threshold_kmh=speed_threshold)
    return anomalies


# ==============================================================================
# FINANCIAL & MONEY-FLOW ENDPOINTS
# ==============================================================================

@router.post("/cases/{case_id}/financial/import")
async def import_bank_statement_file(
    case_id: Any,
    file: UploadFile = File(...),
    evidence_id: Optional[int] = Form(None),
    account_number: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parses and stores bank account statements in CSV or Excel format.
    Every transaction is mapped to its exact line number and stored with counterparty extraction.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=403, detail="Permission denied to add evidence to this case.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        res = parse_and_store_bank_statement(
            file_content=content,
            file_name=file.filename or "uploaded_statement.csv",
            case_id=real_case_id,
            evidence_id=evidence_id,
            db=db,
            account_number_hint=account_number,
            bank_name_hint=bank_name
        )

        user_ident = getattr(current_user, "full_name", None) or getattr(current_user, "email", str(current_user.id))
        log_audit_event(
            db=db,
            action_type="BANK_STATEMENT_IMPORTED",
            target_type="bank_transactions",
            target_id=str(evidence_id or "batch"),
            description=f"Imported {res.get('parsed_transactions', 0)} bank transactions from '{file.filename}' by {user_ident}.",
            user_id=current_user.id,
            user_name=user_ident,
            user_role=getattr(current_user, "role", "analyst"),
            case_id=real_case_id
        )

        # Automated Live Analytics: money-flow, structuring, rapid layering, and watchlists
        try:
            live_res = run_live_cdr_and_financial_analytics(
                case_id=real_case_id,
                db=db,
                file_name=file.filename or "uploaded_statement.csv",
                user_id=current_user.id
            )
            res["live_analysis"] = live_res
        except Exception as lae:
            logger.warning(f"Automated live financial analysis notice: {lae}")

        # Real-time Cross-Case Matching across permitted cases
        try:
            from cross_case_engine import match_exhibit_cross_case_realtime
            match_exhibit_cross_case_realtime(
                evidence_id=evidence_id,
                user=current_user,
                db=db,
                case_id=real_case_id,
                file_name=file.filename
            )
        except Exception as cce:
            logger.warning(f"[BankImport] Real-time cross-case match notice: {cce}")

        return res
    except Exception as e:
        logger.exception("Failed to parse bank statement")
        raise HTTPException(status_code=400, detail=f"Failed to parse bank statement: {str(e)}")


@router.get("/cases/{case_id}/financial/transactions", response_model=List[BankTransactionOut])
def get_bank_transactions(
    case_id: Any,
    account_number: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves paginated and filtered bank statement transactions."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    query = db.query(BankTransaction).filter(BankTransaction.case_id == real_case_id)
    if account_number:
        query = query.filter(BankTransaction.account_number == account_number)
    if mode:
        query = query.filter(BankTransaction.transaction_mode == mode.upper())

    txns = query.order_by(BankTransaction.transaction_date.desc()).offset(offset).limit(limit).all()
    return txns


@router.get("/cases/{case_id}/financial/money-flow", response_model=MoneyFlowAnalysisOut)
def get_money_flow_network(
    case_id: Any,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes directed money-flow graph and suspicious financial structuring (smurfing/layering).
    Every node, edge, and alert retains exact row numbers from the statement.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    flow_data = analyze_money_flow(real_case_id, db)
    return flow_data

