"""
backend/tests/test_streaming_analysis.py
========================================
Automated test suite verifying streaming analysis with partial stage events,
"What Changed" summary generation, and interactive highlighting.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from models import Case, CaseMember, Evidence, Hypothesis, Contradiction
from jobs.pipeline import execute_evidence_pipeline, _stream_pipeline_event


@pytest.fixture
def streaming_case(db, seed_users):
    """Creates a case with member and initial hypotheses for streaming tests."""
    lead = seed_users["lead_investigator"]
    c = Case(
        title="Streaming Analysis Forensic Test",
        description="Verify real-time progressive partial facts streaming",
        fir_number="FIR-2026-STREAM-001",
        status="Active",
        created_by=lead.full_name,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    cm = CaseMember(
        case_id=c.id,
        user_id=lead.id,
        case_role="lead_investigator",
    )
    db.add(cm)

    # Initial Hypotheses for testing score delta tracking
    h1 = Hypothesis(
        case_id=c.id,
        title="Suspect Alpha was at scene",
        description="Location data places Alpha at primary perimeter",
        combined_score=55.0,
        support_score=55.0,
        status="Active",
    )
    h2 = Hypothesis(
        case_id=c.id,
        title="Suspect Beta acted as getaway accomplice",
        description="Vehicle forensics suggest secondary participant",
        combined_score=41.0,
        support_score=41.0,
        status="Active",
    )
    db.add_all([h1, h2])
    db.commit()
    return c


def test_simulate_streaming_endpoint(client, streaming_case, lead_headers):
    """
    Verifies POST /cases/{case_id}/streaming/simulate broadcasts all progressive
    stages and returns the exact 'What Changed' summary requested by the user.
    """
    case_id = streaming_case.id
    resp = client.post(f"/cases/{case_id}/streaming/simulate", headers=lead_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "success"
    assert "3 new entities, 1 new contradiction, H2 moved from 41% to 47%." in data["what_changed_summary"]
    assert "event_id" in data


def test_get_latest_streaming_endpoint(client, streaming_case, lead_headers):
    """
    Verifies GET /cases/{case_id}/streaming/latest returns the cached streaming state
    and what-changed strip information.
    """
    case_id = streaming_case.id

    # Trigger a simulate call first to populate the latest cache
    client.post(f"/cases/{case_id}/streaming/simulate", headers=lead_headers)

    # Query latest streaming state
    resp = client.get(f"/cases/{case_id}/streaming/latest", headers=lead_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["has_stream"] is True
    assert "what_changed_summary" in data
    assert "3 new entities, 1 new contradiction, H2 moved from 41% to 47%." in data["what_changed_summary"]
    payload = data["payload"]
    assert len(payload["new_entities"]) == 3
    assert payload["new_contradictions_count"] == 1
    assert len(payload["score_deltas"]) >= 1


def test_pipeline_stream_events_emission(db, streaming_case):
    """
    Verifies that running execute_evidence_pipeline directly emits the required
    progressive partial facts events:
    - stream_stage_text
    - stream_stage_entities
    - stream_stage_citations
    - stream_stage_contradictions
    - stream_stage_scores
    - stream_stage_completed
    """
    case_id = streaming_case.id
    from models import EvidenceStatus, Job

    # Create an evidence item to process
    ev = Evidence(
        case_id=case_id,
        file_name="surveillance_feed_cam4.txt",
        storage_path="uploads/surveillance_feed_cam4.txt",
        file_type="forensic_report",
        file_size=1200,
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extracted_text="Suspect Vikram Rao seen leaving ATM at 23:45. Vehicle DL-04-AB-1234 identified.",
        processing_status=EvidenceStatus.QUEUED,
        uploaded_by="Lead Investigator",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Create a processing job for this evidence
    job = Job(
        case_id=case_id,
        exhibit_id=ev.id,
        job_type="process_evidence",
        status="queued",
        created_by="Lead Investigator",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    captured_events = []

    def mock_publish(db, case_id, event_type, payload=None, user_id=None, summary="", item_type=None, item_id=None, commit=True):
        captured_events.append({
            "case_id": case_id,
            "event_type": event_type,
            "payload": payload or {},
            "summary": summary,
        })
        mock_ev = MagicMock()
        mock_ev.id = 123
        return mock_ev

    mock_analysis_result = {
        "text": ev.extracted_text,
        "summary": "Surveillance footage report analysis",
        "entities": [{"name": "Vikram Rao", "type": "Person", "confidence": 0.95}],
        "events": [{"title": "ATM Exit", "timestamp": "2026-10-30 23:45:00", "description": "Left ATM"}],
        "claims": [{"claim": "Suspect left ATM", "category": "Action"}],
        "extraction_mode": "live",
        "is_demo_fixture": False,
    }

    def mock_scoring_run(case_id, db, triggered_by=""):
        # Shift H2 score from 41% to 47% during rescore
        h2 = db.query(Hypothesis).filter(Hypothesis.case_id == case_id, Hypothesis.title.like("%Beta%")).first()
        if h2:
            h2.combined_score = 47.0
            h2.support_score = 47.0
            db.commit()
        return {"status": "completed", "success": True, "hypotheses": [{"id": 2, "score": 47.0}]}

    mock_detector = MagicMock()
    mock_detector.detect_contradictions_for_case.return_value = {"new_contradictions_detected": 1}

    with patch("collaboration.publish_collaboration_event", side_effect=mock_publish):
        with patch("jobs.pipeline.run_comprehensive_analysis", return_value=mock_analysis_result):
            with patch("jobs.pipeline.anchor_fact_citation", return_value=True):
                with patch("nli_engine.ForensicNLIDetector", return_value=mock_detector):
                    with patch("jobs.pipeline.execute_scoring_run", side_effect=mock_scoring_run):
                        # Execute pipeline
                        success = execute_evidence_pipeline(job.id, db)
                        assert success is True

    event_types = [e["event_type"] for e in captured_events]
    assert "stream_stage_text" in event_types, f"Missing stream_stage_text in {event_types}"
    assert "stream_stage_entities" in event_types, f"Missing stream_stage_entities in {event_types}"
    assert "stream_stage_citations" in event_types, f"Missing stream_stage_citations in {event_types}"
    assert "stream_stage_contradictions" in event_types, f"Missing stream_stage_contradictions in {event_types}"
    assert "stream_stage_scores" in event_types, f"Missing stream_stage_scores in {event_types}"
    assert "stream_stage_completed" in event_types, f"Missing stream_stage_completed in {event_types}"

    # Verify stage completed payload
    completion_event = next(e for e in captured_events if e["event_type"] == "stream_stage_completed")
    payload = completion_event["payload"]
    assert "what_changed_summary" in payload
    assert "1 new entity" in payload["what_changed_summary"] or "entities" in payload["what_changed_summary"]
