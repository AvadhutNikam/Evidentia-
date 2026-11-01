"""
backend/routers/watchlists.py
=============================
Cross-Case Watchlists & Live Telecommunications/Financial Network Router.

Features:
1. Full Watchlist Target Registry (phone numbers, bank accounts, vehicle plates, persons of interest).
2. Cross-Case Detection Hook: When a target appears in ANY case the investigator can access,
   an automated alert is raised and linked directly to the file and row number.
3. Live Network Endpoint: Correlated node-link graph of calls and transfers with time, number, and amount filters.
4. On-Demand / Streaming Live Analysis Execution.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from database import get_db
from models import WatchlistEntry, Alert, Case, User, CaseMember
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from schemas import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistOut,
    LiveNetworkResponse
)
from cdr_financial_engine import (
    normalize_watchlist_token,
    check_watchlists_for_case,
    run_live_cdr_and_financial_analytics,
    get_live_correlated_network
)

router = APIRouter(tags=["Watchlists & Live Network Analytics"])
logger = logging.getLogger("evidentia.watchlists")


# ==============================================================================
# WATCHLIST CRUD ENDPOINTS
# ==============================================================================

@router.get("/watchlists", response_model=List[WatchlistOut])
def get_watchlists(
    entity_type: Optional[str] = Query(None, description="Filter by phone, account, vehicle, person"),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all watchlist targets accessible to the current investigator.
    Cross-case targets monitor phone numbers, accounts, plates, and persons across all accessible dockets.
    """
    query = db.query(WatchlistEntry)

    if entity_type:
        query = query.filter(WatchlistEntry.entity_type == entity_type.lower())
    if is_active is not None:
        query = query.filter(WatchlistEntry.is_active == is_active)

    entries = query.order_by(WatchlistEntry.created_at.desc()).all()
    return entries


@router.post("/watchlists", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
def create_watchlist_entry(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registers a new target on the investigative watchlist (phone, account, vehicle plate, person).
    Immediately scans active cases and sets up triggers for any future data arrival.
    """
    normalized_val = payload.entity_value.strip()
    if payload.entity_type.lower() == "phone":
        # Keep canonical digits
        normalized_val = payload.entity_value.strip()

    creator_name = getattr(current_user, "full_name", None) or getattr(current_user, "email", "Investigator")

    entry = WatchlistEntry(
        created_by_user_id=current_user.id,
        created_by_name=creator_name,
        case_id=payload.case_id,
        entity_type=payload.entity_type.lower(),
        entity_value=normalized_val,
        label=payload.label,
        priority=payload.priority or "critical",
        is_active=True,
        notes=payload.notes,
        match_count=0
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(f"[Watchlist] Target '{entry.entity_value}' ({entry.entity_type}) created by {creator_name}.")

    # Scan originating case immediately if provided
    if payload.case_id:
        try:
            check_watchlists_for_case(payload.case_id, db, current_user.id)
            db.refresh(entry)
        except Exception as e:
            logger.warning(f"Immediate case scan failed: {e}")

    return entry


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistOut)
def get_watchlist_entry(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves details of a specific watchlist entry."""
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")
    return entry


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist_entry(
    watchlist_id: int,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates label, priority, active status, or notes on a watchlist entry."""
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")

    if payload.label is not None:
        entry.label = payload.label
    if payload.priority is not None:
        entry.priority = payload.priority
    if payload.is_active is not None:
        entry.is_active = payload.is_active
    if payload.notes is not None:
        entry.notes = payload.notes

    entry.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_entry(
    watchlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Removes a target from the investigative watchlist."""
    entry = db.query(WatchlistEntry).filter(WatchlistEntry.id == watchlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")

    db.delete(entry)
    db.commit()
    return None


@router.get("/watchlists-matches")
def get_watchlist_matches(
    case_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all alerts raised due to watchlist hits across cases accessible to the user.
    """
    query = db.query(Alert).filter(Alert.rule_type == "watchlist_hit")
    if case_id:
        real_id = resolve_case_id(case_id, db)
        query = query.filter(Alert.case_id == real_id)

    alerts = query.order_by(Alert.created_at.desc()).limit(100).all()
    return [
        {
            "id": a.id,
            "case_id": a.case_id,
            "title": a.title,
            "message": a.message,
            "severity": a.severity,
            "status": a.status,
            "watchlist_id": a.linked_item_id,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]


# ==============================================================================
# LIVE NETWORK VIEW & AUTOMATED PIPELINE EXECUTION
# ==============================================================================

@router.get("/cases/{case_id}/telecom-financial/live-network", response_model=LiveNetworkResponse)
def get_live_network(
    case_id: str,
    time_start: Optional[str] = Query(None, description="ISO timestamp for window start"),
    time_end: Optional[str] = Query(None, description="ISO timestamp for window end"),
    search_number: Optional[str] = Query(None, description="Search phone or account number"),
    min_amount: float = Query(0.0, ge=0.0, description="Minimum transfer amount"),
    mode: str = Query("all", description="'all', 'telecom', or 'financial'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes a real-time correlated node-link network of telecom calls and financial transfers.
    Dynamically grows as new CDR and bank statements arrive.
    Supports filtering by time horizon, specific phone/account, minimum transaction amount, and mode.
    Highlights targets matching active watchlists.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    dt_start = None
    dt_end = None
    if time_start:
        try:
            dt_start = datetime.fromisoformat(time_start.replace("Z", "+00:00"))
        except Exception:
            pass
    if time_end:
        try:
            dt_end = datetime.fromisoformat(time_end.replace("Z", "+00:00"))
        except Exception:
            pass

    net_data = get_live_correlated_network(
        case_id=real_case_id,
        db=db,
        time_start=dt_start,
        time_end=dt_end,
        search_number=search_number,
        min_amount=min_amount,
        mode=mode
    )

    return net_data


@router.post("/cases/{case_id}/telecom-financial/run-live-analysis")
def trigger_live_analysis(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Forces immediate execution of automated co-location, common-contact,
    short-lived burner SIM, impossible travel, money-flow structuring, and watchlist checks.
    Raises alerts ONLY for new findings.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied to run analysis on this case.")

    res = run_live_cdr_and_financial_analytics(
        case_id=real_case_id,
        db=db,
        file_name="On-Demand / Live Trigger",
        user_id=current_user.id
    )
    return res

