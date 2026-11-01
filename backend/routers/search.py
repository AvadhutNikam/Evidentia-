"""
backend/routers/search.py
Router for Global Omni-Search & Command Palette.

Features:
1. Case Omni-Search: Searches across exhibits, entities, claims, quotes, suspects, tasks,
   and alerts across original text, normalized text, and judicial translations.
2. Global Cross-Case Omni-Search: Searches across all cases accessible to the authenticated user.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Case
from auth import get_current_user, check_case_access, get_user_accessible_case_ids
from routers.common import resolve_case_id
from schemas import OmniSearchResponseOut, OmniSearchResultItemOut
from omni_search_engine import search_case_omni

router = APIRouter(tags=["Command Palette & Omni-Search"])


@router.get("/cases/{case_id}/omni-search", response_model=OmniSearchResponseOut)
def omni_search_case(
    case_id: str,
    q: str = Query(..., min_length=1, description="Search term for exhibits, entities, claims, quotes, suspects, tasks, alerts"),
    category: Optional[str] = Query("all", description="Category filter: all, exhibit, entity, claim, quote, suspect, task, alert"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified omni-search for a single case:
    - Finds matches across original verbatim text, normalized text, and regional translations.
    - Searches quotes, entities, hypotheses, suspect background factors, investigation tasks, and alerts.
    - Returns match source attribution and target deep-links with highlighted text offsets.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "view_evidence"):
        raise HTTPException(
            status_code=403,
            detail=f"User role '{current_user.role}' is not authorized to search case {case_id}."
        )

    results = search_case_omni(
        db=db,
        case_id=real_case_id,
        query=q,
        category_filter=category,
        limit=limit
    )

    return {
        "query": q,
        "case_id": real_case_id,
        "total_matches": len(results),
        "matches": results
    }


@router.get("/search/omni", response_model=OmniSearchResponseOut)
def global_omni_search(
    q: str = Query(..., min_length=1, description="Global search query across all accessible cases"),
    category: Optional[str] = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Global cross-case omni-search across all cases permitted for the user.
    """
    accessible_case_ids = get_user_accessible_case_ids(current_user, db)
    if accessible_case_ids is None:
        # User is admin or has unrestricted access - query all cases
        accessible_case_ids = [c[0] for c in db.query(Case.id).all()]
    else:
        # Also include cases created by the user
        user_name = getattr(current_user, "full_name", None) or current_user.email
        created_cases = [c[0] for c in db.query(Case.id).filter(Case.created_by == user_name).all()]
        accessible_case_ids = list(set(accessible_case_ids + created_cases))

    if not accessible_case_ids:
        return {"query": q, "case_id": None, "total_matches": 0, "matches": []}

    all_matches = []
    for c_id in accessible_case_ids:
        case_results = search_case_omni(
            db=db,
            case_id=c_id,
            query=q,
            category_filter=category,
            limit=limit
        )
        all_matches.extend(case_results)

    # Sort and cap at limit
    all_matches.sort(key=lambda x: (0 if q.lower() in x["title"].lower() else 1))

    return {
        "query": q,
        "case_id": None,
        "total_matches": len(all_matches),
        "matches": all_matches[:limit]
    }
