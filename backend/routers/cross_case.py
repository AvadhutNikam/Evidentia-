"""
backend/routers/cross_case.py
Cross-Case Intelligence & Entity Resolution Router.

Endpoints:
- GET /cases/{case_id}/cross-case/summary: Overview of resolved links and MO similar cases.
- GET /cases/{case_id}/cross-case/entities: List detected cross-case entity links with RBAC filtering.
- POST /cases/{case_id}/cross-case/entities/resolve: Trigger real-time multi-tier entity resolution scan.
- PATCH /cases/{case_id}/cross-case/entities/{link_id}: Confirm or reject a link with reviewer notes and Merkle audit.
- GET /cases/{case_id}/cross-case/mo-similarity: Compute MO similarity against user-accessible cases with feature pills.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Case, User
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from schemas import (
    CrossCaseEntityLinkOut,
    CrossCaseLinkReviewRequest,
    CrossCaseMOSimilarCaseOut,
    CrossCaseIntelligenceSummaryOut,
    ConnectedCasesSummaryOut
)
from cross_case_engine import (
    resolve_cross_case_entities,
    get_cross_case_entity_links,
    confirm_or_reject_entity_link,
    find_mo_similar_cases,
    get_connected_cases_summary,
    match_exhibit_cross_case_realtime
)

router = APIRouter(tags=["Cross-Case Intelligence"])
logger = logging.getLogger("evidentia.cross_case")


@router.get("/cases/{case_id}/cross-case/summary", response_model=CrossCaseIntelligenceSummaryOut)
def get_case_cross_case_summary(
    case_id: Any,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns an aggregated intelligence dossier for a case:
    - Resolved cross-case entity links with status breakdowns.
    - MO-similar cases ranked by tradecraft similarity.
    Strictly isolated by case permissions.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    # 1. Fetch entity links
    links = get_cross_case_entity_links(real_case_id, current_user, db)
    pending_count = sum(1 for l in links if l.get("status") == "pending_review")
    confirmed_count = sum(1 for l in links if l.get("status") == "confirmed")
    rejected_count = sum(1 for l in links if l.get("status") == "rejected")

    # 2. Fetch MO-similar cases
    similar_cases = find_mo_similar_cases(real_case_id, current_user, db, min_similarity=0.15)

    return {
        "case_id": real_case_id,
        "total_links": len(links),
        "pending_links": pending_count,
        "confirmed_links": confirmed_count,
        "rejected_links": rejected_count,
        "links": links,
        "similar_cases": similar_cases
    }


@router.get("/cases/{case_id}/cross-case/connected-cases", response_model=ConnectedCasesSummaryOut)
def get_connected_cases_overview(
    case_id: Any,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns an aggregated overview of possibly connected and confirmed cases:
    - Grouped by connected case with detailed matching features (phone, plate, address, name).
    - Status flag indicates pending candidate review.
    - Strictly enforces case permissions: shows that a link exists ONLY to users who can open BOTH cases.
    """
    real_case_id = resolve_case_id(case_id, db)
    try:
        return get_connected_cases_summary(real_case_id, current_user, db)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.get("/cases/{case_id}/cross-case/entities", response_model=List[CrossCaseEntityLinkOut])
def get_case_cross_case_entities(
    case_id: Any,
    status: Optional[str] = Query(None, description="Filter by status: pending_review, confirmed, rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all detected cross-case entity links (phone, vehicle, person, address, digital).
    Users only see links to cases they are authorized to access.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    links = get_cross_case_entity_links(real_case_id, current_user, db, status_filter=status)
    return links


@router.post("/cases/{case_id}/cross-case/entities/resolve", response_model=List[CrossCaseEntityLinkOut])
def trigger_cross_case_resolution(
    case_id: Any,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an on-demand multi-tier entity resolution scan:
    - Tier 1: Exact identifiers (phones, vehicle plates, digital telemetry).
    - Tier 2: Exact names and locations.
    - Tier 3: Fuzzy names (>=85%) and fuzzy addresses.
    Returns all detected links.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    links = resolve_cross_case_entities(real_case_id, current_user, db)
    return links


@router.patch("/cases/{case_id}/cross-case/entities/{link_id}")
def review_cross_case_entity_link(
    case_id: Any,
    link_id: int,
    payload: CrossCaseLinkReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Investigator / Reviewer Action: Confirm or reject a detected cross-case entity link.
    Requires edit/analyze permissions or admin/lead investigator role.
    Cryptographically logs action to the Merkle Audit Chain.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    try:
        result = confirm_or_reject_entity_link(
            link_id=link_id,
            status=payload.status,
            user=current_user,
            notes=payload.notes,
            db=db
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


@router.get("/cases/{case_id}/cross-case/mo-similarity", response_model=List[CrossCaseMOSimilarCaseOut])
def get_case_mo_similar_cases(
    case_id: Any,
    min_similarity: float = Query(0.15, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reuses the 5-dimensional relevance engine (weapon, entry method, victim type,
    location type, time pattern + tradecraft narrative overlap) to discover
    analogous cases.
    Respects case permissions: strictly limits candidates to user-accessible dockets.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case.")

    similar = find_mo_similar_cases(
        case_id=real_case_id,
        user=current_user,
        db=db,
        min_similarity=min_similarity
    )
    return similar

