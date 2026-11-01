"""
backend/routers/collaboration.py
================================
Real-Time Case Collaboration & Presence Router.
Provides:
  - POST /cases/{case_id}/presence/heartbeat: Heartbeat & current view location
  - GET  /cases/{case_id}/presence: Active users viewing this case
  - POST /cases/{case_id}/locks/acquire: Soft edit lock acquisition & renewal
  - POST /cases/{case_id}/locks/release: Explicit lock release
  - POST /cases/{case_id}/locks/override: Administrative lock override (Lead/Admin)
  - GET  /cases/{case_id}/locks: Active edit locks in this case
  - GET  /cases/{case_id}/collaboration/history: Replay buffer of collaboration events
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import (
    PresenceHeartbeatRequest, PresenceUserOut,
    EditLockRequest, EditLockOut
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from collaboration import (
    record_presence_heartbeat, get_active_presence,
    acquire_edit_lock, release_edit_lock, override_edit_lock,
    get_case_locks, get_events_after
)

router = APIRouter(tags=["Live Collaboration & Presence"])


# ==============================================================================
# PRESENCE ENDPOINTS
# ==============================================================================

@router.post("/cases/{case_id}/presence/heartbeat")
def heartbeat_endpoint(
    case_id: str,
    data: PresenceHeartbeatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records a periodic (20-30s) user presence heartbeat.
    Transmits user location inside the app and renews any held locks.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return record_presence_heartbeat(
        db=db,
        case_id=real_case_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        current_location=data.current_location,
        item_id=data.item_id
    )


@router.get("/cases/{case_id}/presence", response_model=List[PresenceUserOut])
def get_case_presence_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the list of active team members currently viewing this case."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return get_active_presence(db, real_case_id)


# ==============================================================================
# SOFT EDIT LOCK ENDPOINTS
# ==============================================================================

@router.post("/cases/{case_id}/locks/acquire")
def acquire_lock_endpoint(
    case_id: str,
    data: EditLockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acquires or renews a soft edit lock on an item.
    Returns HTTP 423 Locked if currently held by another user.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied: Reviewers and unauthorized users cannot edit.")

    success, res = acquire_edit_lock(
        db=db,
        case_id=real_case_id,
        item_type=data.item_type,
        item_id=data.item_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        ttl_seconds=data.ttl_seconds or 120
    )

    if not success:
        if res.get("error") == "locked":
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=res
            )
        elif res.get("error") == "forbidden":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=res)
        raise HTTPException(status_code=400, detail=res)

    return res


@router.post("/cases/{case_id}/locks/release")
def release_lock_endpoint(
    case_id: str,
    data: EditLockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Releases a soft edit lock when the user saves, cancels, or navigates away."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    released = release_edit_lock(
        db=db,
        case_id=real_case_id,
        item_type=data.item_type,
        item_id=data.item_id,
        user_id=current_user.id
    )
    return {
        "status": "released" if released else "not_found",
        "success": released,
        "item_type": data.item_type,
        "item_id": data.item_id
    }


@router.post("/cases/{case_id}/locks/override")
def override_lock_endpoint(
    case_id: str,
    data: EditLockRequest,
    reason: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Forces transfer of an edit lock to an administrator or lead investigator."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    effective_reason = data.reason or reason or "Lead investigator administrative lock override"
    success, res = override_edit_lock(
        db=db,
        case_id=real_case_id,
        item_type=data.item_type,
        item_id=data.item_id,
        admin_user=current_user,
        reason=effective_reason
    )
    if not success:
        raise HTTPException(status_code=403, detail=res)

    return res


@router.get("/cases/{case_id}/locks", response_model=List[EditLockOut])
def get_case_locks_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all currently active edit locks in the case."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return get_case_locks(db, real_case_id)


# ==============================================================================
# EVENT REPLAY & HISTORY
# ==============================================================================

@router.get("/cases/{case_id}/collaboration/history")
def get_collaboration_history(
    case_id: str,
    after_id: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns collaboration events created after after_id for reconnection catch-up."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return get_events_after(db, real_case_id, after_id=after_id, user_role=current_user.role)
