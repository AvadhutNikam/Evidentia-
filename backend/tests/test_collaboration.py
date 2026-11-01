import pytest
from datetime import datetime, timezone, timedelta
from models import Case, CaseMember, Hypothesis, PriorRecord, EditLock, CasePresence, AuditLog, CollaborationEvent
from collaboration import (
    record_presence_heartbeat,
    get_active_presence,
    sweep_expired_presence,
    acquire_edit_lock,
    release_edit_lock,
    override_edit_lock,
    publish_collaboration_event,
    get_events_after,
)


@pytest.fixture
def test_case(db, seed_users):
    c = Case(
        title="Collaboration Test Case",
        description="Testing multi-user collaboration",
        created_by="Lead Investigator",
        status="active",
        version=1
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Assign members
    for role_key in ["admin", "lead_investigator", "analyst", "reviewer"]:
        u = seed_users[role_key]
        m = CaseMember(case_id=c.id, user_id=u.id, case_role=u.role, added_by="Test Setup")
        db.add(m)
    db.commit()

    return c


@pytest.fixture
def test_hypothesis(db, test_case):
    h = Hypothesis(
        case_id=test_case.id,
        title="Primary Suspect H1",
        description="Initial hypothesis narrative",
        status="active",
        support_score=50.0,
        version=1
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@pytest.fixture
def test_prior_record(db, test_case, test_hypothesis):
    pr = PriorRecord(
        case_id=test_case.id,
        hypothesis_id=test_hypothesis.id,
        suspect_name="John Doe",
        offense_type="Theft",
        outcome="conviction",
        source_agency="Metropolitan Police Department",
        source_document="Docket #8921",
        verified_identity=True,
        identity_match_confidence=0.95,
        version=1
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


# ==============================================================================
# 1. PRESENCE TESTS
# ==============================================================================

def test_presence_heartbeat_and_active_list(client, test_case, analyst_headers, lead_headers):
    # Analyst sends heartbeat
    res1 = client.post(
        f"/cases/{test_case.id}/presence/heartbeat",
        headers=analyst_headers,
        json={"current_location": "Hypotheses Screen", "item_id": "H-1"}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["user_role"] == "analyst"
    assert data1["current_location"] == "Hypotheses Screen"

    # Lead sends heartbeat
    res2 = client.post(
        f"/cases/{test_case.id}/presence/heartbeat",
        headers=lead_headers,
        json={"current_location": "Suspect Profile", "item_id": "SP-1"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["user_role"] == "lead_investigator"

    # Query presence GET endpoint
    get_res = client.get(f"/cases/{test_case.id}/presence", headers=analyst_headers)
    assert get_res.status_code == 200
    active_users = get_res.json()
    assert len(active_users) >= 2
    assert any(u["user_role"] == "analyst" for u in active_users)
    assert any(u["user_role"] == "lead_investigator" for u in active_users)


def test_presence_sweep_expired(db, test_case, seed_users):
    u = seed_users["analyst"]
    # Insert expired presence record
    old_time = datetime.now(timezone.utc) - timedelta(seconds=60)
    p = CasePresence(
        case_id=test_case.id,
        user_id=u.id,
        user_name=u.full_name,
        user_role=u.role,
        current_location="Overview",
        last_seen_at=old_time
    )
    db.add(p)
    db.commit()

    active_before = get_active_presence(db, test_case.id, timeout_seconds=45)
    assert not any(x["user_id"] == u.id for x in active_before)

    swept = sweep_expired_presence(db, timeout_seconds=45)
    assert swept >= 1


# ==============================================================================
# 2. SOFT EDIT LOCK TESTS
# ==============================================================================

def test_soft_edit_lock_lifecycle(client, test_case, analyst_headers, lead_headers, reviewer_headers):
    item_type = "hypothesis"
    item_id = "1"

    # Reviewer cannot acquire lock (403)
    rev_res = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=reviewer_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 60}
    )
    assert rev_res.status_code == 403

    # Analyst acquires lock (200)
    acquire_res = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=analyst_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 60}
    )
    assert acquire_res.status_code == 200
    lock_data = acquire_res.json()
    assert lock_data["item_type"] == item_type
    assert lock_data["item_id"] == item_id

    # Second user (Lead) attempts to acquire same lock -> 423 Locked
    clash_res = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=lead_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 60}
    )
    assert clash_res.status_code == 423
    err_detail = clash_res.json()["detail"]
    assert err_detail["error"] == "locked"
    assert "Analyst User" in err_detail["message"]

    # Analyst renews lock -> 200
    renew_res = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=analyst_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 60}
    )
    assert renew_res.status_code == 200

    # Analyst releases lock -> 200
    rel_res = client.post(
        f"/cases/{test_case.id}/locks/release",
        headers=analyst_headers,
        json={"item_type": item_type, "item_id": item_id}
    )
    assert rel_res.status_code == 200
    assert rel_res.json()["status"] == "released"

    # Now Lead can acquire it -> 200
    lead_acq = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=lead_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 60}
    )
    assert lead_acq.status_code == 200


def test_admin_lock_override(client, db, test_case, analyst_headers, admin_headers, seed_users):
    item_type = "hypothesis"
    item_id = "2"

    # Analyst acquires lock
    acq = client.post(
        f"/cases/{test_case.id}/locks/acquire",
        headers=analyst_headers,
        json={"item_type": item_type, "item_id": item_id, "ttl_seconds": 120}
    )
    assert acq.status_code == 200

    # Non-admin / non-lead analyst tries to override -> 403
    override_fail = client.post(
        f"/cases/{test_case.id}/locks/override",
        headers=analyst_headers,
        json={"item_type": item_type, "item_id": item_id, "reason": "Unauthorized override"}
    )
    assert override_fail.status_code == 403

    # Admin overrides lock -> 200
    override_ok = client.post(
        f"/cases/{test_case.id}/locks/override",
        headers=admin_headers,
        json={"item_type": item_type, "item_id": item_id, "reason": "Urgent lead intervention"}
    )
    assert override_ok.status_code == 200
    data = override_ok.json()
    assert data["user_role"] == "admin"

    # Check that LOCK_OVERRIDE audit log was written
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action_type == "LOCK_OVERRIDE",
        AuditLog.target_id == item_id
    ).first()
    assert audit_entry is not None
    assert "Urgent lead intervention" in audit_entry.description


# ==============================================================================
# 3. OPTIMISTIC CONCURRENCY TESTS (HTTP 409 CONFLICT)
# ==============================================================================

def test_optimistic_concurrency_hypothesis_update(client, db, test_case, test_hypothesis, analyst_headers):
    # Save 1: Client submits correct version (v1) -> succeeds and bumps to v2
    update_payload = {
        "title": "Updated Title First Pass",
        "description": "Updated description",
        "status": "active",
        "version": 1
    }
    res1 = client.put(
        f"/hypotheses/{test_hypothesis.id}",
        headers=analyst_headers,
        json=update_payload
    )
    assert res1.status_code == 200
    assert res1.json()["version"] == 2

    # Save 2: Concurrent investigator submits stale version (v1 instead of v2) -> 409 Conflict
    stale_payload = {
        "title": "Stale Overwrite Attempt",
        "description": "Will be rejected",
        "status": "active",
        "version": 1
    }
    res2 = client.put(
        f"/hypotheses/{test_hypothesis.id}",
        headers=analyst_headers,
        json=stale_payload
    )
    assert res2.status_code == 409
    conflict_detail = res2.json()["detail"]
    assert conflict_detail["error"] == "conflict"
    assert conflict_detail["current_version"] == 2
    assert conflict_detail["submitted_version"] == 1
    assert conflict_detail["current_data"]["title"] == "Updated Title First Pass"

    # Verify conflict was recorded in Merkle audit log
    conflict_log = db.query(AuditLog).filter(
        AuditLog.action_type == "CONFLICT_REJECTED",
        AuditLog.target_type == "hypothesis",
        AuditLog.target_id == str(test_hypothesis.id)
    ).first()
    assert conflict_log is not None


def test_optimistic_concurrency_prior_record_update(client, test_case, test_prior_record, analyst_headers):
    # Save 1: matching version 1 -> succeeds, increments to 2
    res1 = client.put(
        f"/cases/{test_case.id}/prior-records/{test_prior_record.id}",
        headers=analyst_headers,
        json={"outcome": "acquittal", "version": 1}
    )
    assert res1.status_code == 200
    assert res1.json()["version"] == 2

    # Save 2: stale version 1 -> 409 Conflict
    res2 = client.put(
        f"/cases/{test_case.id}/prior-records/{test_prior_record.id}",
        headers=analyst_headers,
        json={"outcome": "conviction", "version": 1}
    )
    assert res2.status_code == 409
    err = res2.json()["detail"]
    assert err["current_version"] == 2
    assert err["submitted_version"] == 1


# ==============================================================================
# 4. SSE REPLAY & PRIVACY FILTERING TESTS
# ==============================================================================

def test_collaboration_event_replay_and_reviewer_privacy(client, db, test_case, analyst_headers, reviewer_headers):
    # Publish normal event
    publish_collaboration_event(
        db=db,
        case_id=test_case.id,
        event_type="item.changed",
        item_type="hypothesis",
        item_id="1",
        version=2,
        user_id=1,
        user_name="Analyst User",
        summary="Updated hypothesis title",
        payload={"title": "New Title"},
        is_restricted=False
    )

    # Publish restricted event (e.g. criminal history)
    publish_collaboration_event(
        db=db,
        case_id=test_case.id,
        event_type="item.changed",
        item_type="prior_record",
        item_id="5",
        version=2,
        user_id=1,
        user_name="Analyst User",
        summary="Updated prior record for suspect Raut",
        payload={"suspect_name": "Raut", "offense": "Homicide"},
        is_restricted=True
    )

    # Analyst retrieves history -> sees restricted payload intact
    analyst_hist = client.get(
        f"/cases/{test_case.id}/collaboration/history?after_id=0",
        headers=analyst_headers
    )
    assert analyst_hist.status_code == 200
    events_analyst = analyst_hist.json()
    restricted_for_analyst = [e for e in events_analyst if e.get("is_restricted")]
    assert len(restricted_for_analyst) == 1
    assert restricted_for_analyst[0]["payload"]["suspect_name"] == "Raut"

    # Reviewer retrieves history -> restricted event payload is redacted
    reviewer_hist = client.get(
        f"/cases/{test_case.id}/collaboration/history?after_id=0",
        headers=reviewer_headers
    )
    assert reviewer_hist.status_code == 200
    events_reviewer = reviewer_hist.json()
    restricted_for_reviewer = [e for e in events_reviewer if e.get("is_restricted")]
    assert len(restricted_for_reviewer) == 1
    assert restricted_for_reviewer[0]["summary"] == "Restricted case data updated."
    assert restricted_for_reviewer[0]["payload"] == {}
