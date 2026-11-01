"""
backend/tests/test_situation_board.py
=====================================
Automated test suite verifying the Live Case Wall (Situation Board):
- Consolidated situation telemetry aggregation
- Leading hypotheses with confidence ranges
- Newest evidence exhibits with integrity and Sec 65B
- Open forensic & custody alerts
- Real-time statutory procedural deadline countdowns
- Online personnel presence
- Presentation / Briefing Mode automatic redaction of restricted data
  (prior criminal records, suspect profiling factors, Section 54 compliance)
"""

from datetime import datetime, timezone, timedelta
import pytest

from models import (
    Case, CaseMember, Evidence, Hypothesis, Alert, CaseDeadline,
    InvestigationTask, Job, PriorRecord, SuspectProfileFactor
)


@pytest.fixture
def situation_test_case(db, seed_users):
    """Creates a complete test case with all situational elements populated."""
    lead = seed_users["lead_investigator"]
    c = Case(
        title="Command Center Situation Board Test Case",
        description="Multi-suspect kidnapping and abduction trial telemetry",
        fir_number="FIR-2026-WALL-001",
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

    # 1. Hypotheses
    h1 = Hypothesis(
        case_id=c.id,
        title="H1: Primary Accused Yogesh Raut Orchestrated Abduction",
        description="DNA and mobile tower coordinates place prime suspect at crime locus",
        combined_score=68.5,
        support_score=68.5,
        evidence_score=65.0,
        background_score=75.0,
        disconfirmation_penalty=0.0,
        status="Active",
    )
    h2 = Hypothesis(
        case_id=c.id,
        title="H2: Approver Rajesh Chaudhari Acted as Secondary Accomplice",
        description="Confession statement under Sec 164 CrPC corroborates vehicle movement",
        combined_score=26.0,
        support_score=26.0,
        evidence_score=24.0,
        background_score=30.0,
        disconfirmation_penalty=0.5,
        status="Active",
    )
    db.add_all([h1, h2])

    # 2. Evidence exhibits
    ev1 = Evidence(
        case_id=c.id,
        file_name="cctv_toll_plaza_feed.mp4",
        file_type="Video",
        evidence_type="cctv",
        file_size=45000000,
        hash_verified=True,
        sec_65b_certificate_present=True,
        processing_status="Analyzed",
        uploaded_by="Forensic Officer",
    )
    ev2 = Evidence(
        case_id=c.id,
        file_name="str_dna_profiling_report.pdf",
        file_type="PDF",
        evidence_type="dna",
        file_size=1200000,
        hash_verified=True,
        sec_65b_certificate_present=False,
        processing_status="Analyzed",
        uploaded_by="Forensic Officer",
    )
    db.add_all([ev1, ev2])

    # 3. Alerts
    a1 = Alert(
        case_id=c.id,
        rule_type="statutory_deadline_approaching",
        severity="critical",
        title="Charge Sheet Filing Deadline in 12 Days",
        message="Statutory 90-day custody deadline expiring pursuant to Section 187 BNSS",
        status="unread",
        dedup_key=f"statutory_{c.id}_deadline",
        is_restricted=False,
    )
    a2 = Alert(
        case_id=c.id,
        rule_type="suspect_prior_conviction",
        severity="warning",
        title="Prior Conviction Record Attached to Raut",
        message="Suspect was previously convicted under Section 392 IPC in 2018",
        status="unread",
        dedup_key=f"prior_record_{c.id}_raut",
        is_restricted=True,
    )
    db.add_all([a1, a2])

    # 4. Statutory Deadlines
    now = datetime.now(timezone.utc)
    d1 = CaseDeadline(
        case_id=c.id,
        title="Statutory 90-day Charge Sheet Filing (Sec 187 BNSS)",
        due_date=now + timedelta(days=12, hours=6),
        status="pending",
    )
    d2 = CaseDeadline(
        case_id=c.id,
        title="Section 65B Electronic Evidence Affidavit Filing",
        due_date=now + timedelta(days=2, hours=14),
        status="pending",
    )
    db.add_all([d1, d2])

    # 5. Investigative Tasks
    t1 = InvestigationTask(
        case_id=c.id,
        task="Obtain certified nodal tower records for IMSI 404-45-6789",
        priority="Critical",
        status="Pending",
        assigned_to="Inspector Shinde",
    )
    db.add(t1)

    # 6. Background Worker Jobs
    j1 = Job(
        case_id=c.id,
        job_type="process_evidence",
        current_stage="verify_citations",
        progress_pct=72.0,
        status="running",
        created_by="Lead Investigator",
    )
    db.add(j1)

    # 7. Restricted Character Evidence & Profile Factors (For Presentation Mode testing)
    pr1 = PriorRecord(
        case_id=c.id,
        suspect_name="Yogesh Raut",
        offense_type="Armed Highway Robbery",
        legal_section="Section 392/397 IPC",
        outcome="conviction",
        source_agency="State Criminal Records Bureau (SCRB)",
    )
    db.add(pr1)

    db.commit()
    return c


def test_situation_board_standard_payload(client, situation_test_case, lead_headers):
    """
    Verifies GET /cases/{case_id}/situation-board returns all 7 situation panels:
    - Leading hypotheses with confidence ranges
    - Newest evidence exhibits with integrity checkmarks
    - Active alerts
    - Real-time deadline countdowns
    - Personnel online
    - Tasks due
    - Jobs running
    """
    case_id = situation_test_case.id
    resp = client.get(f"/cases/{case_id}/situation-board", headers=lead_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Case info
    assert data["case_info"]["id"] == case_id
    assert "FIR-2026-WALL-001" in data["case_info"]["fir_number"]

    # Leading Hypotheses with ranges
    hypotheses = data["leading_hypotheses"]
    assert len(hypotheses) >= 2
    top = hypotheses[0]
    assert top["score"] >= 65.0
    assert top["range_min"] < top["score"]
    assert top["range_max"] > top["score"]
    assert "code" in top

    # Newest evidence
    evidence = data["newest_evidence"]
    assert len(evidence) >= 2
    assert any(e["hash_verified"] is True for e in evidence)

    # Open alerts
    alerts = data["open_alerts"]
    assert len(alerts) >= 2
    assert any(a["severity"] == "critical" for a in alerts)

    # Deadline countdowns
    deadlines = data["deadline_countdowns"]
    assert len(deadlines) >= 2
    first_dl = deadlines[0]
    assert "formatted_countdown" in first_dl
    assert "urgency" in first_dl
    assert first_dl["total_seconds"] > 0

    # Who is online
    online = data["who_is_online"]
    assert len(online) >= 1
    assert any(u["user_role"] in ["lead_investigator", "admin"] for u in online)

    # Tasks due
    tasks = data["tasks_due"]
    assert len(tasks) >= 1
    assert tasks[0]["priority"] == "Critical"

    # Jobs running
    jobs = data["jobs_running"]
    assert len(jobs) >= 1
    assert jobs[0]["status"] == "running"
    assert jobs[0]["progress_pct"] == 72.0

    # Presentation mode flag
    assert data["presentation_mode_active"] is False


def test_situation_board_presentation_mode_redaction(client, situation_test_case, lead_headers):
    """
    Verifies that calling GET /cases/{case_id}/situation-board?presentation_mode=true
    automatically redacts restricted character data (prior records, suspect profiling),
    masks background character scores, and filters restricted alerts pursuant to
    Section 54 of the Indian Evidence Act.
    """
    case_id = situation_test_case.id
    resp = client.get(f"/cases/{case_id}/situation-board?presentation_mode=true", headers=lead_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["presentation_mode_active"] is True
    assert data["redacted_items_count"] >= 1

    # In presentation mode, background scores must be suppressed
    for h in data["leading_hypotheses"]:
        assert h["background_score"] is None
        # Verify title does not contain prejudicial character remarks
        assert "prior convict" not in h["title"].lower()

    # Alerts marked is_restricted or containing prior convictions must be filtered out
    alert_titles = [a["title"] for a in data["open_alerts"]]
    assert not any("Prior Conviction" in t for t in alert_titles)


def test_situation_board_access_denied_for_non_member(client, situation_test_case, reviewer_headers):
    """
    Verifies that a user without access to a private case docket receives 403 Forbidden.
    """
    case_id = situation_test_case.id
    resp = client.get(f"/cases/{case_id}/situation-board", headers=reviewer_headers)
    # Reviewer is not a member of situation_test_case
    assert resp.status_code == 403
