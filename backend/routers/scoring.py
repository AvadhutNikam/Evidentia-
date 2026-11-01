"""
backend/routers/scoring.py
Scientific ACH Scoring, Bayesian LR, Suspect Profiles & Sensitivity Router.
"""

import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("evidentia.scoring")
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Case, Evidence, Hypothesis, EvidenceAssessment,
    ReliabilityConfig, ScoringRun, LikelihoodRatioReference,
    SuspectProfileFactor, BackgroundWeightConfig, PriorRecord, User
)
from schemas import (
    ReliabilityConfigOut, LikelihoodRatioReferenceOut,
    MonteCarloScoringResponse, SuspectProfileFactorCreate
)
from auth import get_current_user, check_case_access
from scoring import (
    calculate_three_layer_ach_scoring,
    calculate_sensitivity_and_robustness,
    compute_monte_carlo_scoring_ranges,
    check_travel_feasibility,
    LIKELIHOOD_RATIO_REFERENCE_TABLE,
    CLASSIFICATION_CONFIG
)
from audit_engine import log_audit_event
from routers.common import resolve_case_id
from routers.cases import ensure_unknown_hypothesis

router = APIRouter(tags=["Scientific Scoring & Sensitivity"])


def execute_scoring_run(
    case_id: int,
    db: Session,
    custom_configs: Optional[Dict[str, float]] = None,
    excluded_ids: Optional[List[int]] = None,
    triggered_by: str = "recalculate",
    scoring_method: str = "bayesian_lr",
    lr_mode: str = "typical",
    broadcast: bool = True
) -> Dict[str, Any]:
    """Central pure-python scoring executor utilizing modularized scoring package."""
    ensure_unknown_hypothesis(case_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    if not hypotheses:
        return {
            "success": False,
            "hypotheses": [],
            "matrix": {},
            "hypothesis_breakdowns": {},
            "robustness_ranges": {},
            "critical_exhibits": [],
            "message": "No hypotheses recorded for this case."
        }

    exhibits = db.query(Evidence).filter(Evidence.case_id == case_id, Evidence.is_deleted == False).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == case_id).all()

    configs_db = db.query(ReliabilityConfig).all()
    base_map = {c.evidence_type: c.base_reliability for c in configs_db}
    if custom_configs:
        base_map.update(custom_configs)

    hypo_dicts = [
        {
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "is_unknown": bool(getattr(h, "is_unknown", False)),
            "background_score": getattr(h, "background_score", None),
            "background_factors": getattr(h, "background_factors", None)
        }
        for h in hypotheses
    ]
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "evidence_type": ev.evidence_type or "document",
            "hash_verified": bool(ev.hash_verified),
            "chain_of_custody_complete": bool(ev.chain_of_custody_complete),
            "sec_65b_certificate_present": bool(ev.sec_65b_certificate_present),
            "source_independent": bool(ev.source_independent if ev.source_independent is not None else True),
            "quality_rating": float(ev.quality_rating or 3.0),
            "dependency_group": getattr(ev, "dependency_group", None)
        }
        for ev in exhibits
    ]
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "llm_confidence": a.llm_confidence or 0.85,
            "quoted_source_line": a.quoted_source_line,
            "reason": a.reason,
            "analyst_override": bool(a.analyst_override),
            "finding_category": getattr(a, "finding_category", None),
            "finding_name": getattr(a, "finding_name", None),
            "likelihood_ratio": getattr(a, "likelihood_ratio", None),
            "effective_lr": getattr(a, "effective_lr", None),
            "is_exculpatory": bool(getattr(a, "is_exculpatory", False)),
            "clearing_factor_note": getattr(a, "clearing_factor_note", None),
            "dependency_group": getattr(a, "dependency_group", None),
            "dependency_weight_multiplier": getattr(a, "dependency_weight_multiplier", 1.0)
        }
        for a in assessments
    ]

    scoring_res = calculate_three_layer_ach_scoring(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map,
        excluded_exhibit_ids=excluded_ids,
        scoring_method=scoring_method,
        lr_mode=lr_mode
    )

    sens_res = calculate_sensitivity_and_robustness(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map
    )

    # Persist updated values into DB
    hyp_map = {h_data["id"]: h_data for h_data in scoring_res.get("hypotheses", [])}
    for h in hypotheses:
        if h.id in hyp_map:
            h_data = hyp_map[h.id]
            ev_val = float(h_data.get("evidence_score", h_data.get("support_score", 0.0)))
            bg_val = float(h_data.get("background_score", 0.0))
            comb_val = float(h_data.get("combined_score", ev_val))
            h.evidence_score = ev_val
            h.background_score = bg_val
            h.combined_score = comb_val
            h.support_score = comb_val
            h.disconfirmation_penalty = h_data.get("disconfirmation_penalty", 0.0)
            h.status = h_data.get("status", "Active")
            h.bayesian_lr_score = float(h_data.get("bayesian_lr_score", comb_val))
            h.bayesian_evidence_score = float(h_data.get("bayesian_evidence_score", ev_val))
            h.classic_ach_score = float(h_data.get("classic_ach_score", comb_val))
            h.classic_evidence_score = float(h_data.get("classic_evidence_score", ev_val))
            h.cumulative_lr = float(h_data.get("cumulative_lr", 1.0))
            h.is_unknown = bool(h_data.get("is_unknown", False))
            h.lead_message = h_data.get("lead_message")

    db.commit()

    READ_ONLY_TRIGGERS = {
        "get_sensitivity", "monte_carlo_query", "plain_language_request",
        "read_only", "query", "breakdown_query", "view_only"
    }
    if broadcast and triggered_by not in READ_ONLY_TRIGGERS:
        try:
            from collaboration import publish_collaboration_event
            publish_collaboration_event(
                db=db,
                case_id=case_id,
                event_type="scores.updated",
                item_type="case_scoring",
                item_id=str(case_id),
                user_name=triggered_by or "System",
                summary=f"Case #{case_id} hypotheses Bayesian scores recalculated ({triggered_by})."
            )
        except Exception as e:
            logger.warning(f"Could not broadcast scores.updated: {e}")

    # Check alert rules: Top hypothesis changed or rank margin narrowed
    try:
        from alerts_engine import check_top_hypothesis_rule
        check_top_hypothesis_rule(case_id=case_id, db=db, triggered_by=triggered_by)
    except Exception as e:
        logger.warning(f"Could not evaluate top hypothesis alert rule: {e}")

    # Synthesize Decision Quality Plain-Language Explanations & Bias Alerts
    try:
        from decision_quality_engine import generate_plain_language_explanation, evaluate_bias_alerts
        for h_dict in scoring_res.get("hypotheses", []):
            expl = generate_plain_language_explanation(
                hypothesis=h_dict,
                all_hypotheses=scoring_res.get("hypotheses", []),
                breakdowns=scoring_res.get("hypothesis_breakdowns", {}),
                critical_exhibits=sens_res.get("critical_exhibits", [])
            )
            h_dict["plain_language_explanation"] = expl
            db_h = next((x for x in hypotheses if x.id == h_dict["id"]), None)
            if db_h:
                db_h.plain_language_summary = expl.get("summary")
                db_h.plain_language_verdict = expl.get("verdict")
                db_h.plain_language_drivers = json.dumps(expl.get("primary_drivers", []))
                db_h.plain_language_doubts = json.dumps(expl.get("vulnerabilities_and_doubts", []))
        db.commit()

        evaluate_bias_alerts(case_id=case_id, db=db)
    except Exception as e:
        logger.warning(f"Could not compute plain-language explanations or bias alerts: {e}")

    return {
        "success": scoring_res.get("success", True),
        "total_relative_sum": scoring_res.get("total_relative_sum", 100.0),
        "scoring_method": scoring_res.get("scoring_method", scoring_method),
        "lr_mode": scoring_res.get("lr_mode", lr_mode),
        "hypotheses": scoring_res.get("hypotheses", []),
        "matrix": scoring_res.get("matrix", {}),
        "hypothesis_breakdowns": scoring_res.get("hypothesis_breakdowns", {}),
        "reliability_audits": scoring_res.get("reliability_audits", {}),
        "diagnosticity_audits": scoring_res.get("diagnosticity_audits", {}),
        "robustness_ranges": sens_res.get("robustness_ranges", {}),
        "critical_exhibits": sens_res.get("critical_exhibits", [])
    }


@router.post("/cases/{case_id}/scoring/recalculate")
@router.post("/cases/{case_id}/ach-score/recalculate")
def recalculate_scoring_endpoint(
    case_id: str,
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pure-python instant re-scoring of hypotheses without external LLM latency."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    p = payload or {}
    custom_cfg = p.get("custom_configs")
    excluded = p.get("excluded_evidence_ids")
    scoring_method = p.get("scoring_method", "bayesian_lr")
    lr_mode = p.get("lr_mode", "typical")
    
    return execute_scoring_run(
        real_case_id, db,
        custom_configs=custom_cfg,
        excluded_ids=excluded,
        triggered_by="recalculate_endpoint",
        scoring_method=scoring_method,
        lr_mode=lr_mode
    )


@router.get("/cases/{case_id}/bayesian-lr/reference-table", response_model=List[LikelihoodRatioReferenceOut])
def get_likelihood_ratio_reference_table_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the Forensic Likelihood Ratio Reference Table entries."""
    real_case_id = resolve_case_id(case_id, db)
    entries = db.query(LikelihoodRatioReference).order_by(
        LikelihoodRatioReference.evidence_type.asc(),
        LikelihoodRatioReference.typical_lr.desc()
    ).all()

    if not entries:
        for cat_key, spec in LIKELIHOOD_RATIO_REFERENCE_TABLE.items():
            db_ref = LikelihoodRatioReference(
                category_key=cat_key,
                evidence_type=spec.get("evidence_type", "document"),
                finding_name=spec.get("finding_name", cat_key),
                support_direction=spec.get("support_direction", "neutral"),
                min_lr=float(spec.get("min_lr", 1.0)),
                max_lr=float(spec.get("max_lr", 1.0)),
                typical_lr=float(spec.get("typical_lr", 1.0)),
                source_citation=spec.get("source_citation", "Forensic Guidelines"),
                forensic_error_rate=spec.get("forensic_error_rate", "N/A"),
                notes=spec.get("notes", "")
            )
            db.add(db_ref)
        db.commit()
        entries = db.query(LikelihoodRatioReference).all()

    return entries


@router.get("/cases/{case_id}/scoring/sensitivity")
def get_scoring_sensitivity(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns sensitivity analysis and critical pivot exhibits."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    res = execute_scoring_run(real_case_id, db, triggered_by="get_sensitivity", broadcast=False)
    return {
        "case_id": real_case_id,
        "robustness_ranges": res.get("robustness_ranges", {}),
        "critical_exhibits": res.get("critical_exhibits", [])
    }

