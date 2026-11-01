"""
backend/routers/jobs.py
======================
Asynchronous Job Management & Real-Time Server-Sent Events (SSE) Router.
Provides:
  - GET /cases/{case_id}/jobs: List all processing jobs for a case docket
  - GET /jobs/{job_id}: Retrieve single job state, progress %, and checkpoints
  - POST /jobs/{job_id}/cancel: Cancel a queued or running job
  - POST /jobs/{job_id}/retry: Re-queue / resume a failed or cancelled job
  - GET /cases/{case_id}/events: Real-time Server-Sent Events stream for live UI progress
"""

import json
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import Job, Case, User, Evidence
from schemas import JobOut
from auth import get_current_user, check_case_access, decode_token
from jobs.queue import cancel_job, retry_job
from routers.common import resolve_case_id
from collaboration import (
    register_case_subscriber,
    unregister_case_subscriber,
    get_events_after
)

router = APIRouter(tags=["Background Jobs & Live Progress"])
logger = logging.getLogger("evidentia.jobs.router")
optional_bearer = HTTPBearer(auto_error=False)


def authenticate_user_for_stream(
    token: Optional[str] = None,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    db: Session = None
) -> User:
    """Authenticates user via either Authorization header or ?token= query parameter."""
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required for event stream."
        )

    payload = decode_token(raw_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    if str(user_id).isdigit():
        user = db.query(User).filter(User.id == int(user_id)).first()
    else:
        user = db.query(User).filter(User.email == str(user_id)).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive or not found.")

    return user


@router.get("/cases/{case_id}/jobs", response_model=List[JobOut])
def get_jobs_for_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all background jobs associated with a case docket."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return db.query(Job).filter(Job.case_id == real_id).order_by(Job.created_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job_by_id(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves real-time execution state and stage progress for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if not check_case_access(job.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_job_endpoint(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Requests cancellation of a queued or actively running background job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if not check_case_access(job.case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Access denied: You cannot cancel jobs for this case.")

    cancelled = cancel_job(db, job_id, user_name=current_user.full_name)
    if not cancelled:
        raise HTTPException(status_code=400, detail=f"Job #{job_id} is already in state '{job.status}'.")

    return {"success": True, "message": f"Job #{job_id} cancellation requested.", "status": "cancelling"}


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job_endpoint(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually re-queues a failed or cancelled job, resuming from the last completed stage."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if not check_case_access(job.case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Access denied: You cannot restart jobs for this case.")

    requeued = retry_job(db, job_id, user_name=current_user.full_name)
    if not requeued:
        raise HTTPException(status_code=500, detail="Failed to re-queue job.")

    return requeued


@router.get("/cases/{case_id}/stream")
@router.get("/cases/{case_id}/events/stream")
async def stream_case_job_events(
    case_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Pushes live stage progress updates (0-100%) and job status changes to the client.
    Supports token via query parameter (?token=...) or standard Bearer authorization header.
    """
    user = authenticate_user_for_stream(token=token, credentials=credentials, db=db)
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    async def event_generator():
        last_states = {}
        ping_counter = 0

        # Register in-memory queue for live collaboration events
        collab_queue = register_case_subscriber(real_id)

        # Send initial connected greeting
        init_data = json.dumps({"connected": True, "case_id": real_id, "timestamp": datetime.now(timezone.utc).isoformat()})
        yield f"event: connect\ndata: {init_data}\n\n"

        # Check for reconnection catch-up / replay via Last-Event-ID or query parameter
        last_event_header = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id")
        if last_event_header and str(last_event_header).isdigit():
            after_id = int(last_event_header)
            session = SessionLocal()
            try:
                missed = get_events_after(session, real_id, after_id=after_id, user_role=user.role)
                for ev in missed:
                    yield f"id: {ev.get('id', 0)}\nevent: {ev.get('event_type')}\ndata: {json.dumps(ev)}\n\n"
            finally:
                session.close()

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.debug(f"[SSE] Client disconnected from Case #{real_id} stream.")
                    break

                # 1. Drain instantaneous collaboration events from async queue
                while not collab_queue.empty():
                    ev = collab_queue.get_nowait()
                    if ev.get("is_restricted") and user.role == "reviewer":
                        redacted = {
                            **ev,
                            "payload": {},
                            "user_name": "Restricted",
                            "summary": "Restricted case data updated."
                        }
                        yield f"id: {ev.get('id', 0)}\nevent: {ev.get('event_type')}\ndata: {json.dumps(redacted)}\n\n"
                        yield f"id: {ev.get('id', 0)}\ndata: {json.dumps(redacted)}\n\n"
                    else:
                        yield f"id: {ev.get('id', 0)}\nevent: {ev.get('event_type')}\ndata: {json.dumps(ev)}\n\n"
                        yield f"id: {ev.get('id', 0)}\ndata: {json.dumps(ev)}\n\n"

                # 2. Query active or recently updated jobs using independent query session
                session = SessionLocal()
                try:
                    jobs = session.query(Job).filter(
                        Job.case_id == real_id
                    ).order_by(Job.id.desc()).limit(15).all()

                    for j in jobs:
                        state_key = f"{j.id}:{j.status}:{j.current_stage}:{j.progress_pct}:{j.attempt_count}"
                        if last_states.get(j.id) != state_key:
                            last_states[j.id] = state_key
                            payload = {
                                "job_id": j.id,
                                "case_id": j.case_id,
                                "exhibit_id": j.exhibit_id,
                                "job_type": j.job_type,
                                "status": j.status,
                                "stage": j.current_stage,
                                "progress": j.progress_pct,
                                "attempt_count": j.attempt_count,
                                "error_message": j.error_message,
                                "updated_at": (j.heartbeat or j.created_at).isoformat() if (j.heartbeat or j.created_at) else None
                            }
                            event_type = "job_progress"
                            if j.status == "succeeded":
                                event_type = "job_completed"
                            elif j.status == "failed":
                                event_type = "job_failed"

                            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                finally:
                    session.close()

                # Send keepalive ping comment every 15 iterations (~15s)
                ping_counter += 1
                if ping_counter >= 15:
                    yield ": ping\n\n"
                    ping_counter = 0

                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.debug(f"[SSE] Stream for Case #{real_id} cancelled.")
        finally:
            unregister_case_subscriber(real_id, collab_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==============================================================================
# STREAMING ANALYSIS PARTIAL RESULTS & "WHAT CHANGED" ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/streaming/latest")
def get_latest_streaming_analysis(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the most recent streaming analysis stage update and 'what changed' summary
    for a case. Allows client to display the what-changed strip and highlighted new items
    even across page reloads.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    from models import CollaborationEvent
    latest_event = (
        db.query(CollaborationEvent)
        .filter(
            CollaborationEvent.case_id == real_id,
            CollaborationEvent.event_type.like("stream_stage_%")
        )
        .order_by(CollaborationEvent.id.desc())
        .first()
    )

    if not latest_event:
        return {
            "has_stream": False,
            "latest_event_type": None,
            "stage": None,
            "what_changed_summary": None,
            "payload": {},
            "timestamp": None
        }

    payload = {}
    if latest_event.payload:
        try:
            payload = json.loads(latest_event.payload)
        except Exception:
            payload = {}

    return {
        "has_stream": True,
        "latest_event_type": latest_event.event_type,
        "stage": payload.get("stage", "completed"),
        "what_changed_summary": payload.get("what_changed_summary") or latest_event.summary,
        "payload": payload,
        "timestamp": latest_event.created_at.isoformat() if latest_event.created_at else None
    }


@router.post("/cases/{case_id}/streaming/simulate")
def simulate_streaming_analysis(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Demonstration and test endpoint:
    Pushes progressive analysis facts through the live SSE stream stage-by-stage:
      1. stream_stage_text: Text extracted snippet appears
      2. stream_stage_entities: 3 new entities & 2 claims appear
      3. stream_stage_citations: Fact citations verified
      4. stream_stage_contradictions: 1 new contradiction detected
      5. stream_stage_scores: H2 moved from 41% to 47%
      6. stream_stage_completed: 'What Changed' strip emitted
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Access denied.")

    from collaboration import publish_collaboration_event

    # Stage 1: Text
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_text",
        summary="Forensic exhibit text extracted (4,820 characters).",
        payload={
            "job_id": 9999,
            "stage": "extract_text",
            "stage_label": "Text Extraction",
            "progress_pct": 25.0,
            "evidence_file_name": "lab_forensic_swab_analysis.pdf",
            "text_preview": "CENTRAL FORENSIC SCIENCE LABORATORY\nExhibit examined: Cotton swab containing brown staining.\nChemical test indicates presence of human blood.\nDNA STR profile matches reference sample of Suspect #2.",
            "text_length": 4820,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Stage 2: Entities & Claims
    entities_sample = [
        {"id": 901, "name": "Yogesh Raut", "type": "Person", "confidence": 0.98},
        {"id": 902, "name": "Katraj Toll Plaza", "type": "Location", "confidence": 0.94},
        {"id": 903, "name": "MH-12-DE-4491", "type": "Vehicle", "confidence": 0.96}
    ]
    events_sample = [
        {"id": 801, "title": "Vehicle passed Katraj toll plaza at 22:15", "timestamp": "2026-10-30T22:15:00Z"},
        {"id": 802, "title": "ATM card transaction recorded at Kothrud", "timestamp": "2026-10-30T22:42:00Z"}
    ]
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_entities",
        summary="3 new entities and 2 timeline events discovered.",
        payload={
            "job_id": 9999,
            "stage": "extract_entities_claims",
            "stage_label": "Entities & Timeline Claims",
            "progress_pct": 65.0,
            "evidence_file_name": "lab_forensic_swab_analysis.pdf",
            "new_entities": entities_sample,
            "new_events": events_sample,
            "new_entities_count": 3,
            "new_events_count": 2,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Stage 3: Citations
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_citations",
        summary="Verified 3 fact claims against raw evidence bytes.",
        payload={
            "job_id": 9999,
            "stage": "verify_citations",
            "stage_label": "Citations Verified",
            "progress_pct": 78.0,
            "anchored_count": 3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Stage 4: Contradictions
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_contradictions",
        summary="1 new contradiction detected with suspect alibi.",
        payload={
            "job_id": 9999,
            "stage": "detect_contradictions",
            "stage_label": "Contradiction Matrix",
            "progress_pct": 85.0,
            "contradictions_found": 1,
            "new_contradictions_count": 1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Stage 5: Scores
    scores_sample = [
        {"hypothesis_id": 1, "code": "H1", "title": "H1: Solo perpetrator", "prev_pct": 28, "new_pct": 21, "delta_pct": -7},
        {"hypothesis_id": 2, "code": "H2", "title": "H2: Multi-suspect abduction (Yogesh Raut)", "prev_pct": 41, "new_pct": 47, "delta_pct": 6},
        {"hypothesis_id": 3, "code": "H3", "title": "H3: Approver Rajesh Chaudhari", "prev_pct": 14, "new_pct": 15, "delta_pct": 1}
    ]
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_scores",
        summary="ACH scores updated: H2 moved from 41% to 47%",
        payload={
            "job_id": 9999,
            "stage": "recalculate_scores",
            "stage_label": "ACH Recalculated",
            "progress_pct": 99.0,
            "score_deltas": scores_sample,
            "score_movement_summary": "H2 moved from 41% to 47%",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    # Final "What Changed" summary strip
    what_changed = "3 new entities, 1 new contradiction, H2 moved from 41% to 47%."
    completed_event = publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="stream_stage_completed",
        summary=what_changed,
        payload={
            "job_id": 9999,
            "stage": "completed",
            "stage_label": "Analysis Complete",
            "progress_pct": 100.0,
            "what_changed_summary": what_changed,
            "new_entities": entities_sample,
            "new_events": events_sample,
            "new_entities_count": 3,
            "new_events_count": 2,
            "new_contradictions_count": 1,
            "score_deltas": scores_sample,
            "score_movement_summary": "H2 moved from 41% to 47%",
            "highlight_duration_minutes": 5,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    )

    return {
        "status": "success",
        "message": "Streamed progressive analysis stages and pushed 'what changed' strip.",
        "what_changed_summary": what_changed,
        "event_id": completed_event.id
    }


