"""
Unit & Integration Tests for Cross-Case Intelligence & Entity Resolution Engine.

Validates:
1. Multi-Tier Entity Resolution:
   - Tier 1: Exact Phone number normalization & matching.
   - Tier 1: Exact Vehicle plate standardization & matching.
   - Tier 1: Digital telemetry (IP, Crypto, IMEI) matching.
   - Tier 2: Exact person name and location matching.
   - Tier 3: Fuzzy person name (>=85% token sort ratio) & address matching.
   - Dissimilar entities rejected (no false positives).
2. Reviewer Confirmation Workflow:
   - Discovery queues links as 'pending_review'.
   - Confirmation / Rejection transitions with reviewer notes.
   - Cryptographic Merkle Audit Chain logging.
3. Cross-Case MO Similarity:
   - 5-dimensional relevance engine (weapon, entry method, victim type, location type, timing).
   - High similarity detection for analogous tradecraft.
   - Low similarity insulation for disparate crimes.
4. Strict RBAC Tenant Isolation:
   - Non-admin users only see links and MO candidates for cases they have membership in.
   - Cross-case data from unassigned dockets is strictly excluded.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    Case, Entity, CaseMember, User, CrossCaseEntityLink,
    AuditLog, PriorRecord, SuspectProfileFactor
)
from cross_case_engine import (
    normalize_phone_number,
    extract_vehicle_plate,
    extract_digital_identifier,
    normalize_person_name,
    compute_string_similarity,
    match_entity_pair,
    resolve_cross_case_entities,
    get_cross_case_entity_links,
    confirm_or_reject_entity_link,
    find_mo_similar_cases,
    extract_case_mo_profile
)
from auth import hash_password, check_case_access, get_user_accessible_case_ids


@pytest.fixture(scope="function")
def db_session():
    """Isolated in-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed Admin User
    admin = User(
        email="admin@test.gov.in",
        full_name="Admin Director",
        hashed_password=hash_password("adminpass123"),
        role="admin"
    )
    # Seed Analyst User
    analyst = User(
        email="analyst@test.gov.in",
        full_name="Detective Pawar",
        hashed_password=hash_password("analystpass123"),
        role="analyst"
    )
    # Seed Restricted Reviewer
    reviewer = User(
        email="reviewer@test.gov.in",
        full_name="Inspector Deshmukh",
        hashed_password=hash_password("reviewerpass123"),
        role="reviewer"
    )
    session.add_all([admin, analyst, reviewer])
    session.commit()

    # Seed Cases
    case1 = Case(
        title="State vs. Raut & Gang (Pune Cab Abduction)",
        description="Abduction and robbery of female IT employee near Kharadi bypass at night in Qualis cab using iron jack rod.",
        status="Active",
        fir_number="FIR-2009-PUNE-01",
        created_by="Admin"
    )
    case2 = Case(
        title="State vs. Highway Robbery Syndicate",
        description="Armed robbery of commuters along arterial bypass at night using metallic rod and fake vehicle decoy.",
        status="Under Investigation",
        fir_number="FIR-2010-BLR-02",
        created_by="Admin"
    )
    case3 = Case(
        title="State vs. Financial Cyber Intrusion",
        description="Data exfiltration from corporate servers using malicious malware payload and remote command and control.",
        status="Active",
        fir_number="FIR-2022-CYBER-03",
        created_by="Admin"
    )
    case4 = Case(
        title="Restricted Internal Investigation (Top Secret)",
        description="Classified counter-espionage docket restricted to specific taskforce.",
        status="Active",
        fir_number="FIR-TOP-SECRET-04",
        created_by="Admin"
    )
    session.add_all([case1, case2, case3, case4])
    session.commit()

    # Grant Analyst membership only to Case 1 and Case 2
    session.add_all([
        CaseMember(case_id=case1.id, user_id=analyst.id, case_role="analyst"),
        CaseMember(case_id=case2.id, user_id=analyst.id, case_role="analyst"),
    ])
    session.commit()

    yield session
    session.close()


# ==============================================================================
# TEST 1: NORMALIZATION & IDENTIFIER EXTRACTION
# ==============================================================================

def test_identifier_normalizations():
    # 1. Phone numbers
    assert normalize_phone_number("+91-98200-44911 (Primary)") == "+919820044911"
    assert normalize_phone_number("Burner Mobile 9820044911 recovered") == "+919820044911"
    assert normalize_phone_number("09820044911") == "+919820044911"
    assert normalize_phone_number("No phone present") is None

    # 2. Vehicle plates
    assert extract_vehicle_plate("Toyota Qualis (MH-12-AQ-4411)") == "MH12AQ4411"
    assert extract_vehicle_plate("Bus DL-1P-C-0149 impounded") == "DL1PC0149"
    assert extract_vehicle_plate("KA 01 AB 1234 spotted") == "KA01AB1234"
    assert extract_vehicle_plate("Bicycle in alley") is None

    # 3. Digital identifiers
    ip_res = extract_digital_identifier("Node IP: 185.220.101.5")
    assert ip_res == ("ip_address", "185.220.101.5")

    email_res = extract_digital_identifier("Contact suspect at operative44@protonmail.com")
    assert email_res == ("email", "operative44@protonmail.com")

    # 4. Person name normalization
    assert normalize_person_name("Dr. Rajesh Talwar (Person of Interest)") == "rajesh talwar"
    assert normalize_person_name("Mukesh Singh (Accused - Driver)") == "mukesh singh"
    assert normalize_person_name("Advocate Kadam") == "kadam"

    # 5. Fuzzy string similarity
    assert compute_string_similarity("yogesh raut", "yogesh raut") == 1.0
    assert compute_string_similarity("yogesh raut", "raut yogesh") == 1.0  # Token sort
    assert compute_string_similarity("yogesh raut", "yogesh ashok raut") >= 0.75


# ==============================================================================
# TEST 2: MULTI-TIER ENTITY RESOLUTION LOGIC
# ==============================================================================

def test_multi_tier_matching_engine():
    # Tier 1: Exact Phone Match
    phone_src = Entity(id=1, case_id=1, type="Phone", name="+91-98200-44911 (CDR Dump)")
    phone_tgt = Entity(id=2, case_id=2, type="Phone", name="SIM 9820044911 Handset Seized")
    res_phone = match_entity_pair(phone_src, phone_tgt, 1, 2)
    assert res_phone is not None
    assert res_phone["entity_type"] == "phone"
    assert res_phone["match_type"] == "exact_identifier"
    assert res_phone["similarity_score"] == 1.0

    # Tier 1: Exact Vehicle Plate Match
    veh_src = Entity(id=3, case_id=1, type="Vehicle", name="Toyota Qualis (MH-12-AQ-4411)")
    veh_tgt = Entity(id=4, case_id=2, type="Vehicle", name="Qualis MH12-AQ-4411 Seen at toll")
    res_veh = match_entity_pair(veh_src, veh_tgt, 1, 2)
    assert res_veh is not None
    assert res_veh["entity_type"] == "vehicle"
    assert res_veh["match_type"] == "exact_identifier"
    assert res_veh["match_value"] == "MH12AQ4411"

    # Tier 2: Exact Person Name Match
    person_src = Entity(id=5, case_id=1, type="Suspect", name="Yogesh Raut")
    person_tgt = Entity(id=6, case_id=2, type="PersonOfInterest", name="Yogesh Raut")
    res_person_exact = match_entity_pair(person_src, person_tgt, 1, 2)
    assert res_person_exact is not None
    assert res_person_exact["match_type"] == "exact_name"
    assert res_person_exact["similarity_score"] == 0.95

    # Tier 3: Fuzzy / Variant Person Name Match
    person_long = Entity(id=7, case_id=2, type="Suspect", name="Yogesh Ashok Raut")
    res_variant = match_entity_pair(person_src, person_long, 1, 2)
    assert res_variant is not None
    assert res_variant["match_type"] == "fuzzy_name"
    assert res_variant["similarity_score"] >= 0.85

    # Dissimilar Persons Should NOT Match
    diff_person1 = Entity(id=8, case_id=1, type="Suspect", name="Mahesh Thakur")
    diff_person2 = Entity(id=9, case_id=2, type="Suspect", name="Akshay Thakur")
    res_diff = match_entity_pair(diff_person1, diff_person2, 1, 2)
    assert res_diff is None


# ==============================================================================
# TEST 3: SCAN & REVIEW CONFIRMATION WORKFLOW
# ==============================================================================

def test_entity_resolution_and_review_lifecycle(db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.gov.in").first()
    analyst = db_session.query(User).filter(User.email == "analyst@test.gov.in").first()

    # Seed entities across Case 1 and Case 2
    e1 = Entity(case_id=1, type="Phone", name="+91-98200-44911 (CDR Dump)")
    e2 = Entity(case_id=1, type="Vehicle", name="Toyota Qualis (MH-12-AQ-4411)")
    e3 = Entity(case_id=1, type="Suspect", name="Yogesh Raut")
    db_session.add_all([e1, e2, e3])

    e4 = Entity(case_id=2, type="Phone", name="Burner (+91-98200-44911)")
    e5 = Entity(case_id=2, type="Vehicle", name="White Qualis MH-12-AQ-4411")
    e6 = Entity(case_id=2, type="Suspect", name="Yogesh Ashok Raut")
    db_session.add_all([e4, e5, e6])
    db_session.commit()

    # Trigger resolution scan as Analyst
    links = resolve_cross_case_entities(case_id=1, user=analyst, db=db_session)
    assert len(links) >= 3

    # All newly discovered links must be in 'pending_review'
    for link in links:
        assert link["status"] == "pending_review"

    # Confirm the Vehicle link with notes
    veh_link = next(l for l in links if l["entity_type"] == "vehicle")
    confirm_res = confirm_or_reject_entity_link(
        link_id=veh_link["id"],
        status="confirmed",
        user=analyst,
        notes="Confirmed identical vehicle plate with RTO Pune register.",
        db=db_session
    )
    assert confirm_res["status"] == "confirmed"
    assert confirm_res["reviewer_notes"] == "Confirmed identical vehicle plate with RTO Pune register."

    # Verify audit chain entry was created
    audit = db_session.query(AuditLog).filter(
        AuditLog.action_type == "CROSS_CASE_ENTITY_LINK_REVIEWED",
        AuditLog.target_id == str(veh_link["id"])
    ).first()
    assert audit is not None
    assert "MH12AQ4411" in audit.description
    assert audit.current_hash is not None

    # Reject another link (e.g., if investigator determines false lead)
    phone_link = next(l for l in links if l["entity_type"] == "phone")
    reject_res = confirm_or_reject_entity_link(
        link_id=phone_link["id"],
        status="rejected",
        user=analyst,
        notes="Burner SIM was sold to subsequent user prior to incident.",
        db=db_session
    )
    assert reject_res["status"] == "rejected"


# ==============================================================================
# TEST 4: CROSS-CASE MO SIMILARITY & RELEVANCE ENGINE
# ==============================================================================

def test_mo_similarity_tradecraft_comparison(db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.gov.in").first()

    # Prior record in Case 1
    p1 = PriorRecord(
        case_id=1,
        suspect_name="Yogesh Raut",
        offense_type="Violent Highway Robbery",
        outcome="convicted",
        source_agency="Pune City Police",
        weapon_used="Iron rod / jack handle",
        entry_method="Fake transport / cab route intercept",
        victim_type="Lone female commuter post-evening shift",
        location_type="Desolate transit bypass / isolated corridor",
        time_pattern="Late night 21:00-01:00"
    )
    db_session.add(p1)
    db_session.commit()

    # Query MO similarity for Case 1
    similar = find_mo_similar_cases(case_id=1, user=admin, db=db_session, min_similarity=0.10)
    assert len(similar) >= 1

    # Case 2 shares highway bypass, transit ambush, late night timing, metallic tool
    case2_match = next((s for s in similar if s["case_id"] == 2), None)
    assert case2_match is not None
    assert case2_match["similarity_percentage"] >= 45.0
    assert len(case2_match["matched_features"]) >= 2

    # Case 3 (Cyber Intrusion) has no physical tradecraft overlap with violent transit homicide
    case3_match = next((s for s in similar if s["case_id"] == 3), None)
    if case3_match:
        # Must be very low
        assert case3_match["similarity_percentage"] < 35.0


# ==============================================================================
# TEST 5: STRICT RBAC ISOLATION & PERMISSION BOUNDARIES
# ==============================================================================

def test_cross_case_rbac_tenant_isolation(db_session):
    admin = db_session.query(User).filter(User.email == "admin@test.gov.in").first()
    analyst = db_session.query(User).filter(User.email == "analyst@test.gov.in").first()
    reviewer = db_session.query(User).filter(User.email == "reviewer@test.gov.in").first()

    # Seed entity in Case 1 (Analyst has access)
    e_c1 = Entity(case_id=1, type="Vehicle", name="Toyota Qualis (MH-12-AQ-4411)")
    # Seed matching entity in Case 2 (Analyst has access)
    e_c2 = Entity(case_id=2, type="Vehicle", name="Decoy Qualis (MH-12-AQ-4411)")
    # Seed matching entity in Case 4 (RESTRICTED: Analyst DOES NOT have access)
    e_c4 = Entity(case_id=4, type="Vehicle", name="Surveillance Qualis (MH-12-AQ-4411)")

    db_session.add_all([e_c1, e_c2, e_c4])
    db_session.commit()

    # 1. Admin scans Case 1: Can see links to both Case 2 and Case 4
    admin_links = resolve_cross_case_entities(case_id=1, user=admin, db=db_session)
    linked_case_ids_admin = {l["linked_case_id"] for l in admin_links}
    assert 2 in linked_case_ids_admin
    assert 4 in linked_case_ids_admin

    # 2. Analyst scans Case 1: MUST ONLY see Case 2. Case 4 MUST NOT appear!
    analyst_links = get_cross_case_entity_links(case_id=1, user=analyst, db=db_session)
    linked_case_ids_analyst = {l["linked_case_id"] for l in analyst_links}
    assert 2 in linked_case_ids_analyst
    assert 4 not in linked_case_ids_analyst  # Restricted docket data is NOT leaked!

    # 3. MO Similarity check for Analyst: Case 4 MUST NOT appear in similar cases
    analyst_mo = find_mo_similar_cases(case_id=1, user=analyst, db=db_session, min_similarity=0.01)
    similar_case_ids_analyst = {s["case_id"] for s in analyst_mo}
    assert 4 not in similar_case_ids_analyst

    # 4. Reviewer has NO membership in Case 1 -> Attempt to access Case 1 denied
    reviewer_links = get_cross_case_entity_links(case_id=1, user=reviewer, db=db_session)
    assert len(reviewer_links) == 0

    reviewer_mo = find_mo_similar_cases(case_id=1, user=reviewer, db=db_session)
    assert len(reviewer_mo) == 0


# ==============================================================================
# TEST 6: REAL-TIME CROSS-CASE MATCHING ON NEW EXHIBIT & CONFIRMATION SAFEGUARD
# ==============================================================================

def test_realtime_cross_case_matching_on_new_exhibit(db_session):
    from cross_case_engine import match_exhibit_cross_case_realtime, get_connected_cases_summary
    from models import Alert, Evidence

    admin = db_session.query(User).filter(User.email == "admin@test.gov.in").first()

    # Pre-seed target Case 2 with known suspect phone, plate, address, and name
    ent_phone = Entity(case_id=2, type="Phone", name="+91-98200-44911")
    ent_plate = Entity(case_id=2, type="Vehicle", name="MH-12-DE-1433")
    ent_addr = Entity(case_id=2, type="Location", name="Kharadi Bypass, Pune")
    ent_name = Entity(case_id=2, type="Person", name="Yogesh Raut")
    db_session.add_all([ent_phone, ent_plate, ent_addr, ent_name])
    db_session.commit()

    # Ingest a brand new exhibit into Case 1
    new_evidence = Evidence(
        case_id=1,
        file_name="Recovered_Notebook_Panchnama.txt",
        file_type="Document",
        file_size=2048,
        storage_path="uploads/test_notebook.txt",
        uploaded_by="Detective Pawar",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extracted_text=(
            "SEIZURE PANCHNAMA: At the scene, recovered a pocket diary with handwritten mobile +91-98200-44911 "
            "and vehicle plate MH12-DE-1433 spotted leaving Kharadi Bypass. Identified key suspect as Yogesh Raut."
        ),
        hash_verified=True,
        chain_of_custody_complete=True,
        sec_65b_certificate_present=True
    )
    db_session.add(new_evidence)
    db_session.commit()

    # Trigger real-time cross-case matcher on this new exhibit
    flagged = match_exhibit_cross_case_realtime(
        evidence_id=new_evidence.id,
        user=admin,
        db=db_session
    )

    # 1. Verify candidate links are flagged
    assert len(flagged) >= 3
    matched_types = {f["entity_type"] for f in flagged}
    assert "phone" in matched_types
    assert "vehicle" in matched_types
    assert "person" in matched_types or "address" in matched_types

    # 2. Verify all flagged links have status strictly 'pending_review' (NEVER auto-merged!)
    for f in flagged:
        assert f["status"] == "pending_review"

    # 3. Verify deduplicated alerts raised for the investigator
    alerts = db_session.query(Alert).filter(Alert.case_id == 1, Alert.rule_type == "cross_case_match").all()
    assert len(alerts) >= 1
    assert "Possibly Connected Case: Case #2" in alerts[0].title

    # 4. Verify connected cases summary
    summary = get_connected_cases_summary(case_id=1, user=admin, db=db_session)
    assert summary["total_connected_cases"] >= 1
    assert summary["pending_candidates_count"] >= 1

    case2_group = next((c for c in summary["connected_cases"] if c["linked_case_id"] == 2), None)
    assert case2_group is not None
    assert case2_group["has_pending_review"] is True
    assert len(case2_group["matching_features"]) >= 3


# ==============================================================================
# TEST 7: STRICT PERMISSIONS BOUNDARY ON LINK VISIBILITY & CONFIRMATION
# ==============================================================================

def test_cross_case_link_visibility_requires_both_cases(db_session):
    from cross_case_engine import get_connected_cases_summary, confirm_or_reject_entity_link

    analyst = db_session.query(User).filter(User.email == "analyst@test.gov.in").first()
    reviewer = db_session.query(User).filter(User.email == "reviewer@test.gov.in").first()

    # Case 4 is restricted: Analyst has access to Case 1 and 2, but NOT Case 4
    # Create an entity in Case 4
    ent_c4 = Entity(case_id=4, type="Phone", name="+91-99887-76655")
    db_session.add(ent_c4)
    db_session.commit()

    # Create a link between Case 1 and Case 4
    link_1_4 = CrossCaseEntityLink(
        source_case_id=1,
        target_case_id=4,
        entity_type="phone",
        match_type="exact_identifier",
        match_value="+919988776655",
        similarity_score=1.0,
        status="pending_review",
        confidence_reason="Shared mobile number"
    )
    db_session.add(link_1_4)
    db_session.commit()

    # 1. Analyst queries Case 1: Can see Case 2 links, but Case 4 MUST NOT appear
    analyst_summary = get_connected_cases_summary(case_id=1, user=analyst, db=db_session)
    linked_ids = {c["linked_case_id"] for c in analyst_summary["connected_cases"]}
    assert 4 not in linked_ids  # STRICT RBAC: Link to Case 4 is invisible because analyst cannot open Case 4!

    # 2. Analyst attempts to review link between Case 1 and Case 4: MUST FAIL with PermissionError
    with pytest.raises(PermissionError) as exc_info:
        confirm_or_reject_entity_link(
            link_id=link_1_4.id,
            status="confirmed",
            user=analyst,
            notes="Investigator confirmed",
            db=db_session
        )
    assert "Access denied: You must have authorization to access both cases" in str(exc_info.value)

    # 3. Reviewer (has access to neither) cannot even view summary for Case 1
    with pytest.raises(PermissionError):
        get_connected_cases_summary(case_id=1, user=reviewer, db=db_session)

