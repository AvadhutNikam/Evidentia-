"""
backend/routers/evaluation.py
ACH Evaluation, Validation Benchmark & Counterfactual Bias Testing Router.
All endpoints require Admin role authorization.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import require_role

router = APIRouter(prefix="/cases/evaluation", tags=["Evaluation Benchmark & Validation"])
logger = logging.getLogger("evidentia.evaluation")


@router.get("/benchmark-results")
def get_evaluation_benchmark_results(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the comprehensive frozen benchmark results across all 20 cases,
    baselines (Keyword, Plain LLM, Old Scoring), and Full ACH Engine.
    Requires Admin authorization.
    """
    results_path = Path(__file__).resolve().parent.parent / "evaluation" / "results" / "benchmark_results.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading benchmark results: {e}")
            
    # If not yet generated, run on the fly
    try:
        from evaluation.run_eval import execute_validation_benchmark
        return execute_validation_benchmark(num_runs=1)
    except Exception as e:
        logger.error(f"Failed to generate benchmark results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark results: {str(e)}")


@router.post("/run")
def trigger_evaluation_run(
    request: dict = None,
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Triggers a live multi-run execution of the forensic benchmark suite.
    Requires Admin authorization due to heavy Google GenAI computational workload.
    """
    runs = 3
    if request and "runs" in request:
        runs = max(1, min(5, int(request["runs"])))
        
    try:
        from evaluation.run_eval import execute_validation_benchmark
        return execute_validation_benchmark(num_runs=runs)
    except Exception as e:
        logger.error(f"Failed to execute benchmark run: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")


@router.get("/dataset")
def get_evaluation_dataset_index(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the list of 20 benchmark cases and their ground-truth metadata.
    Requires Admin authorization.
    """
    from evaluation.benchmark_dataset import BENCHMARK_CASES
    return [{
        "id": c["id"],
        "title": c["title"],
        "split": c["split"],
        "category": c["category"],
        "is_contested": c.get("is_contested", False),
        "citation": c["citation"],
        "ground_truth_hypothesis": c["ground_truth"]["hypothesis_id"],
        "culprit_summary": c["ground_truth"]["culprit_summary"],
        "exhibits_count": len(c.get("exhibits", [])),
        "hypotheses_count": len(c.get("hypotheses", []))
    } for c in BENCHMARK_CASES]


@router.get("/bias-test-results")
def get_bias_test_results(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the counterfactual demographic matched-pair testing results and
    history-based disadvantage evaluations for innocent suspects.
    Requires Admin authorization.
    """
    results_path = Path(__file__).resolve().parent.parent / "evaluation" / "results" / "benchmark_results.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "demographic_bias": data.get("demographic_bias_analysis"),
                    "innocent_prior_disadvantage": data.get("innocent_prior_disadvantage_analysis"),
                    "prior_contribution": data.get("prior_contribution_analysis")
                }
        except Exception as e:
            logger.error(f"Error reading bias test results: {e}")
            
    from evaluation.benchmark_dataset import BENCHMARK_CASES
    from evaluation.evaluator import (
        infer_case_assessments,
        run_variant_evidence_plus_bg_with_history,
        run_variant_evidence_plus_bg_no_history
    )
    from evaluation.bias_tests import (
        run_demographic_bias_suite,
        run_innocent_prior_disadvantage_test
    )
    
    demog = run_demographic_bias_suite(BENCHMARK_CASES, run_variant_evidence_plus_bg_with_history, infer_case_assessments)
    innocent = run_innocent_prior_disadvantage_test(
        BENCHMARK_CASES,
        run_variant_evidence_plus_bg_with_history,
        run_variant_evidence_plus_bg_no_history,
        infer_case_assessments
    )
    return {
        "demographic_bias": demog,
        "innocent_prior_disadvantage": innocent,
        "prior_contribution": None
    }


@router.post("/run-bias-tests")
def trigger_bias_tests_run(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Triggers on-demand live execution of the counterfactual matched-pair demographic
    bias suite and innocent suspect prior disadvantage verification.
    Requires Admin authorization.
    """
    try:
        from evaluation.benchmark_dataset import BENCHMARK_CASES
        from evaluation.evaluator import (
            infer_case_assessments,
            run_variant_evidence_plus_bg_with_history,
            run_variant_evidence_plus_bg_no_history
        )
        from evaluation.bias_tests import (
            run_demographic_bias_suite,
            run_innocent_prior_disadvantage_test
        )
        
        demog = run_demographic_bias_suite(BENCHMARK_CASES, run_variant_evidence_plus_bg_with_history, infer_case_assessments)
        innocent = run_innocent_prior_disadvantage_test(
            BENCHMARK_CASES,
            run_variant_evidence_plus_bg_with_history,
            run_variant_evidence_plus_bg_no_history,
            infer_case_assessments
        )
        return {
            "success": True,
            "demographic_bias": demog,
            "innocent_prior_disadvantage": innocent
        }
    except Exception as e:
        logger.error(f"Error running bias tests: {e}")
        raise HTTPException(status_code=500, detail=f"Bias tests execution failed: {str(e)}")


# ==============================================================================
# VALIDATION 2.0: BLIND INDEPENDENT BENCHMARK & REGRESSION CATCHER ENDPOINTS
# ==============================================================================

@router.get("/validation-v2/results")
def get_validation_v2_results(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the latest Validation 2.0 benchmark report:
    - 5 blind cases authored by external domain authorities (answers unblinded after run).
    - Top-1/Top-3 Accuracy, MRR, Calibration ECE, Perturbation Stability.
    - Multi-domain reviewer comparison against Ret. ACP Deshmukh, Prof. Sharma, and Adv. Joshi.
    - Qualitative failure notes & frozen baseline regression status.
    Requires Admin authorization.
    """
    results_path = Path(__file__).resolve().parent.parent / "evaluation" / "results" / "validation_v2_results.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Validation 2.0 results from cache: {e}")

    try:
        from evaluation.validation_v2_engine import execute_blind_validation_run
        return execute_blind_validation_run(num_perturbations=3, run_by=current_user.email or current_user.username)
    except Exception as e:
        logger.error(f"Failed to generate Validation 2.0 results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute Validation 2.0: {str(e)}")


@router.post("/validation-v2/run")
def trigger_validation_v2_run(
    request: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Triggers an on-demand multi-perturbation execution of the Validation 2.0 suite.
    Runs blind scoring, unblinds ground truth, calculates calibration & stability,
    compares with domain reviewers, and records the run in the database audit log.
    Requires Admin authorization.
    """
    perturbations = 3
    custom_configs = None
    if request:
        if "runs" in request:
            perturbations = max(1, min(10, int(request["runs"])))
        if "custom_base_configs" in request:
            custom_configs = request["custom_base_configs"]

    try:
        from evaluation.validation_v2_engine import execute_blind_validation_run
        report = execute_blind_validation_run(
            num_perturbations=perturbations,
            custom_base_configs=custom_configs,
            run_by=current_user.email or current_user.username
        )

        # Audit persist to database
        try:
            from models import ValidationRunRecord
            run_rec = ValidationRunRecord(
                suite_version=report["suite_version"],
                run_by=current_user.email or current_user.username,
                run_type="blind_evaluation",
                top1_accuracy=report["accuracy"]["top1_pct"],
                top3_accuracy=report["accuracy"]["top3_pct"],
                mrr=report["ranking_position"]["mrr"],
                avg_culprit_rank=report["ranking_position"]["avg_culprit_rank"],
                calibration_ece=report["calibration"]["expected_calibration_error"],
                brier_score=report["calibration"]["brier_score"],
                stability_score=report["stability"]["stability_score"],
                is_regression=report["regression_status"]["is_regression"],
                regression_details=json.dumps(report["regression_status"]),
                case_results=json.dumps(report["cases"]),
                reviewer_comparison=json.dumps(report["multi_reviewer_comparison"]),
                failure_notes=json.dumps(report["failure_notes"])
            )
            db.add(run_rec)
            db.commit()
        except Exception as dbe:
            logger.warning(f"Could not persist ValidationRunRecord to DB: {dbe}")
            db.rollback()

        return report
    except Exception as e:
        logger.error(f"Error executing Validation 2.0 run: {e}")
        raise HTTPException(status_code=500, detail=f"Validation 2.0 run failed: {str(e)}")


@router.post("/validation-v2/regression-check")
def trigger_regression_check(
    request: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Executes the automated Regression Catcher against the frozen benchmark suite (v2.0-FROZEN-2026).
    Re-runs the blind test set and compares current accuracy, ranking position, and calibration
    against the immutable frozen baseline to catch regressions from scoring changes.
    Requires Admin authorization.
    """
    custom_configs = None
    if request and "custom_base_configs" in request:
        custom_configs = request["custom_base_configs"]

    try:
        from evaluation.validation_v2_engine import run_regression_check
        result = run_regression_check(
            custom_base_configs=custom_configs,
            run_by=current_user.email or current_user.username
        )

        # Persist audit record
        try:
            from models import ValidationRunRecord
            run_rec = ValidationRunRecord(
                suite_version=result["suite_version"],
                run_by=current_user.email or current_user.username,
                run_type="regression_check",
                top1_accuracy=result["accuracy"]["top1_pct"],
                top3_accuracy=result["accuracy"]["top3_pct"],
                mrr=result["ranking_position"]["mrr"],
                avg_culprit_rank=result["ranking_position"]["avg_culprit_rank"],
                calibration_ece=result["calibration"]["expected_calibration_error"],
                brier_score=result["calibration"]["brier_score"],
                stability_score=result["stability"]["stability_score"],
                is_regression=result["regression_status"]["is_regression"],
                regression_details=json.dumps(result["regression_status"]),
                case_results="[]"
            )
            db.add(run_rec)
            db.commit()
        except Exception as dbe:
            logger.warning(f"Could not persist RegressionCheckRecord to DB: {dbe}")
            db.rollback()

        return result
    except Exception as e:
        logger.error(f"Regression check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Regression check failed: {str(e)}")


@router.get("/validation-v2/frozen-suite")
def get_frozen_suite_metadata(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns frozen suite metadata including version, immutable SHA-256 fingerprint,
    independent external author credentials, and domain reviewer profiles.
    Requires Admin authorization.
    """
    from evaluation.validation_v2_dataset import FROZEN_SUITE_METADATA, FROZEN_BASELINE_METRICS
    return {
        "suite": FROZEN_SUITE_METADATA,
        "frozen_baseline_metrics": FROZEN_BASELINE_METRICS
    }


@router.get("/validation-v2/blind-cases")
def get_blind_cases_list(
    current_user: User = Depends(require_role(["admin"]))
):
    """
    Returns the 5 independent blind test cases with author details and domain reviewer ratings.
    Ground truth solutions remain sealed with SHA-256 cryptographic hashes.
    Requires Admin authorization.
    """
    from evaluation.validation_v2_dataset import get_blind_cases_for_scoring
    return get_blind_cases_for_scoring()


