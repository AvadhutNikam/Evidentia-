"""
backend/tests/test_validation_2.py
==================================
Unit and Integration Tests for Validation 2.0:
- Blind cases with hidden sealed answers.
- Multi-domain reviewer comparison (Ret. ACP, Forensic Faculty, Law Student).
- Comprehensive metrics: Accuracy, Ranking Position (MRR), Calibration (ECE), Stability.
- Frozen test set SHA-256 checksum integrity.
- Automated Regression Catcher.
- API endpoints & RBAC enforcement.
"""

import sys
import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import app
from database import get_db, SessionLocal, engine, Base
from models import User
from auth import create_access_token, hash_password

from evaluation.validation_v2_dataset import (
    SUITE_VERSION,
    SUITE_CHECKSUM_SHA256,
    FROZEN_SUITE_METADATA,
    FROZEN_BASELINE_METRICS,
    BLIND_CASES_DATA,
    get_blind_cases_for_scoring,
    unblind_ground_truth,
    compute_suite_checksum
)
from evaluation.validation_v2_engine import (
    score_blind_case,
    execute_blind_validation_run,
    run_regression_check,
    check_for_regressions,
    compute_spearman_rank_correlation
)

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "admin_val2@evidentia.test").first()
    if not user:
        user = User(
            email="admin_val2@evidentia.test",
            hashed_password=hash_password("AdminPass123!"),
            role="admin",
            full_name="Admin Val Two",
            badge_number="MH-ADM-002",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role})
    db.close()
    return token


@pytest.fixture(scope="module")
def investigator_token():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "investigator_val2@evidentia.test").first()
    if not user:
        user = User(
            email="investigator_val2@evidentia.test",
            hashed_password=hash_password("InvestigatorPass123!"),
            role="lead_investigator",
            full_name="Lead Investigator Val Two",
            badge_number="MH-INV-002",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(data={"sub": user.email, "role": user.role})
    db.close()
    return token


# ==============================================================================
# 1. BLIND DATASET & SEALED GROUND TRUTH INTEGRITY TESTS
# ==============================================================================

def test_blind_cases_answers_sealed_before_run():
    """
    Verifies that blind cases hide true hypotheses, culprit identity, and sealed solutions
    when queried for evaluation, ensuring the evaluation is never self-authored or leaked.
    """
    blind_cases = get_blind_cases_for_scoring()
    assert len(blind_cases) == 5

    for case in blind_cases:
        assert case["is_blinded"] is True
        assert "ground_truth" not in case or case["ground_truth"] == "GROUND_TRUTH_SEALED_UNTIL_RUN_COMPLETE"
        assert "_sealed_solution" not in case
        assert "ground_truth_sealed_hash" in case
        assert len(case["ground_truth_sealed_hash"]) == 64  # Valid SHA-256
        assert len(case["hypotheses"]) == 4
        assert len(case["exhibits"]) >= 5


def test_unblind_ground_truth_matches_sealed_hash():
    """
    Verifies that unblinded solutions match their sealed case records.
    """
    for case in BLIND_CASES_DATA:
        cid = case["id"]
        truth = unblind_ground_truth(cid)
        assert truth["case_id"] == cid
        assert truth["true_hypothesis_id"] == "H1"
        assert truth["expected_rank"] == 1
        assert len(truth["decisive_exhibits"]) >= 2
        assert truth["sealed_hash"] == case["ground_truth_sealed_hash"]
        assert len(truth["rationale"]) > 20
        assert len(truth["failure_note"]) > 20


# ==============================================================================
# 2. EVALUATION EXECUTION & COMPREHENSIVE METRICS TESTS
# ==============================================================================

def test_blind_validation_execution_metrics():
    """
    Executes the full blind validation run and validates:
    - 100% Top-1 Accuracy across independent cases
    - MRR == 1.000
    - Average Culprit Rank == 1.00
    - Expected Calibration Error (ECE) < 0.05
    - Stability score 100% with 0 rank flips
    - Case failure notes generated for every scenario
    """
    report = execute_blind_validation_run(num_perturbations=2, run_by="pytest_runner")

    assert report["suite_version"] == SUITE_VERSION
    assert report["total_blind_cases"] == 5

    # 1. Accuracy
    assert report["accuracy"]["top1_pct"] == 100.0
    assert report["accuracy"]["top1_count"] == "5 of 5"
    assert report["accuracy"]["top3_pct"] == 100.0

    # 2. Ranking Position
    assert report["ranking_position"]["mrr"] == 1.000
    assert report["ranking_position"]["avg_culprit_rank"] == 1.00
    assert report["ranking_position"]["median_culprit_rank"] == 1.0
    assert report["ranking_position"]["rank_distribution"]["rank_1"] == 5

    # 3. Calibration
    cal = report["calibration"]
    assert "expected_calibration_error" in cal
    assert cal["expected_calibration_error"] < 0.05
    assert "brier_score" in cal
    assert len(cal["calibration_bins"]) == 5

    # 4. Stability
    stab = report["stability"]
    assert stab["stability_score"] == 100.0
    assert stab["rank_flips_detected"] == 0
    assert stab["is_deterministic"] is True

    # 5. Failure notes
    assert len(report["failure_notes"]) == 5
    for fn in report["failure_notes"]:
        assert fn["culprit_rank"] == 1
        assert len(fn["failure_note"]) > 20
        assert len(fn["rationale"]) > 20


# ==============================================================================
# 3. MULTI-REVIEWER COMPARISON & SPEARMAN RANK CORRELATION TESTS
# ==============================================================================

def test_spearman_rank_correlation_utility():
    """
    Tests Spearman rank correlation calculation.
    """
    # Identical rankings -> rho = 1.0
    assert compute_spearman_rank_correlation([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    # Completely reversed rankings -> rho = -1.0
    assert compute_spearman_rank_correlation([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    # Minor swap -> rho > 0.7
    rho = compute_spearman_rank_correlation([1, 2, 3, 4], [1, 3, 2, 4])
    assert 0.7 <= rho < 1.0


def test_multi_reviewer_agreement_consensus():
    """
    Verifies that system rankings match all 3 domain reviewers (Ret. ACP, Forensic Faculty, Law Student)
    with positive Spearman correlation (>= 0.50) and 100% Top-1 agreement on true culprit.
    """
    report = execute_blind_validation_run(num_perturbations=1, run_by="pytest_runner")
    rev_comp = report["multi_reviewer_comparison"]

    assert rev_comp["overall_human_system_consensus_rho"] >= 0.50
    summaries = rev_comp["reviewer_summaries"]
    assert "REV-01" in summaries  # Ret. ACP Deshmukh
    assert "REV-02" in summaries  # Prof. K. Sharma
    assert "REV-03" in summaries  # Adv. Ananya Joshi

    for rid, meta in summaries.items():
        assert meta["avg_spearman_rho"] >= 0.50
        assert meta["top1_agreement_pct"] == 100.0


# ==============================================================================
# 4. FROZEN TEST SET INTEGRITY & REGRESSION CATCHER TESTS
# ==============================================================================

def test_frozen_suite_checksum_integrity():
    """
    Verifies that the dataset checksum is immutable and matches SUITE_CHECKSUM_SHA256.
    """
    current_hash = compute_suite_checksum()
    assert current_hash == SUITE_CHECKSUM_SHA256
    assert FROZEN_SUITE_METADATA["checksum_sha256"] == SUITE_CHECKSUM_SHA256
    assert FROZEN_SUITE_METADATA["is_frozen"] is True
    assert len(FROZEN_SUITE_METADATA["authors"]) == 5
    assert len(FROZEN_SUITE_METADATA["domain_reviewers"]) == 3


def test_regression_catcher_passes_on_baseline():
    """
    Runs the automated regression catcher against the frozen suite and asserts zero regressions.
    """
    reg_result = run_regression_check(run_by="pytest_runner")
    status = reg_result["regression_status"]

    assert status["status"] == "PASSED"
    assert status["is_regression"] is False
    assert status["regressions_count"] == 0
    assert reg_result["accuracy"]["top1_pct"] == 100.0


def test_regression_catcher_detects_deliberate_regression():
    """
    Tests that check_for_regressions correctly catches degraded metrics and raises alerts.
    """
    degraded_cases = [
        {"case_title": "Case 1", "culprit_rank": 2},
        {"case_title": "Case 2", "culprit_rank": 1}
    ]
    res = check_for_regressions(
        current_top1_pct=80.0,
        current_mrr=0.85,
        current_ece=0.10,
        current_stability_flips=1,
        case_outcomes=degraded_cases
    )

    assert res["status"] == "REGRESSION_DETECTED"
    assert res["is_regression"] is True
    assert res["regressions_count"] >= 4
    alert_types = [a["type"] for a in res["alerts"]]
    assert "ACCURACY_REGRESSION" in alert_types
    assert "RANKING_REGRESSION" in alert_types
    assert "CASE_RANK_DROP" in alert_types
    assert "CALIBRATION_DEGRADATION" in alert_types


# ==============================================================================
# 5. FASTAPI ROUTER ENDPOINTS & RBAC TESTS
# ==============================================================================

def test_validation_v2_endpoints_rbac(investigator_token, admin_token):
    """
    Verifies that non-admin roles are rejected with 403 Forbidden, and Admins can access all endpoints.
    """
    headers_investigator = {"Authorization": f"Bearer {investigator_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # 1. Non-admin should be forbidden
    res = client.get("/cases/evaluation/validation-v2/frozen-suite", headers=headers_investigator)
    assert res.status_code == 403

    # 2. Admin can access frozen suite metadata
    res = client.get("/cases/evaluation/validation-v2/frozen-suite", headers=headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["suite"]["suite_version"] == SUITE_VERSION
    assert len(data["suite"]["authors"]) == 5

    # 3. Admin can access blind cases
    res = client.get("/cases/evaluation/validation-v2/blind-cases", headers=headers_admin)
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) == 5
    assert cases[0]["is_blinded"] is True

    # 4. Admin can get results
    res = client.get("/cases/evaluation/validation-v2/results", headers=headers_admin)
    assert res.status_code == 200
    report = res.json()
    assert report["accuracy"]["top1_pct"] == 100.0

    # 5. Admin can trigger regression check
    res = client.post("/cases/evaluation/validation-v2/regression-check", json={}, headers=headers_admin)
    assert res.status_code == 200
    reg = res.json()
    assert reg["regression_status"]["status"] == "PASSED"
