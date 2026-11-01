"""
backend/tests/test_jobs.py
=========================
Comprehensive Test Suite for Asynchronous Job Queue, Worker Pipeline,
Atomic Claiming, Checkpointing, Stuck Job Recovery, and SSE/Polling Endpoints.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from io import BytesIO
from fastapi import UploadFile

from models import Case, Evidence, EvidenceStatus, Job, User
from jobs.queue import (
    create_job, claim_next_job, update_job_stage, update_job_heartbeat,
    complete_job, fail_job, cancel_job, retry_job, recover_stuck_jobs,
    classify_error, calculate_backoff
)
from jobs.pipeline import execute_evidence_pipeline


@pytest.fixture
def case_and_evidence(db):
    """Sets up a test case docket and forensic exhibit."""
    case = Case(
        title="Operation Nightshade",
        description="Armed burglary and evidence tampering investigation"
    )
    db.add(case)
    db.commit()

    sample_report = (
        "OFFICIAL FORENSIC LABORATORY EXAMINATION REPORT\n"
        "Exhibit A: Partial blood smear collected from railing.\n"
        "DNA profiling matches suspect Marcus Vance with random match probability < 1 in 10 billion.\n"
        "Julian Hayes is definitively excluded as a contributor.\n"
    )

    evidence = Evidence(
        case_id=case.id,
        file_name="forensic_report.txt",
        file_type="text",
        file_size=len(sample_report),
        storage_path=None,
        extracted_text=sample_report,
        processing_status=EvidenceStatus.UPLOADED,
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        hash_verified=True
    )
    db.add(evidence)
    db.commit()

    return case, evidence


def test_job_creation_and_atomic_priority_claim(db, case_and_evidence):
    """Verifies that jobs are claimed atomically according to priority and creation order."""
    case, evidence = case_and_evidence

    # Create 3 jobs: low, normal, and high priority
    job_low = create_job(db, case_id=case.id, exhibit_id=evidence.id, job_type="process_evidence", priority=0)
    job_high = create_job(db, case_id=case.id, exhibit_id=evidence.id, job_type="process_evidence", priority=10)
    job_normal = create_job(db, case_id=case.id, exhibit_id=evidence.id, job_type="process_evidence", priority=5)

    # First claim should atomically grab the HIGH priority job
    claimed_1 = claim_next_job(db, worker_id="worker-A")
    assert claimed_1 is not None
    assert claimed_1.id == job_high.id
    assert claimed_1.status == "running"
    assert claimed_1.attempt_count == 1
    assert claimed_1.heartbeat is not None

    # Second claim should grab NORMAL priority job
    claimed_2 = claim_next_job(db, worker_id="worker-B")
    assert claimed_2 is not None
    assert claimed_2.id == job_normal.id
    assert claimed_2.status == "running"

    # Third claim should grab LOW priority job
    claimed_3 = claim_next_job(db, worker_id="worker-A")
    assert claimed_3 is not None
    assert claimed_3.id == job_low.id

    # Queue is now empty: next claim should return None
    assert claim_next_job(db) is None


def test_upload_returns_immediately_with_queued_job(client, admin_headers, db, case_and_evidence):
    """
    Validates that the upload endpoint returns immediately (< 1 second)
    with status 200, db_evidence, and a queued job_id in headers and payload.
    """
    case, _ = case_and_evidence

    sample_content = b"CCTV Forensic Log: Suspect observed entering front entrance at 22:15."
    files = {"file": ("cctv_log.txt", sample_content, "text/plain")}
    data = {
        "source": "Security Terminal 1",
        "collected_by": "Detective Clark",
        "evidence_type": "document"
    }

    start_time = datetime.now()
    resp = client.post(f"/cases/{case.id}/evidence", files=files, data=data, headers=admin_headers)
    elapsed = (datetime.now() - start_time).total_seconds()

    # Upload must return in well under a second
    assert elapsed < 1.5
    assert resp.status_code == 200

    resp_data = resp.json()
    assert resp_data["id"] is not None
    assert resp_data["job_id"] is not None
    assert resp_data["processing_status"] in ["Queued", "Uploaded"]
    assert "X-Job-Id" in resp.headers

    # Verify job exists in DB with queued status
    job_in_db = db.query(Job).filter(Job.id == resp_data["job_id"]).first()
    assert job_in_db is not None
    assert job_in_db.status == "queued"
    assert job_in_db.case_id == case.id
    assert job_in_db.exhibit_id == resp_data["id"]


def test_multi_stage_pipeline_execution_and_checkpointing(db, case_and_evidence):
    """
    Executes the 7-stage evidence pipeline and verifies that all stages
    complete, progress reaches 100%, and intermediate stage results are checkpointed.
    """
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id)
    claimed = claim_next_job(db)
    assert claimed is not None

    success = execute_evidence_pipeline(job.id, db)
    assert success is True

    # Refresh records
    db.refresh(job)
    db.refresh(evidence)

    assert job.status == "succeeded"
    assert job.current_stage == "completed"
    assert job.progress_pct == 100.0
    assert evidence.processing_status == EvidenceStatus.ANALYZED

    # Checkpoint results must be saved for completed stages
    checkpoints = json.loads(job.stage_results or "{}")
    assert "extract_text" in checkpoints
    assert "chunk_text" in checkpoints
    assert "extract_entities_claims" in checkpoints
    assert "verify_citations" in checkpoints
    assert "classify_hypotheses" in checkpoints
    assert "recalculate_scores" in checkpoints


def test_job_resumes_from_last_checkpoint_on_retry(db, case_and_evidence):
    """
    Validates that a retried job resumes from its last completed stage
    instead of restarting completed stages.
    """
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id)

    # Pre-populate Stage 1 and Stage 2 as completed
    initial_checkpoints = {
        "extract_text": {"completed_at": datetime.now(timezone.utc).isoformat(), "data": {"text_length": 150}},
        "chunk_text": {"completed_at": datetime.now(timezone.utc).isoformat(), "data": {"chunk_count": 2}}
    }
    job.stage_results = json.dumps(initial_checkpoints)
    job.current_stage = "chunk_text"
    job.progress_pct = 40.0
    db.commit()

    # Claim and execute
    claimed = claim_next_job(db)
    assert claimed is not None

    success = execute_evidence_pipeline(job.id, db)
    assert success is True

    db.refresh(job)
    assert job.status == "succeeded"
    final_checkpoints = json.loads(job.stage_results)

    # Stages 1 and 2 timestamps are preserved (not re-executed)
    assert final_checkpoints["extract_text"]["data"]["text_length"] == 150
    assert final_checkpoints["chunk_text"]["data"]["chunk_count"] == 2
    # Later stages are also completed
    assert "classify_hypotheses" in final_checkpoints
    assert "recalculate_scores" in final_checkpoints


def test_heartbeat_timeout_recovers_stuck_job(db, case_and_evidence):
    """
    Validates that worker crash or abandoned jobs (expired heartbeat)
    are detected and automatically re-queued.
    """
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id, max_attempts=3)
    claimed = claim_next_job(db)

    # Simulate worker crash: set heartbeat to 10 minutes ago
    ten_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    job.heartbeat = ten_mins_ago
    db.commit()

    # Recover stuck jobs with 60s timeout
    recovered_count = recover_stuck_jobs(db, timeout_seconds=60)
    assert recovered_count == 1

    db.refresh(job)
    assert job.status == "queued"
    assert "heartbeat timeout" in job.error_message.lower()

    # If job has reached max_attempts, recovery should permanently fail it
    job.attempt_count = 3
    job.status = "running"
    job.heartbeat = ten_mins_ago
    db.commit()

    recover_stuck_jobs(db, timeout_seconds=60)
    db.refresh(job)
    assert job.status == "failed"
    assert "exceeded attempts" in job.error_message.lower() or "terminated unexpectedly" in job.error_message.lower()


def test_retryable_error_applies_backoff(db, case_and_evidence):
    """Transient rate-limit (429) errors apply exponential backoff and remain queued."""
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id, max_attempts=3)
    claim_next_job(db)

    # Simulate 429 ResourceExhausted exception
    rate_limit_err = RuntimeError("429 ResourceExhausted: rate limit exceeded for model")
    is_retryable, user_msg, _ = classify_error(rate_limit_err)
    assert is_retryable is True

    fail_job(db, job.id, rate_limit_err, allow_retry=True)

    db.refresh(job)
    assert job.status == "queued"
    assert job.next_run_at is not None
    next_run = job.next_run_at.replace(tzinfo=timezone.utc) if job.next_run_at.tzinfo is None else job.next_run_at
    assert next_run > datetime.now(timezone.utc)
    assert "rate limit" in job.error_message.lower()


def test_non_retryable_error_fails_immediately(db, case_and_evidence):
    """Corrupted files or permanent 400 Bad Request errors fail immediately without retry."""
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id, max_attempts=3)
    claim_next_job(db)

    perm_err = ValueError("Corrupted file payload: unsupported format header")
    is_retryable, user_msg, _ = classify_error(perm_err)
    assert is_retryable is False

    fail_job(db, job.id, perm_err, allow_retry=True)

    db.refresh(job)
    assert job.status == "failed"
    assert job.finished_at is not None


def test_job_cancellation(db, case_and_evidence):
    """Validates cancelling queued jobs and requesting cancellation for running jobs."""
    case, evidence = case_and_evidence

    # Queued job cancellation
    queued_job = create_job(db, case_id=case.id, exhibit_id=evidence.id)
    cancelled = cancel_job(db, queued_job.id, user_name="Investigator")
    assert cancelled is True
    db.refresh(queued_job)
    assert queued_job.status == "cancelled"

    # Running job cancellation
    running_job = create_job(db, case_id=case.id, exhibit_id=evidence.id)
    claim_next_job(db)
    cancel_job(db, running_job.id, user_name="Investigator")
    db.refresh(running_job)
    assert running_job.cancel_requested is True


def test_job_router_endpoints_and_case_isolation(client, admin_headers, analyst_headers, db, case_and_evidence):
    """Verifies GET /cases/{id}/jobs, GET /jobs/{id}, POST /jobs/{id}/retry and RBAC isolation."""
    case, evidence = case_and_evidence

    job = create_job(db, case_id=case.id, exhibit_id=evidence.id)

    # Admin access
    resp = client.get(f"/cases/{case.id}/jobs", headers=admin_headers)
    assert resp.status_code == 200
    jobs_list = resp.json()
    assert len(jobs_list) >= 1
    assert jobs_list[0]["id"] == job.id

    # Single job details
    resp_single = client.get(f"/jobs/{job.id}", headers=admin_headers)
    assert resp_single.status_code == 200
    assert resp_single.json()["status"] == "queued"

    # Cancel via API
    resp_cancel = client.post(f"/jobs/{job.id}/cancel", headers=admin_headers)
    assert resp_cancel.status_code == 200

    # Retry via API
    resp_retry = client.post(f"/jobs/{job.id}/retry", headers=admin_headers)
    assert resp_retry.status_code == 200
    assert resp_retry.json()["status"] == "queued"

    # Unauthenticated request rejected
    resp_unauth = client.get(f"/cases/{case.id}/jobs")
    assert resp_unauth.status_code == 401


def test_sse_stream_endpoint_unshadowed_and_distinct_from_timeline_events(client, admin_headers, db, case_and_evidence):
    """
    Verifies that:
    1. GET /cases/{id}/events returns timeline events (JSON List[EventOut]) from cases_router.
    2. GET /cases/{id}/stream provides dedicated SSE streaming from jobs_router without route shadowing.
    3. Unauthenticated stream request is rejected with 401.
    """
    case, _ = case_and_evidence

    # 1. Timeline events endpoint returns JSON array
    resp_events = client.get(f"/cases/{case.id}/events", headers=admin_headers)
    assert resp_events.status_code == 200
    assert isinstance(resp_events.json(), list)
    assert "application/json" in resp_events.headers.get("content-type", "")

    # 2. SSE streaming endpoint returns text/event-stream with initial connect frame
    with client.stream("GET", f"/cases/{case.id}/stream", headers=admin_headers) as stream_resp:
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")
        # Read the initial connect event
        first_chunk = next(stream_resp.iter_lines())
        assert "event: connect" in first_chunk or "data:" in first_chunk

    # 3. Stream alias (/cases/{id}/events/stream) also functions identically
    with client.stream("GET", f"/cases/{case.id}/events/stream", headers=admin_headers) as stream_resp:
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")

    # 4. Unauthenticated stream request is rejected
    resp_unauth = client.get(f"/cases/{case.id}/stream")
    assert resp_unauth.status_code == 401


def test_analyze_evidence_endpoint_defaults_to_sync_and_tracks_user(client, admin_headers, analyst_headers, seed_users, db, case_and_evidence):
    """
    Verifies that:
    1. POST /evidence/{id}/analyze defaults to sync=True, executing immediately and returning status: success.
    2. POST /evidence/{id}/analyze?sync=false enqueues a background job attributed to the logged-in user (not hardcoded "Analyst").
    3. Unauthenticated requests are rejected with 401.
    """
    case, evidence = case_and_evidence
    admin_user = seed_users["admin"]

    # 1. Direct call without sync parameter defaults to sync=True
    resp_sync = client.post(f"/evidence/{evidence.id}/analyze", headers=admin_headers)
    assert resp_sync.status_code == 200
    data_sync = resp_sync.json()
    assert data_sync["status"] == "success"
    assert data_sync["processing_status"] == "Analyzed"
    assert "Synchronously" in data_sync["message"] or "completed" in data_sync["message"].lower()

    # 2. Call with sync=false enqueues job and attributes to logged-in user
    second_evidence = Evidence(
        case_id=case.id,
        file_name="fiber_sample_analysis.txt",
        file_type="text",
        file_size=64,
        extracted_text="Forensic fiber comparison indicates matching weave on jacket.",
        processing_status=EvidenceStatus.UPLOADED,
        file_hash="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        hash_verified=True
    )
    db.add(second_evidence)
    db.commit()

    resp_async = client.post(f"/evidence/{second_evidence.id}/analyze?sync=false", headers=admin_headers)
    assert resp_async.status_code == 200
    data_async = resp_async.json()
    assert data_async["status"] == "queued"
    job_id = data_async["job_id"]

    db_job = db.query(Job).filter(Job.id == job_id).first()
    assert db_job is not None
    assert db_job.status == "queued"
    # Creator must NOT be the generic hardcoded "Analyst"; must match logged-in user
    assert db_job.created_by == admin_user.full_name
    assert db_job.user_id == admin_user.id

    # 3. Unauthenticated request rejected
    resp_unauth = client.post(f"/evidence/{second_evidence.id}/analyze")
    assert resp_unauth.status_code == 401


