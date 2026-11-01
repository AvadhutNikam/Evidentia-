"""
backend/jobs/queue.py
====================
Database-backed queue management for asynchronous background forensic processing.
Supports atomic job claiming, stage checkpointing, heartbeats, stuck-job recovery,
and exponential backoff with jitter for transient failures.
Works seamlessly on SQLite and PostgreSQL.
"""

import json
import logging
import random
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, update

from models import Job, Case, Evidence, EvidenceStatus, User
from audit_engine import log_audit_event

logger = logging.getLogger("evidentia.jobs")


# ==============================================================================
# ERROR CLASSIFICATION & BACKOFF CALCULATION
# ==============================================================================

RETRYABLE_ERROR_SUBSTRINGS = [
    "429", "rate limit", "resource exhausted", "quota",
    "timeout", "timed out", "connection reset", "502", "503", "504",
    "temporarily unavailable", "try again later", "deadline exceeded"
]

NON_RETRYABLE_SUBSTRINGS = [
    "400", "invalid argument", "corrupted", "not found", "unsupported format",
    "bad signature", "permission denied", "invalid api key", "unauthorized"
]


def classify_error(err: Exception) -> Tuple[bool, str, str]:
    """
    Classifies an exception into retryable vs permanent.
    Returns (is_retryable, user_safe_message, error_detail).
    """
    msg = str(err).lower()
    detail = traceback.format_exc()

    # Explicit check for known retryable patterns
    is_retryable = False
    for sub in RETRYABLE_ERROR_SUBSTRINGS:
        if sub in msg:
            is_retryable = True
            break

    # Non-retryable takes precedence if explicit
    for non_sub in NON_RETRYABLE_SUBSTRINGS:
        if non_sub in msg and not any(r in msg for r in ["429", "rate limit"]):
            is_retryable = False
            break

    # Provide concise, user-safe error summary
    if "429" in msg or "rate limit" in msg:
        user_safe = "AI engine rate limit encountered. Job queued for automatic retry."
    elif "timeout" in msg or "timed out" in msg:
        user_safe = "Processing timed out. Queued for automatic retry."
    elif "api key" in msg:
        user_safe = "AI service authentication error. Check GEMINI_API_KEY."
    elif "not found" in msg:
        user_safe = "Referenced file or exhibit record was not found."
    else:
        user_safe = f"Processing error: {str(err)[:120]}"

    return is_retryable, user_safe, detail


def calculate_backoff(attempt_count: int, base: float = 5.0, factor: float = 2.0, max_backoff: float = 120.0) -> float:
    """
    Calculates exponential backoff delay with random jitter in seconds:
      delay = min(max_backoff, base * (factor ^ (attempt - 1))) + jitter
    """
    exp_delay = base * (factor ** max(0, attempt_count - 1))
    jitter = random.uniform(0.5, 3.0)
    return min(max_backoff, exp_delay) + jitter


# ==============================================================================
# JOB CREATION & ATOMIC CLAIMING
# ==============================================================================

def create_job(
    db: Session,
    case_id: int,
    exhibit_id: Optional[int] = None,
    job_type: str = "process_evidence",
    user_id: Optional[int] = None,
    created_by: Optional[str] = None,
    priority: int = 0,
    max_attempts: int = 3
) -> Job:
    """
    Registers a new background job in the database with status 'queued'.
    Returns immediately in under a few milliseconds.
    """
    now = datetime.now(timezone.utc)
    job = Job(
        case_id=case_id,
        exhibit_id=exhibit_id,
        user_id=user_id,
        created_by=created_by or "System",
        job_type=job_type,
        status="queued",
        current_stage="queued",
        progress_pct=0.0,
        attempt_count=0,
        max_attempts=max_attempts,
        stage_results=json.dumps({}),
        heartbeat=now,
        next_run_at=now,
        priority=priority,
        cancel_requested=False,
        created_at=now
    )
    db.add(job)

    # If associated with an exhibit, update evidence processing status to Queued
    if exhibit_id:
        ev = db.query(Evidence).filter(Evidence.id == exhibit_id).first()
        if ev:
            ev.processing_status = EvidenceStatus.QUEUED

    db.commit()
    db.refresh(job)

    logger.info(f"[Jobs] Created job #{job.id} ({job_type}) for Case #{case_id}, Exhibit #{exhibit_id}")
    return job


def claim_next_job(db: Session, worker_id: Optional[str] = None) -> Optional[Job]:
    """
    Atomically claims the highest priority, oldest queued job whose next_run_at <= now.
    Prevents race conditions between concurrent worker threads or processes.
    Uses database row update verification (works across SQLite and PostgreSQL).
    """
    now = datetime.now(timezone.utc)

    # Find candidates
    query = db.query(Job).filter(
        Job.status == "queued",
        Job.cancel_requested == False,
        or_(Job.next_run_at == None, Job.next_run_at <= now)
    ).order_by(
        Job.priority.desc(),
        Job.created_at.asc()
    )

    candidate = query.first()
    if not candidate:
        return None

    # Atomic CAS (Compare-And-Swap) claim
    result = db.query(Job).filter(
        Job.id == candidate.id,
        Job.status == "queued"
    ).update({
        "status": "running",
        "started_at": now,
        "heartbeat": now,
        "attempt_count": candidate.attempt_count + 1
    }, synchronize_session=False)

    db.commit()

    if result == 1:
        # Successfully claimed
        claimed_job = db.query(Job).filter(Job.id == candidate.id).first()
        logger.info(f"[Jobs] Worker claimed job #{claimed_job.id} (Attempt {claimed_job.attempt_count}/{claimed_job.max_attempts})")
        return claimed_job

    # Another worker claimed it first
    return None


# ==============================================================================
# PROGRESS & STAGE CHECKPOINTING
# ==============================================================================

def update_job_stage(
    db: Session,
    job_id: int,
    stage: str,
    progress_pct: float,
    stage_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Updates the active job stage, progress percentage, heartbeat timestamp,
    and stores serialized stage results for resume capability.
    """
    now = datetime.now(timezone.utc)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return

    job.current_stage = stage
    job.progress_pct = round(max(0.0, min(100.0, progress_pct)), 1)
    job.heartbeat = now

    # Merge stage results into checkpoint
    current_results = {}
    if job.stage_results:
        try:
            current_results = json.loads(job.stage_results)
        except Exception:
            current_results = {}

    if stage_data:
        current_results[stage] = {
            "completed_at": now.isoformat(),
            "data": stage_data
        }
        job.stage_results = json.dumps(current_results)

    db.commit()
    logger.debug(f"[Jobs] Job #{job_id} stage -> {stage} ({job.progress_pct}%)")


def update_job_heartbeat(db: Session, job_id: int) -> None:
    """Updates the heartbeat timestamp of a running job."""
    now = datetime.now(timezone.utc)
    db.query(Job).filter(Job.id == job_id).update({"heartbeat": now}, synchronize_session=False)
    db.commit()


def complete_job(db: Session, job_id: int, summary: Optional[str] = None) -> None:
    """Marks a job as succeeded and records an audit log entry."""
    now = datetime.now(timezone.utc)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return

    job.status = "succeeded"
    job.current_stage = "completed"
    job.progress_pct = 100.0
    job.finished_at = now
    job.error_message = None

    if job.exhibit_id:
        ev = db.query(Evidence).filter(Evidence.id == job.exhibit_id).first()
        if ev:
            ev.processing_status = EvidenceStatus.ANALYZED

    db.commit()

    log_audit_event(
        db=db,
        action_type="JOB_COMPLETED",
        target_type="job",
        target_id=str(job_id),
        description=f"Background job #{job_id} ({job.job_type}) completed successfully. {summary or ''}".strip(),
        case_id=job.case_id,
        user_name=job.created_by
    )

    logger.info(f"[Jobs] Job #{job_id} succeeded.")


def fail_job(
    db: Session,
    job_id: int,
    error: Exception,
    allow_retry: bool = True
) -> None:
    """
    Handles job failure. If error is transient and attempts remain,
    calculates backoff and re-queues. Otherwise, marks as permanently failed.
    """
    now = datetime.now(timezone.utc)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return

    is_retryable, user_msg, detail = classify_error(error)

    if allow_retry and is_retryable and job.attempt_count < job.max_attempts:
        backoff_sec = calculate_backoff(job.attempt_count)
        next_run = now + timedelta(seconds=backoff_sec)

        job.status = "queued"
        job.next_run_at = next_run
        job.error_message = f"Temporary failure: {user_msg} (Retry in {int(backoff_sec)}s)"
        job.error_detail = detail
        db.commit()

        logger.warning(
            f"[Jobs] Job #{job_id} failed transiently (attempt {job.attempt_count}/{job.max_attempts}). "
            f"Retrying in {backoff_sec:.1f}s at {next_run.isoformat()}."
        )
    else:
        # Permanent failure
        job.status = "failed"
        job.finished_at = now
        job.error_message = user_msg
        job.error_detail = detail

        if job.exhibit_id:
            ev = db.query(Evidence).filter(Evidence.id == job.exhibit_id).first()
            if ev:
                ev.processing_status = EvidenceStatus.FAILED

        db.commit()

        log_audit_event(
            db=db,
            action_type="JOB_FAILED",
            target_type="job",
            target_id=str(job_id),
            description=f"Background job #{job_id} ({job.job_type}) failed permanently: {user_msg}",
            case_id=job.case_id,
            user_name=job.created_by,
            after_value=user_msg
        )

        logger.error(f"[Jobs] Job #{job_id} failed permanently: {user_msg}")


def cancel_job(db: Session, job_id: int, user_name: Optional[str] = None) -> bool:
    """Cancels a queued or running job."""
    now = datetime.now(timezone.utc)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.status in ["succeeded", "failed", "cancelled"]:
        return False

    if job.status == "queued":
        job.status = "cancelled"
        job.finished_at = now
        job.error_message = "Cancelled by user before execution."
    else:
        # Running: set cancellation flag for worker to abort between stages
        job.cancel_requested = True

    db.commit()

    log_audit_event(
        db=db,
        action_type="JOB_CANCELLED",
        target_type="job",
        target_id=str(job_id),
        description=f"Job #{job_id} cancelled by {user_name or 'user'}.",
        case_id=job.case_id,
        user_name=user_name
    )

    logger.info(f"[Jobs] Job #{job_id} cancellation requested.")
    return True


def retry_job(db: Session, job_id: int, user_name: Optional[str] = None) -> Optional[Job]:
    """Manually re-queues a failed or cancelled job."""
    now = datetime.now(timezone.utc)
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None

    job.status = "queued"
    job.cancel_requested = False
    job.error_message = None
    job.error_detail = None
    job.next_run_at = now
    job.finished_at = None
    # Reset attempt count to allow full retry attempts from human trigger
    job.attempt_count = 0

    if job.exhibit_id:
        ev = db.query(Evidence).filter(Evidence.id == job.exhibit_id).first()
        if ev:
            ev.processing_status = EvidenceStatus.QUEUED

    db.commit()
    db.refresh(job)

    log_audit_event(
        db=db,
        action_type="JOB_RETRIED",
        target_type="job",
        target_id=str(job_id),
        description=f"Job #{job_id} manually restarted by {user_name or 'analyst'}.",
        case_id=job.case_id,
        user_name=user_name
    )

    logger.info(f"[Jobs] Job #{job_id} manually re-queued.")
    return job


# ==============================================================================
# STUCK JOB RECOVERY (WORKER CRASH RECOVERY)
# ==============================================================================

def recover_stuck_jobs(db: Session, timeout_seconds: int = 120) -> int:
    """
    Finds jobs marked 'running' whose heartbeat has not been updated in timeout_seconds.
    If attempts remain, returns them to 'queued' for retry.
    Otherwise, marks them as 'failed'.
    Returns count of recovered jobs.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=timeout_seconds)

    stuck_jobs = db.query(Job).filter(
        Job.status == "running",
        or_(Job.heartbeat == None, Job.heartbeat < cutoff)
    ).all()

    recovered = 0
    for job in stuck_jobs:
        if job.attempt_count < job.max_attempts:
            job.status = "queued"
            job.error_message = "Worker heartbeat timeout. Automatically re-queued."
            job.next_run_at = now
            recovered += 1
            logger.warning(f"[Jobs] Recovered abandoned job #{job.id} -> re-queued.")
        else:
            job.status = "failed"
            job.finished_at = now
            job.error_message = "Worker process terminated unexpectedly (heartbeat timeout)."
            logger.error(f"[Jobs] Abandoned job #{job.id} exceeded attempts -> failed.")
            recovered += 1

    if stuck_jobs:
        db.commit()

    return recovered

