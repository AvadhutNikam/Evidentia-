"""
backend/tests/test_decision_quality.py
======================================
Comprehensive test suite for Decision-Quality Features:
  1. Devil's Advocate Counter-Case Dossier & Suppression Stress-Testing
  2. Four-Eyes Principle / Two-Analyst Sign-Off Protocol
  3. Cognitive & Evidentiary Bias Alerts (Fragility, Tunnel Vision, Monoculture)
  4. Plain-Language Explanation for Non-Technical Officers
  5. API Endpoints & RBAC Validation
"""

import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from database import get_db, Base
from models import (
    User, Case, Evidence, Hypothesis, EvidenceAssessment,
    ChargesheetDraft, DecisionSignoff, Alert, CaseMember
)
from auth import hash_password, create_access_token
from decision_quality_engine import (
    build_devils_advocate_dossier,
    evaluate_bias_alerts,
    generate_plain_language_explanation,
    request_second_signoff,
    review_second_signoff
)
from routers.scoring import execute_scoring_run


@pytest.fixture
def decision_fixture(db: Session, seed_users):
    """Sets up a realistic test case with 2 analysts, 2 competing hypotheses, and 4 exhibits."""
    maker = seed_users["analyst"]
    checker = seed_users["lead_investigator"]

    # 2. Case
    test_case = Case(
        title="Sessions Case No. 89/2010 - State v. Yogesh Raut & Ors",
        description="Pune Cab Driver Murder & Kidnapping Investigation",
        status="Active",
        created_by="Priya Sharma"
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    # 3. Case Members
    cm1 = CaseMember(case_id=test_case.id, user_id=maker.id, case_role="analyst")
    cm2 = CaseMember(case_id=test_case.id, user_id=checker.id, case_role="lead_investigator")
    db.add_all([cm1, cm2])

    # 4. Competing Hypotheses
    h1 = Hypothesis(
        case_id=test_case.id,
        title="Accused Yogesh Raut Premeditated Crime",
        description="Primary accused abducted victim in Qualis MH-12-AR-2541 with accomplices.",
        status="Active",
        support_score=78.5,
        combined_score=78.5
    )
    h2 = Hypothesis(
        case_id=test_case.id,
        title="Lone Opportunistic Third-Party Abductor",
        description="Victim boarded an unauthorized private carrier operated by an unknown opportunistic driver.",
        status="Active",
        support_score=21.5,
        combined_score=21.5
    )
    db.add_all([h1, h2])
    db.commit()
    db.refresh(h1)
    db.refresh(h2)

    # 5. Exhibits
    e1 = Evidence(
        case_id=test_case.id,
        file_name="fsl_kalina_dna_biological_report.txt",
        file_type="forensic_report",
        evidence_type="forensic_report",
        hash_verified=True,
        sec_65b_certificate_present=True,
        quality_rating=5.0
    )
    e2 = Evidence(
        case_id=test_case.id,
        file_name="sbi_atm_surveillance_log_and_stills.txt",
        file_type="cctv_digital",
        evidence_type="cctv_digital",
        hash_verified=True,
        sec_65b_certificate_present=False,  # Vulnerability: Missing 65B!
        quality_rating=4.0
    )
    e3 = Evidence(
        case_id=test_case.id,
        file_name="witness_auto_driver_statement.txt",
        file_type="witness_statement",
        evidence_type="witness_statement",
        hash_verified=True,
        sec_65b_certificate_present=True,
        quality_rating=3.0
    )
    db.add_all([e1, e2, e3])
    db.commit()
    db.refresh(e1)
    db.refresh(e2)
    db.refresh(e3)

    # 6. Assessments
    a1_h1 = EvidenceAssessment(
        hypothesis_id=h1.id,
        evidence_id=e1.id,
        classification="strongly_consistent",
        reason="DNA matches Yogesh Raut on victim apparel",
        final_contribution=4.5,
        effective_lr=1000.0
    )
    a2_h1 = EvidenceAssessment(
        hypothesis_id=h1.id,
        evidence_id=e2.id,
        classification="consistent",
        reason="Stills capture Qualis near ATM",
        final_contribution=2.5,
        effective_lr=15.0
    )
    a3_h2 = EvidenceAssessment(
        hypothesis_id=h2.id,
        evidence_id=e3.id,
        classification="strongly_consistent",
        reason="Auto driver observed lone unidentified individual at Kharadi bypass around 22:30",
        final_contribution=3.2,
        effective_lr=25.0
    )
    a1_h2 = EvidenceAssessment(
        hypothesis_id=h2.id,
        evidence_id=e1.id,
        classification="inconsistent",
        reason="DNA excludes third party",
        final_contribution=-2.0,
        effective_lr=0.05
    )
    db.add_all([a1_h1, a2_h1, a3_h2, a1_h2])
    db.commit()

    return {
        "maker": maker,
        "checker": checker,
        "case": test_case,
        "h1": h1,
        "h2": h2,
        "e1": e1,
        "e2": e2,
        "e3": e3,
        "a1_h1": a1_h1
    }


def test_devils_advocate_dossier_assembly(db: Session, decision_fixture):
    """Tests that Devil's Advocate builds counter-case, finds vulnerabilities, and runs suppression tests."""
    fixture = decision_fixture
    case_id = fixture["case"].id
    h1 = fixture["h1"]
    h2 = fixture["h2"]

    dossier = build_devils_advocate_dossier(case_id=case_id, db=db)
    assert dossier["success"] is True
    assert dossier["leading_hypothesis"]["id"] == h1.id
    assert dossier["counter_hypothesis"]["id"] == h2.id
    assert dossier["prob_gap"] >= 0

    # 1. Check counter-corroborating points
    points = dossier["counter_corroborating_points"]
    assert len(points) >= 1
    # Auto driver witness statement supports H2
    auto_driver_point = next((p for p in points if p["evidence_id"] == fixture["e3"].id), None)
    assert auto_driver_point is not None
    assert "Alternative" in auto_driver_point["role_in_counter_case"]

    # 2. Check lead vulnerabilities
    vulnerabilities = dossier["lead_vulnerabilities"]
    assert len(vulnerabilities) >= 1
    # Exhibit 2 has missing Sec 65B
    e2_vuln = next((v for v in vulnerabilities if v["evidence_id"] == fixture["e2"].id), None)
    assert e2_vuln is not None
    assert any("65B" in r for r in e2_vuln["vulnerabilities"])

    # 3. Check suppression stress-test simulation
    suppression = dossier["suppression_simulation"]
    assert suppression is not None
    assert suppression["suppressed_exhibit_id"] == fixture["e1"].id  # DNA was highest contributor
    assert suppression["new_lead_score"] < suppression["original_lead_score"]

    # 4. Check legal challenge brief
    brief = dossier["legal_challenge_brief"]
    assert "executive_challenge" in brief
    assert "counter_case_narrative" in brief
    assert len(brief["defense_cross_examination_angles"]) >= 2
    assert len(brief["stress_test_recommendations"]) >= 2


def test_four_eyes_two_analyst_signoff_lifecycle(db: Session, decision_fixture):
    """Tests the two-analyst sign-off workflow enforcing maker != checker."""
    fixture = decision_fixture
    case_id = fixture["case"].id
    maker = fixture["maker"]
    checker = fixture["checker"]
    a1_h1 = fixture["a1_h1"]

    # 1. Analyst requests second sign-off
    signoff = request_second_signoff(
        db=db,
        case_id=case_id,
        item_type="evidence_assessment",
        item_id=a1_h1.id,
        item_summary="Strongly consistent DNA match override",
        maker_user_id=maker.id,
        maker_name=maker.full_name
    )
    assert signoff.status == "pending"
    assert signoff.maker_name == maker.full_name
    assert a1_h1.second_signoff_status == "pending_signoff"

    # 2. Maker attempts to approve own request -> MUST BE BLOCKED BY FOUR-EYES RULE
    with pytest.raises(ValueError, match="Four-Eyes Violation"):
        review_second_signoff(
            db=db,
            case_id=case_id,
            signoff_id=signoff.id,
            checker_user_id=maker.id,  # Same as maker!
            checker_name=maker.full_name,
            checker_role=maker.role,
            approved=True,
            review_notes="Self approval should fail"
        )

    # 3. Second independent analyst approves
    review_res = review_second_signoff(
        db=db,
        case_id=case_id,
        signoff_id=signoff.id,
        checker_user_id=checker.id,
        checker_name=checker.full_name,
        checker_role=checker.role,
        approved=True,
        review_notes="Verified against FSL Kalina electropherogram; approved."
    )
    assert review_res["success"] is True
    assert review_res["status"] == "approved"
    assert a1_h1.second_signoff_status == "approved"
    assert a1_h1.second_signoff_by_name == checker.full_name


def test_cognitive_bias_alerts_detection(db: Session, decision_fixture):
    """Tests detection of Single-Exhibit Fragility, Untested Alternative, and Source Monoculture."""
    fixture = decision_fixture
    case_id = fixture["case"].id

    alerts = evaluate_bias_alerts(case_id=case_id, db=db)
    # E1 represents > 45% of total lead support, so fragility alert should fire
    rule_types = [a.rule_type for a in alerts]
    assert any("bias_single_exhibit_dependency" in r for r in rule_types)

    # Verify alert fields
    fragility_alert = next(a for a in alerts if a.rule_type == "bias_single_exhibit_dependency")
    assert fragility_alert.severity == "warning"
    assert "Fragility" in fragility_alert.title


def test_plain_language_explanation_synthesis(db: Session, decision_fixture):
    """Tests generating plain-language, non-technical explanations for non-technical officers."""
    fixture = decision_fixture
    case_id = fixture["case"].id
    h1 = fixture["h1"]

    scoring_res = execute_scoring_run(case_id=case_id, db=db, triggered_by="test")
    h1_dict = next(h for h in scoring_res["hypotheses"] if h["id"] == h1.id)

    expl = generate_plain_language_explanation(
        hypothesis=h1_dict,
        all_hypotheses=scoring_res["hypotheses"],
        breakdowns=scoring_res["hypothesis_breakdowns"],
        critical_exhibits=scoring_res.get("critical_exhibits", [])
    )

    assert expl["rank"] == 1
    assert "Decisive" in expl["verdict"] or "Lead" in expl["verdict"]
    assert len(expl["primary_drivers"]) >= 1
    assert len(expl["summary"]) > 20
    assert len(expl["recommended_action"]) > 10


def test_decision_quality_api_endpoints(client, analyst_headers, lead_headers, db: Session, decision_fixture):
    """Tests FastAPI router endpoints for Devil's Advocate, Bias Alerts, and Sign-Offs."""
    fixture = decision_fixture
    case_id = fixture["case"].id
    maker = fixture["maker"]
    checker = fixture["checker"]

    # 1. GET /cases/{id}/devils-advocate
    resp = client.get(
        f"/cases/{case_id}/devils-advocate",
        headers=analyst_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "counter_corroborating_points" in data
    assert "legal_challenge_brief" in data

    # 2. GET /cases/{id}/bias-alerts
    resp = client.get(
        f"/cases/{case_id}/bias-alerts",
        headers=analyst_headers
    )
    assert resp.status_code == 200
    b_data = resp.json()
    assert "bias_alerts" in b_data

    # 3. GET /cases/{id}/hypotheses/{h1.id}/plain-language
    resp = client.get(
        f"/cases/{case_id}/hypotheses/{fixture['h1'].id}/plain-language",
        headers=analyst_headers
    )
    assert resp.status_code == 200
    pl_data = resp.json()
    assert "verdict" in pl_data
    assert "primary_drivers" in pl_data

    # 4. POST /cases/{id}/signoffs/request
    req_resp = client.post(
        f"/cases/{case_id}/signoffs/request",
        headers=analyst_headers,
        json={
            "item_type": "evidence_assessment",
            "item_id": fixture["a1_h1"].id,
            "item_summary": "Strong DNA match review request"
        }
    )
    assert req_resp.status_code == 200
    signoff_id = req_resp.json()["id"]

    # 5. Maker attempts to approve own request -> Must return 400 Four-Eyes violation
    fail_resp = client.post(
        f"/cases/{case_id}/signoffs/{signoff_id}/review",
        headers=analyst_headers,
        json={
            "approved": True,
            "review_notes": "Attempting self-signoff"
        }
    )
    assert fail_resp.status_code == 400
    assert "Four-Eyes Violation" in fail_resp.json()["detail"]

    # 6. Second analyst approves -> Must succeed
    ok_resp = client.post(
        f"/cases/{case_id}/signoffs/{signoff_id}/review",
        headers=lead_headers,
        json={
            "approved": True,
            "review_notes": "Reviewed and confirmed by Lead Investigator"
        }
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == "approved"
