import pytest
from datetime import datetime, timezone, timedelta
from models import (
    Case, CaseMember, Evidence, CaseDeadline, StatutoryDeadlineRule,
    OffenceEvidenceProtocol, AuditLog, Alert
)
from procedure_engine import (
    ensure_comprehensive_statutory_rules,
    ensure_evidence_protocols,
    recalculate_case_deadlines,
    detect_case_offence_category,
    evaluate_evidence_checklist,
)


@pytest.fixture
def procedure_case(db, seed_users):
    c = Case(
        title="Procedure Tracking Test Case",
        description="Testing legal procedure dates and evidence checklist",
        created_by="Lead Investigator",
        status="active",
        fir_number="FIR-PROC-101/2026",
        fir_date=datetime.now(timezone.utc) - timedelta(days=20),
        incident_date=datetime.now(timezone.utc) - timedelta(days=22),
        arrest_date=datetime.now(timezone.utc) - timedelta(days=15),
        remand_date=datetime.now(timezone.utc) - timedelta(days=4),
        offence_section="Section 302 IPC / Section 103 BNS",
        statutory_time_limit_days=90,
        version=1,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    for role_key in ["admin", "lead_investigator", "analyst", "reviewer"]:
        u = seed_users[role_key]
        m = CaseMember(case_id=c.id, user_id=u.id, case_role=u.role, added_by="Setup")
        db.add(m)
    db.commit()
    return c


def test_statutory_rules_expert_reviewed_table(client, db, analyst_headers, admin_headers):
    ensure_comprehensive_statutory_rules(db)

    # 1. GET /statutory-rules
    res = client.get("/statutory-rules", headers=analyst_headers)
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 6

    heinous_rule = next((r for r in rules if r["offence_category"] == "heinous"), None)
    assert heinous_rule is not None
    assert heinous_rule["limit_days"] == 90
    assert heinous_rule["is_reviewed_by_expert"] is True
    assert heinous_rule["expert_reviewer"] is not None
    assert "Sanjay Dutt" in (heinous_rule["legal_notes"] or "") or "Section 187" in (heinous_rule["legal_notes"] or "")

    # 2. Admin can update rule notes
    rule_id = heinous_rule["id"]
    update_res = client.patch(
        f"/statutory-rules/{rule_id}",
        headers=admin_headers,
        json={"legal_notes": "Reviewed and ratified under Section 187(3) BNSS 2023 with Supreme Court precedents."}
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert "ratified under Section 187(3)" in updated_data["legal_notes"]


def test_recalculate_deadlines_from_procedure_dates(db, procedure_case):
    deadlines = recalculate_case_deadlines(procedure_case.id, db)
    assert len(deadlines) >= 2

    # Verify charge sheet deadline (90 days from arrest_date)
    charge_sheet = next(d for d in deadlines if "Charge Sheet" in d.title)
    expected_due = procedure_case.arrest_date.replace(tzinfo=timezone.utc) + timedelta(days=90)
    assert abs((charge_sheet.due_date.replace(tzinfo=timezone.utc) - expected_due).total_seconds()) < 60

    # Verify 14-day remand review deadline (14 days from remand_date)
    remand_dl = next(d for d in deadlines if "Remand" in d.title)
    expected_remand_due = procedure_case.remand_date.replace(tzinfo=timezone.utc) + timedelta(days=14)
    assert abs((remand_dl.due_date.replace(tzinfo=timezone.utc) - expected_remand_due).total_seconds()) < 60


def test_patch_case_procedure_endpoint(client, procedure_case, lead_headers, db):
    new_arrest = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    new_remand = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    res = client.patch(
        f"/cases/{procedure_case.id}/procedure",
        headers=lead_headers,
        json={
            "fir_number": "FIR-NEW-999/2026",
            "arrest_date": new_arrest,
            "remand_date": new_remand,
            "offence_section": "Section 420 IPC / Section 318 BNS",
            "statutory_time_limit_days": 60,
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["fir_number"] == "FIR-NEW-999/2026"
    assert data["statutory_time_limit_days"] == 60
    assert "Section 420" in data["offence_section"]

    # Check audit log written
    audit = db.query(AuditLog).filter(
        AuditLog.case_id == procedure_case.id,
        AuditLog.action_type == "PROCEDURE_DATES_UPDATED"
    ).first()
    assert audit is not None


def test_evidence_checklist_per_offence_type(client, db, procedure_case, analyst_headers):
    # Case is homicide (Section 302 IPC)
    # Add one matching exhibit: post-mortem report
    ev1 = Evidence(
        case_id=procedure_case.id,
        file_name="autopsy_post_mortem_exam.pdf",
        file_type="application/pdf",
        evidence_type="document",
        upload_date=datetime.now(timezone.utc),
    )
    # Add one matching exhibit: crime scene sketch
    ev2 = Evidence(
        case_id=procedure_case.id,
        file_name="crime_scene_sketch_plan.png",
        file_type="image/png",
        evidence_type="sketch",
        upload_date=datetime.now(timezone.utc),
    )
    db.add_all([ev1, ev2])
    db.commit()

    res = client.get(f"/cases/{procedure_case.id}/evidence-checklist", headers=analyst_headers)
    assert res.status_code == 200
    chk = res.json()

    assert chk["case_id"] == procedure_case.id
    assert chk["offence_category"] == "homicide"
    assert chk["total_expected"] >= 6
    assert chk["present_count"] >= 2
    assert chk["missing_count"] >= 1
    assert chk["mandatory_missing_count"] >= 1
    assert chk["compliance_percentage"] > 0

    # Verify matching
    pm_item = next(i for i in chk["items"] if i["exhibit_code"] == "POST_MORTEM_REPORT")
    assert pm_item["status"] == "present"
    assert pm_item["matched_evidence_id"] == ev1.id

    # Verify missing item has court warning
    inquest_item = next(i for i in chk["items"] if i["exhibit_code"] == "INQUEST_PANCHANAMA")
    assert inquest_item["status"] == "missing"
    assert "Section 194 BNSS" in inquest_item["legal_provision"] or "Section 174 CrPC" in inquest_item["legal_provision"]

    # Check that warnings list contains actionable advisories
    assert len(chk["warnings"]) >= 1
    assert any("Inquest" in w or "Recovery" in w or "FSL" in w for w in chk["warnings"])


def test_detect_case_offence_category():
    assert detect_case_offence_category("Section 302 IPC / Section 103 BNS") == "homicide"
    assert detect_case_offence_category("Section 420 IPC / Section 66D IT Act") == "financial_fraud"
    assert detect_case_offence_category("Section 20(b)(ii)(C) NDPS Act") == "narcotics"
    assert detect_case_offence_category("Section 376 IPC / Section 4 POCSO Act") == "sexual_offence"
    assert detect_case_offence_category("Section 392 IPC Armed Robbery") == "theft_robbery"
    assert detect_case_offence_category("Section 323 IPC Simple Hurt") == "general_cognizable"

