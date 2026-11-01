"""
backend/tests/test_alibi_workflow.py
================================================================================
AUTOMATED TEST SUITE FOR ALIBI VERIFICATION WORKFLOW
================================================================================
Tests:
1. Spatiotemporal Travel Feasibility (Haversine & velocity constraints)
2. Crime Window Coverage & Critical Gap Detection
3. Automated Verification Tasks & InvestigationTask linkage
4. Electronic CDR checks (safeguard: absence of data is never contradicted)
5. Status Roll-Up (Verified, Partly Verified, Contradicted) and Prior Sync
6. Section 180 BNSS / 161 CrPC Confrontation Questions & Chargesheet Refutation
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    Case, User, CasePerson, Hypothesis, Interview, InterviewStatement,
    AlibiClaim, AlibiSegment, AlibiCheck, StatementComparison,
    InvestigationTask, Contradiction, SuspectProfileFactor
)
from alibi_engine import (
    haversine_distance_km, check_travel_feasibility,
    calculate_crime_window_coverage, generate_verification_tasks,
    run_automatic_cdr_check, roll_up_alibi_status,
    generate_confrontation_questions, generate_chargesheet_refutation
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    # Seed User
    user = User(
        id=1,
        email="inspector.patil@police.gov.in",
        full_name="Inspector S. Patil",
        role="lead_investigator",
        hashed_password="hashed_test_password"
    )
    session.add(user)

    # Seed Case
    case = Case(
        id=1,
        title="State of Maharashtra vs. Yogesh Raut & Ors",
        fir_number="FIR-2009-MH-PUN-534",
        crime_number="CR-534/2009",
        incident_date=datetime(2009, 10, 7, 21, 30, tzinfo=timezone.utc),
        status="Active"
    )
    session.add(case)

    # Seed Person (Accused)
    person = CasePerson(
        id=1,
        case_id=1,
        name="Yogesh Ashok Raut",
        role="accused",
        contact_info="+91-98200-44911"
    )
    session.add(person)

    # Seed Hypothesis
    hypo = Hypothesis(
        id=1,
        case_id=1,
        title="H1: Yogesh Raut committed abduction and ATM robbery",
        status="Active"
    )
    session.add(hypo)

    session.commit()
    yield session
    session.close()


def test_travel_feasibility_plausible_vs_impossible(db_session):
    """Verifies that plausible speeds pass and physically impossible speeds fail."""
    # Segment A: Yerwada (18.5529, 73.8797) until 21:00
    seg_a = AlibiSegment(
        id=1,
        claim_id=1,
        segment_order=1,
        start_time=datetime(2009, 10, 7, 20, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 21, 0, tzinfo=timezone.utc),
        time_uncertainty_mins=5,
        claimed_place_name="Yerwada Residence",
        latitude=18.5529,
        longitude=73.8797,
        travel_mode="none"
    )

    # Segment B (Plausible): Pune Station (18.5284, 73.8739) at 21:30 (~3 km in 30 mins)
    seg_b_plausible = AlibiSegment(
        id=2,
        claim_id=1,
        segment_order=2,
        start_time=datetime(2009, 10, 7, 21, 30, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 30, tzinfo=timezone.utc),
        time_uncertainty_mins=5,
        claimed_place_name="Pune Railway Station",
        latitude=18.5284,
        longitude=73.8739,
        travel_mode="car_two_wheeler"
    )

    res_plausible = check_travel_feasibility(seg_a, seg_b_plausible)
    assert res_plausible["is_feasible"] is True
    assert res_plausible["distance_km"] < 5.0
    assert res_plausible["required_speed_kmh"] < 50.0

    # Segment C (Impossible): Mumbai CST (18.9401, 72.8354) at 21:10 (~150 km in 10 mins!)
    seg_c_impossible = AlibiSegment(
        id=3,
        claim_id=1,
        segment_order=2,
        start_time=datetime(2009, 10, 7, 21, 10, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 30, tzinfo=timezone.utc),
        time_uncertainty_mins=0,
        claimed_place_name="Mumbai CST",
        latitude=18.9401,
        longitude=72.8354,
        travel_mode="car_two_wheeler"
    )

    res_impossible = check_travel_feasibility(seg_a, seg_c_impossible)
    assert res_impossible["is_feasible"] is False
    assert "Travel speed anomaly" in (res_impossible["warning"] or "") or "Physically impossible" in (res_impossible["warning"] or "")


def test_crime_window_coverage_and_gaps(db_session):
    """Verifies coverage percentage calculation and critical temporal gap detection."""
    case = db_session.query(Case).filter(Case.id == 1).first()

    # Case incident: 21:30 to 23:30 (120 mins)
    # Alibi only covers 21:30 to 22:00 (30 mins) -> Leaves a 90-min gap
    seg1 = AlibiSegment(
        id=1,
        claim_id=1,
        segment_order=1,
        start_time=datetime(2009, 10, 7, 21, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 0, tzinfo=timezone.utc),
        time_uncertainty_mins=0,
        claimed_place_name="Family Dinner, Kothrud",
        latitude=18.5074,
        longitude=73.8077
    )

    coverage = calculate_crime_window_coverage(case, [seg1])
    assert coverage["coverage_percentage"] == 25.0  # 30 of 120 mins
    assert coverage["has_critical_gaps"] is True
    assert len(coverage["gaps"]) == 1
    assert coverage["gaps"][0]["duration_mins"] == 90.0
    assert coverage["gaps"][0]["severity"] == "critical"


def test_generate_verification_tasks(db_session):
    """Verifies that verification checks and linked InvestigationTask items are properly generated."""
    claim = AlibiClaim(
        id=1,
        case_id=1,
        person_id=1,
        suspect_name="Yogesh Ashok Raut",
        hypothesis_id=1,
        claim_text="I was dining at Hotel Sagar near Swargate with my brother Rajesh from 20:00 to 23:00.",
        status="open",
        is_current=True
    )
    db_session.add(claim)

    seg = AlibiSegment(
        id=1,
        claim_id=1,
        segment_order=1,
        start_time=datetime(2009, 10, 7, 20, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 23, 0, tzinfo=timezone.utc),
        time_uncertainty_mins=15,
        claimed_place_name="Hotel Sagar, Swargate",
        vouching_persons="Rajesh Raut (Brother)",
        travel_mode="none"
    )
    db_session.add(seg)
    db_session.commit()

    checks = generate_verification_tasks(
        claim_id=1,
        user_id=1,
        user_name="Inspector S. Patil",
        db=db_session
    )

    assert len(checks) >= 3  # CDR check, CCTV check (Hotel), Witness check (Rajesh Raut)
    types = [c.source_type for c in checks]
    assert "cdr_tower" in types
    assert "cctv" in types
    assert "witness" in types

    # Verify InvestigationTasks created and linked
    tasks = db_session.query(InvestigationTask).filter(InvestigationTask.case_id == 1).all()
    assert len(tasks) == len(checks)
    for c in checks:
        assert c.investigation_task_id is not None
        linked_task = db_session.query(InvestigationTask).filter(InvestigationTask.id == c.investigation_task_id).first()
        assert linked_task is not None
        assert "Yogesh" in linked_task.task or "Swargate" in linked_task.task


def test_cdr_safeguard_no_data_is_never_contradicted(db_session):
    """Ensures that missing CDR dump records results in inconclusive, NEVER contradicted."""
    claim = AlibiClaim(id=2, case_id=1, suspect_name="Mahesh Thakur", claim_text="At home", status="open")
    db_session.add(claim)
    seg = AlibiSegment(
        id=2,
        claim_id=2,
        start_time=datetime(2009, 10, 7, 21, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 0, tzinfo=timezone.utc),
        claimed_place_name="Hadapsar Residence"
    )
    db_session.add(seg)
    check = AlibiCheck(id=10, claim_id=2, segment_id=2, source_type="cdr_tower", requirement_details="CDR check")
    db_session.add(check)
    db_session.commit()

    res = run_automatic_cdr_check(check_id=10, db=db_session)
    assert res["result"] == "inconclusive"
    assert "Absence of data cannot contradict the alibi" in res["explanation"]


def test_status_roll_up_and_suspect_prior_sync(db_session):
    """Verifies that status rolls up to contradicted and updates suspect profile priors properly."""
    claim = AlibiClaim(
        id=3,
        case_id=1,
        hypothesis_id=1,
        suspect_name="Yogesh Ashok Raut",
        claim_text="I was at Swargate bus depot.",
        status="being_verified"
    )
    db_session.add(claim)
    seg = AlibiSegment(
        id=3,
        claim_id=3,
        start_time=datetime(2009, 10, 7, 21, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 0, tzinfo=timezone.utc),
        claimed_place_name="Swargate Bus Depot"
    )
    db_session.add(seg)

    check = AlibiCheck(
        id=20,
        claim_id=3,
        segment_id=3,
        source_type="cctv",
        requirement_details="Swargate CCTV verification",
        result="contradicted",
        explanation="Swargate Depot camera 04 shows no individual matching suspect; victim ATM camera shows accused at Yerwada at 21:42."
    )
    db_session.add(check)
    db_session.commit()

    summary = roll_up_alibi_status(claim_id=3, db=db_session)
    assert summary["status"] == "contradicted"

    # Verify SuspectProfileFactor was synchronized
    factor = db_session.query(SuspectProfileFactor).filter(
        SuspectProfileFactor.case_id == 1,
        SuspectProfileFactor.hypothesis_id == 1,
        SuspectProfileFactor.factor_type == "alibi_status"
    ).first()
    assert factor is not None
    assert factor.factor_value == "contradicted"
    assert factor.numeric_adjustment == 1.30

    # Verify Contradiction entry created
    conflict = db_session.query(Contradiction).filter(
        Contradiction.case_id == 1,
        Contradiction.conflict_type == "Alibi Discrepancy"
    ).first()
    assert conflict is not None
    assert "Yogesh Ashok Raut" in conflict.statement_a


def test_confrontation_and_chargesheet_refutation(db_session):
    """Verifies generation of Section 180 BNSS confrontation questions and court chargesheet chapter."""
    claim = AlibiClaim(
        id=4,
        case_id=1,
        suspect_name="Yogesh Ashok Raut",
        claim_text="I was at Hinjewadi IT park until 22:30.",
        status="contradicted",
        final_verdict="contradicted",
        verdict_reason="Contradicted by ATM footage and tower dump."
    )
    db_session.add(claim)
    seg = AlibiSegment(
        id=4,
        claim_id=4,
        start_time=datetime(2009, 10, 7, 20, 0, tzinfo=timezone.utc),
        end_time=datetime(2009, 10, 7, 22, 30, tzinfo=timezone.utc),
        claimed_place_name="Hinjewadi Phase 1"
    )
    db_session.add(seg)
    check = AlibiCheck(
        id=30,
        claim_id=4,
        segment_id=4,
        source_type="cctv",
        requirement_details="Hinjewadi Security Gate CCTV",
        result="contradicted",
        explanation="Vehicle MH-12-AQ-4411 exited Kharadi at 21:15, 32 km from Hinjewadi."
    )
    db_session.add(check)
    db_session.commit()

    # Test confrontation questions
    questions = generate_confrontation_questions(claim_id=4, db=db_session)
    assert len(questions) >= 1
    assert "Section 180 BNSS" in questions[0]["statutory_guidance"]
    assert "Hinjewadi" in questions[0]["suggested_question"]

    # Test chargesheet chapter
    refutation = generate_chargesheet_refutation(claim_id=4, db=db_session)
    assert refutation["verdict"] == "contradicted"
    assert "SECTION 193 BNSS" in refutation["chargesheet_markdown"]
    assert "Dudh Nath Pandey v. State of U.P." in refutation["chargesheet_markdown"]

