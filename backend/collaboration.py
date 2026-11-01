"""
backend/collaboration.py
========================
Real-time Case Collaboration Engine.
Provides:
  1. Presence: Heartbeat tracking (20-30s), active presence sweep, and location transitions.
  2. Change Awareness: Granular item-level change broadcasting (item.changed, scores.updated).
  3. Conflict Protection:
     - Optimistic Concurrency version checking (rejects stale saves with HTTP 409 Conflict).
     - Soft Edit Locks (2-min automatic expiry, typing renewal, and lead/admin override).
  4. Reconnection & Replay: Monotonic sequential event IDs and rolling event buffers.
  5. Privacy & RBAC: Role-restricted event redaction (criminal history / suspect profiles hidden from reviewers).
"""

import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import deque
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database import SessionLocal
from models import EditLock, CasePresence, CollaborationEvent, User, AuditLog
from audit_engine import log_audit_event

logger = logging.getLogger("evidentia.collaboration")

# In-memory subscriber registry and event ring buffers for instantaneous local SSE dispatch
_SUBSCRIBERS: Dict[int, Set[asyncio.Queue]] = {}
_SUBSCRIBERS_LOCK = threading.Lock()
_EVENT_RING_BUFFER: Dict[int, deque] = {}  # case_id -> deque(maxlen=200) of event dicts
_BUFFER_LOCK = threading.Lock()

PRESENCE_TIMEOUT_SECONDS = 45
DEFAULT_LOCK_TTL_SECONDS = 120


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is offset-aware UTC, even if SQLite returned offset-naive."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==============================================================================
# IN-MEMORY SUBSCRIBER MANAGEMENT FOR SSE STREAMS
# ==============================================================================

def register_case_subscriber(case_id: int) -> asyncio.Queue:
    """Registers an async queue to receive real-time collaboration events for a case."""
    queue = asyncio.Queue(maxsize=100)
    with _SUBSCRIBERS_LOCK:
        if case_id not in _SUBSCRIBERS:
            _SUBSCRIBERS[case_id] = set()
        _SUBSCRIBERS[case_id].add(queue)
    return queue


def unregister_case_subscriber(case_id: int, queue: asyncio.Queue) -> None:
    """Removes an async queue from the case subscriber registry."""
    with _SUBSCRIBERS_LOCK:
        if case_id in _SUBSCRIBERS:
            _SUBSCRIBERS[case_id].discard(queue)
            if not _SUBSCRIBERS[case_id]:
                del _SUBSCRIBERS[case_id]


def broadcast_to_local_subscribers(case_id: int, event_dict: Dict[str, Any]) -> None:
    """Delivers an event immediately to all active in-process async SSE queues for a case."""
    with _BUFFER_LOCK:
        if case_id not in _EVENT_RING_BUFFER:
            _EVENT_RING_BUFFER[case_id] = deque(maxlen=200)
        _EVENT_RING_BUFFER[case_id].append(event_dict)

    with _SUBSCRIBERS_LOCK:
        subscribers = list(_SUBSCRIBERS.get(case_id, set()))

    for q in subscribers:
        try:
            q.put_nowait(event_dict)
        except asyncio.QueueFull:
            # Drain oldest item if subscriber is lagging
            try:
                q.get_nowait()
                q.put_nowait(event_dict)
            except Exception:
                pass


# ==============================================================================
# COLLABORATION EVENT PUBLISHING & REPLAY
# ==============================================================================

def publish_collaboration_event(
    db: Session,
    case_id: int,
    event_type: str,
    item_type: Optional[str] = None,
    item_id: Optional[str] = None,
    version: Optional[int] = None,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    summary: str = "",
    payload: Optional[Dict[str, Any]] = None,
    is_restricted: bool = False,
    commit: bool = True
) -> CollaborationEvent:
    """
    Persists a collaboration event into the database with a sequential monotonic ID
    and immediately broadcasts it to all active stream listeners.
    """
    now = datetime.now(timezone.utc)
    payload_json = json.dumps(payload) if payload is not None else None

    event_row = CollaborationEvent(
        case_id=case_id,
        event_type=event_type,
        item_type=item_type,
        item_id=str(item_id) if item_id is not None else None,
        version=version,
        user_id=user_id,
        user_name=user_name or "System",
        summary=summary,
        payload=payload_json,
        is_restricted=is_restricted,
        created_at=now
    )
    db.add(event_row)
    if commit:
        db.commit()
        db.refresh(event_row)
    else:
        db.flush()

    # Construct lightweight broadcast dict
    event_dict = {
        "id": event_row.id,
        "case_id": case_id,
        "event_type": event_type,
        "item_type": item_type,
        "item_id": str(item_id) if item_id is not None else None,
        "version": version,
        "user_id": user_id,
        "user_name": user_name or "System",
        "summary": summary,
        "payload": payload or {},
        "is_restricted": is_restricted,
        "timestamp": now.isoformat()
    }

    # Broadcast to in-memory listeners
    broadcast_to_local_subscribers(case_id, event_dict)
    return event_row


def get_events_after(
    db: Session,
    case_id: int,
    after_id: int,
    user_role: str = "investigator"
) -> List[Dict[str, Any]]:
    """
    Retrieves events strictly greater than after_id for connection recovery / replay.
    Redacts or filters role-restricted events if caller is a read-only reviewer.
    """
    query = db.query(CollaborationEvent).filter(
        CollaborationEvent.case_id == case_id,
        CollaborationEvent.id > after_id
    ).order_by(CollaborationEvent.id.asc()).limit(100)

    rows = query.all()
    results = []
    for r in rows:
        # Privacy filter: Reviewer without criminal-history clearance
        if r.is_restricted and user_role == "reviewer":
            results.append({
                "id": r.id,
                "case_id": r.case_id,
                "event_type": r.event_type,
                "item_type": r.item_type,
                "item_id": r.item_id,
                "version": r.version,
                "user_id": None,
                "user_name": "Restricted",
                "summary": "Restricted case data updated.",
                "payload": {},
                "is_restricted": True,
                "timestamp": r.created_at.isoformat() if r.created_at else None
            })
        else:
            payload_data = {}
            if r.payload:
                try:
                    payload_data = json.loads(r.payload)
                except Exception:
                    pass
            results.append({
                "id": r.id,
                "case_id": r.case_id,
                "event_type": r.event_type,
                "item_type": r.item_type,
                "item_id": r.item_id,
                "version": r.version,
                "user_id": r.user_id,
                "user_name": r.user_name,
                "summary": r.summary,
                "payload": payload_data,
                "is_restricted": r.is_restricted,
                "timestamp": r.created_at.isoformat() if r.created_at else None
            })
    return results


# ==============================================================================
# PRESENCE HEARTBEAT & TRACKING
# ==============================================================================

def record_presence_heartbeat(
    db: Session,
    case_id: int,
    user_id: int,
    user_name: str,
    user_role: str,
    current_location: str = "Case Overview",
    item_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates or inserts a short-lived presence heartbeat record.
    Broadcasts presence.joined or presence.moved events as appropriate.
    Automatically renews any active edit locks held on the active item_id.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=PRESENCE_TIMEOUT_SECONDS)

    presence = db.query(CasePresence).filter(
        CasePresence.case_id == case_id,
        CasePresence.user_id == user_id
    ).first()

    is_new_join = False
    location_changed = False

    if not presence:
        presence = CasePresence(
            case_id=case_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            current_location=current_location,
            item_id=str(item_id) if item_id is not None else None,
            last_seen_at=now
        )
        db.add(presence)
        is_new_join = True
    else:
        # If user was absent for longer than threshold, treat as rejoin
        if _ensure_utc(presence.last_seen_at) < threshold:
            is_new_join = True
        elif presence.current_location != current_location or presence.item_id != (str(item_id) if item_id else None):
            location_changed = True

        presence.user_name = user_name
        presence.user_role = user_role
        presence.current_location = current_location
        presence.item_id = str(item_id) if item_id is not None else None
        presence.last_seen_at = now

    db.commit()
    db.refresh(presence)

    # Renew active soft lock on item if currently held by this user
    if item_id:
        active_lock = db.query(EditLock).filter(
            EditLock.case_id == case_id,
            EditLock.item_id == str(item_id),
            EditLock.user_id == user_id,
            EditLock.expires_at > now
        ).first()
        if active_lock:
            active_lock.expires_at = now + timedelta(seconds=DEFAULT_LOCK_TTL_SECONDS)
            db.commit()

    # Broadcast presence events
    if is_new_join:
        publish_collaboration_event(
            db=db,
            case_id=case_id,
            event_type="presence.joined",
            user_id=user_id,
            user_name=user_name,
            summary=f"{user_name} joined the case workspace.",
            payload={
                "user_id": user_id,
                "user_name": user_name,
                "user_role": user_role,
                "current_location": current_location,
                "item_id": item_id
            }
        )
    elif location_changed:
        publish_collaboration_event(
            db=db,
            case_id=case_id,
            event_type="presence.moved",
            user_id=user_id,
            user_name=user_name,
            summary=f"{user_name} navigated to {current_location}.",
            payload={
                "user_id": user_id,
                "user_name": user_name,
                "user_role": user_role,
                "current_location": current_location,
                "item_id": item_id
            }
        )

    return {
        "status": "ok",
        "user_id": user_id,
        "user_name": user_name,
        "user_role": user_role,
        "current_location": current_location,
        "item_id": item_id,
        "last_seen_at": now.isoformat()
    }


def get_active_presence(
    db: Session,
    case_id: int,
    timeout_seconds: int = PRESENCE_TIMEOUT_SECONDS
) -> List[Dict[str, Any]]:
    """Returns all users actively present in the case within the timeout threshold."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=timeout_seconds)

    records = db.query(CasePresence).filter(
        CasePresence.case_id == case_id,
        CasePresence.last_seen_at >= threshold
    ).order_by(CasePresence.last_seen_at.desc()).all()

    return [
        {
            "user_id": r.user_id,
            "user_name": r.user_name,
            "user_role": r.user_role,
            "current_location": r.current_location,
            "item_id": r.item_id,
            "last_seen_at": _ensure_utc(r.last_seen_at).isoformat() if r.last_seen_at else None
        }
        for r in records
    ]


def sweep_expired_presence(
    db: Session,
    timeout_seconds: int = PRESENCE_TIMEOUT_SECONDS
) -> int:
    """
    Cleans up expired presence records and emits presence.left events.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=timeout_seconds)

    expired = db.query(CasePresence).filter(
        CasePresence.last_seen_at < threshold
    ).all()

    departed_count = len(expired)
    for p in expired:
        publish_collaboration_event(
            db=db,
            case_id=p.case_id,
            event_type="presence.left",
            user_id=p.user_id,
            user_name=p.user_name,
            summary=f"{p.user_name} left the case workspace.",
            payload={"user_id": p.user_id, "user_name": p.user_name}
        )
        db.delete(p)

    if expired:
        db.commit()

    return departed_count


# ==============================================================================
# SOFT EDIT LOCK MANAGEMENT
# ==============================================================================

def acquire_edit_lock(
    db: Session,
    case_id: int,
    item_type: str,
    item_id: str,
    user_id: int,
    user_name: str,
    user_role: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    client_token: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Acquires or renews a soft edit lock on an item.
    Rejects read-only reviewers (HTTP 403).
    Returns (True, lock_dict) if granted/renewed, or (False, error_dict) with 423 status details.
    """
    if user_role == "reviewer":
        return False, {
            "error": "forbidden",
            "message": "Reviewer accounts have read-only permissions and cannot acquire edit locks."
        }

    now = datetime.now(timezone.utc)
    clean_item_id = str(item_id).strip()

    # Clean up any expired lock on this item
    db.query(EditLock).filter(
        EditLock.case_id == case_id,
        EditLock.item_type == item_type,
        EditLock.item_id == clean_item_id,
        EditLock.expires_at <= now
    ).delete()
    db.commit()

    # Check for active existing lock
    existing = db.query(EditLock).filter(
        EditLock.case_id == case_id,
        EditLock.item_type == item_type,
        EditLock.item_id == clean_item_id,
        EditLock.expires_at > now
    ).first()

    if existing:
        if existing.user_id == user_id:
            # Renew existing lock
            existing.expires_at = now + timedelta(seconds=ttl_seconds)
            existing.user_name = user_name
            existing.user_role = user_role
            if client_token:
                existing.client_token = client_token
            db.commit()
            db.refresh(existing)
            return True, _lock_to_dict(existing)
        else:
            # Held by another user
            remaining_seconds = max(1, int((_ensure_utc(existing.expires_at) - now).total_seconds()))
            return False, {
                "error": "locked",
                "message": f"{existing.user_name} is currently editing this {item_type}.",
                "locked_by": existing.user_name,
                "user_id": existing.user_id,
                "user_role": existing.user_role,
                "expires_at": _ensure_utc(existing.expires_at).isoformat() if existing.expires_at else None,
                "remaining_seconds": remaining_seconds
            }

    # Grant new lock
    expires_at = now + timedelta(seconds=ttl_seconds)
    lock = EditLock(
        case_id=case_id,
        item_type=item_type,
        item_id=clean_item_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        acquired_at=now,
        expires_at=expires_at,
        client_token=client_token
    )
    db.add(lock)
    db.commit()
    db.refresh(lock)

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="lock.acquired",
        item_type=item_type,
        item_id=clean_item_id,
        user_id=user_id,
        user_name=user_name,
        summary=f"{user_name} acquired edit lock on {item_type} #{clean_item_id}.",
        payload=_lock_to_dict(lock)
    )

    return True, _lock_to_dict(lock)


def release_edit_lock(
    db: Session,
    case_id: int,
    item_type: str,
    item_id: str,
    user_id: int,
    force: bool = False
) -> bool:
    """
    Releases an edit lock if held by user_id or forced by administrator.
    Broadcasts lock.released event.
    """
    now = datetime.now(timezone.utc)
    clean_item_id = str(item_id).strip()

    query = db.query(EditLock).filter(
        EditLock.case_id == case_id,
        EditLock.item_type == item_type,
        EditLock.item_id == clean_item_id
    )
    if not force:
        query = query.filter(EditLock.user_id == user_id)

    lock = query.first()
    if not lock:
        return False

    holder_name = lock.user_name
    db.delete(lock)
    db.commit()

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="lock.released",
        item_type=item_type,
        item_id=clean_item_id,
        user_id=user_id,
        user_name=holder_name,
        summary=f"Edit lock on {item_type} #{clean_item_id} released.",
        payload={"item_type": item_type, "item_id": clean_item_id}
    )

    return True


def override_edit_lock(
    db: Session,
    case_id: int,
    item_type: str,
    item_id: str,
    admin_user: User,
    reason: str = "Lead investigator administrative override"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Enables Lead Investigators or Admins to break another user's edit lock.
    Records an immutable audit entry and transfers lock.
    """
    if admin_user.role not in ["admin", "lead_investigator"]:
        return False, {
            "error": "forbidden",
            "message": "Only Case Leads and Administrators can override active edit locks."
        }

    now = datetime.now(timezone.utc)
    clean_item_id = str(item_id).strip()

    existing = db.query(EditLock).filter(
        EditLock.case_id == case_id,
        EditLock.item_type == item_type,
        EditLock.item_id == clean_item_id
    ).first()

    old_holder = existing.user_name if existing else "Nobody"

    # Transactional audit log for lock override
    log_audit_event(
        db=db,
        action_type="LOCK_OVERRIDE",
        target_type=item_type,
        target_id=clean_item_id,
        description=f"Admin/Lead {admin_user.full_name} broke edit lock on {item_type} #{clean_item_id} previously held by {old_holder}. Reason: {reason}",
        case_id=case_id,
        user_id=admin_user.id,
        user_name=admin_user.full_name,
        user_role=admin_user.role,
        before_value=f"Locked by {old_holder}",
        after_value=f"Acquired by {admin_user.full_name}",
        commit=False
    )

    if existing:
        db.delete(existing)

    new_lock = EditLock(
        case_id=case_id,
        item_type=item_type,
        item_id=clean_item_id,
        user_id=admin_user.id,
        user_name=admin_user.full_name,
        user_role=admin_user.role,
        acquired_at=now,
        expires_at=now + timedelta(seconds=DEFAULT_LOCK_TTL_SECONDS)
    )
    db.add(new_lock)
    db.commit()
    db.refresh(new_lock)

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="lock.acquired",
        item_type=item_type,
        item_id=clean_item_id,
        user_id=admin_user.id,
        user_name=admin_user.full_name,
        summary=f"{admin_user.full_name} overrode lock and acquired edit access on {item_type} #{clean_item_id}.",
        payload=_lock_to_dict(new_lock)
    )

    return True, _lock_to_dict(new_lock)


def get_case_locks(db: Session, case_id: int) -> List[Dict[str, Any]]:
    """Returns all non-expired edit locks active in a case."""
    now = datetime.now(timezone.utc)
    locks = db.query(EditLock).filter(
        EditLock.case_id == case_id,
        EditLock.expires_at > now
    ).all()
    return [_lock_to_dict(l) for l in locks]


def _lock_to_dict(lock: EditLock) -> Dict[str, Any]:
    acq = _ensure_utc(lock.acquired_at)
    exp = _ensure_utc(lock.expires_at)
    return {
        "id": lock.id,
        "case_id": lock.case_id,
        "item_type": lock.item_type,
        "item_id": lock.item_id,
        "user_id": lock.user_id,
        "user_name": lock.user_name,
        "user_role": lock.user_role,
        "acquired_at": acq.isoformat() if acq else None,
        "expires_at": exp.isoformat() if exp else None,
        "is_active": True
    }


# ==============================================================================
# OPTIMISTIC CONCURRENCY VERSION CHECKING
# ==============================================================================

def check_optimistic_concurrency(
    db: Session,
    case_id: int,
    item_type: str,
    item_id: str,
    current_version: int,
    submitted_version: Optional[int],
    current_data: Dict[str, Any],
    user_id: int,
    user_name: str
) -> None:
    """
    Enforces optimistic concurrency version safety.
    If submitted_version is supplied and does not match current_version,
    records a CONFLICT_REJECTED audit entry and raises HTTP 409 Conflict.
    """
    if submitted_version is not None and submitted_version != current_version:
        log_audit_event(
            db=db,
            action_type="CONFLICT_REJECTED",
            target_type=item_type,
            target_id=str(item_id),
            description=f"Concurrent edit conflict rejected for {item_type} #{item_id}: User {user_name} submitted v{submitted_version}, but database was already at v{current_version}.",
            case_id=case_id,
            user_id=user_id,
            user_name=user_name,
            before_value=f"v{submitted_version}",
            after_value=f"v{current_version}",
            commit=True
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict",
                "message": f"This {item_type} was modified by another investigator while you were editing.",
                "item_type": item_type,
                "item_id": str(item_id),
                "current_version": current_version,
                "submitted_version": submitted_version,
                "current_data": current_data
            }
        )
