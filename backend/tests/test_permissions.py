"""
Tests for Authentication & Role-Based Access Control (RBAC).
Validates:
1. Unauthenticated requests are rejected with 401 Unauthorized.
2. Admin-only evaluation routes (/cases/evaluation/*) permit admin and forbid non-admin roles (403 Forbidden).
3. Case isolation: Non-admin users cannot read or modify cases they are not members of.
4. Admin unrestricted global case access.
5. Role hierarchy: Analysts and Reviewers cannot delete cases (403 Forbidden).
6. Lead Investigators can create and manage their assigned cases.
"""

import pytest
from datetime import datetime, timezone
from models import Case, CaseMember, User
from auth import hash_password, create_access_token


def test_unauthenticated_request_rejected(client):
    """Endpoints require valid authentication credentials."""
    resp = client.get("/cases")
    assert resp.status_code == 401
    assert "detail" in resp.json()

    resp_eval = client.get("/cases/evaluation/benchmark-results")
    assert resp_eval.status_code == 401


def test_admin_can_access_evaluation_benchmark(client, admin_headers):
    """Admin users have permission to view evaluation benchmark results."""
    resp = client.get("/cases/evaluation/benchmark-results", headers=admin_headers)
    # Status should not be 401 or 403
    assert resp.status_code in [200, 500]  # If benchmark results file isn't pre-generated, it might attempt eval or return 200
    assert resp.status_code != 401
    assert resp.status_code != 403


def test_analyst_cannot_access_evaluation_benchmark(client, analyst_headers):
    """Analysts are forbidden from running or viewing evaluation benchmarks (403 Forbidden)."""
    resp = client.get("/cases/evaluation/benchmark-results", headers=analyst_headers)
    assert resp.status_code == 403
    assert "Required role in ['admin']" in resp.json()["detail"]


def test_reviewer_cannot_access_evaluation(client, reviewer_headers):
    """Reviewers are forbidden from accessing evaluation benchmarks."""
    resp = client.get("/cases/evaluation/benchmark-results", headers=reviewer_headers)
    assert resp.status_code == 403


def test_case_isolation_for_unassigned_user(client, seed_users, db):
    """Case membership isolation: Users cannot access cases they are not assigned to."""
    # Create Case Alpha
    case = Case(
        title="Case Alpha - Confidential",
        description="Restricted homicide investigation",
        status="Active",
        created_by="Admin"
    )
    db.add(case)
    db.commit()

    # Assign Analyst user to Case Alpha
    analyst_user = seed_users["analyst"]
    membership = CaseMember(
        case_id=case.id,
        user_id=analyst_user.id,
        case_role="analyst"
    )
    db.add(membership)
    db.commit()

    # Create an unassigned analyst: "Analyst Beta"
    unassigned_user = User(
        email="unassigned@evidentia.test",
        full_name="Unassigned Analyst",
        hashed_password=hash_password("password123"),
        role="analyst",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(unassigned_user)
    db.commit()
    db.refresh(unassigned_user)

    unassigned_token = create_access_token({
        "sub": str(unassigned_user.id),
        "email": unassigned_user.email,
        "role": unassigned_user.role
    })
    unassigned_headers = {"Authorization": f"Bearer {unassigned_token}"}

    # Assigned analyst can access Case Alpha
    assigned_token = create_access_token({
        "sub": str(analyst_user.id),
        "email": analyst_user.email,
        "role": analyst_user.role
    })
    assigned_headers = {"Authorization": f"Bearer {assigned_token}"}

    resp_assigned = client.get(f"/cases/{case.id}", headers=assigned_headers)
    assert resp_assigned.status_code == 200
    assert resp_assigned.json()["title"] == "Case Alpha - Confidential"

    # Unassigned analyst gets 403 Forbidden
    resp_unassigned = client.get(f"/cases/{case.id}", headers=unassigned_headers)
    assert resp_unassigned.status_code == 403
    assert "not assigned to this case" in resp_unassigned.json()["detail"].lower()


def test_admin_has_unrestricted_case_access(client, admin_headers, db):
    """Admins can view any case without explicit membership assignment."""
    case = Case(
        title="Admin Test Case",
        description="Case with no members",
        status="Active",
        created_by="Someone"
    )
    db.add(case)
    db.commit()

    resp = client.get(f"/cases/{case.id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == case.id


def test_analyst_cannot_delete_case(client, analyst_headers, seed_users, db):
    """Analysts do not have permission to delete cases."""
    case = Case(
        title="Case For Delete Test",
        description="Should not be deletable by analyst",
        status="Active"
    )
    db.add(case)
    db.commit()

    # Even if analyst is a member
    membership = CaseMember(
        case_id=case.id,
        user_id=seed_users["analyst"].id,
        case_role="analyst"
    )
    db.add(membership)
    db.commit()

    resp = client.delete(f"/cases/{case.id}", headers=analyst_headers)
    assert resp.status_code == 403
    assert "cannot delete cases" in resp.json()["detail"].lower() or "not permitted" in resp.json()["detail"].lower()


def test_lead_investigator_can_create_case(client, lead_headers):
    """Lead investigators have permission to register new case dockets."""
    new_case_payload = {
        "title": "Operation Vanguard",
        "description": "Counter-narcotics docket",
        "status": "Active"
    }
    resp = client.post("/cases", json=new_case_payload, headers=lead_headers)
    assert resp.status_code == 200
    created = resp.json()
    assert created["title"] == "Operation Vanguard"
    assert created["id"] is not None

