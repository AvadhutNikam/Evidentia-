"""
ach_scoring.py
==============
Pure, standalone scoring engine implementing Richards J. Heuer Jr.'s
Analysis of Competing Hypotheses (ACH) methodology.

Design Principles:
1. No database or LLM calls inside this module.
2. Accepts plain dicts / primitives, returns clean structured dicts.
3. Fully deterministic, testable in isolation.
4. Handles all edge cases (single hypothesis, zero diagnosticity).
5. Comprehensive Sensitivity Analysis (Leave-One-Out and Reliability Perturbation).
"""

from typing import Dict, List, Any, Optional, Tuple
import math

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

DEFAULT_BASE_RELIABILITY = {
    "DNA": 0.95,
    "fingerprint": 0.90,
    "CCTV": 0.85,
    "CDR": 0.80,
    "document": 0.70,
    "witness": 0.55,
    "confession": 0.40,
}

CLASSIFICATION_CONFIG = {
    "strong_support": {
        "numeric": 3.0,
        "penalty": 0.0,
        "bonus": 1.0,
        "label": "Strong Support"
    },
    "moderate_support": {
        "numeric": 2.0,
        "penalty": 0.0,
        "bonus": 0.65,
        "label": "Moderate Support"
    },
    "weak_support": {
        "numeric": 1.0,
        "penalty": 0.0,
        "bonus": 0.30,
        "label": "Weak Support"
    },
    "neutral": {
        "numeric": 0.0,
        "penalty": 0.0,
        "bonus": 0.0,
        "label": "Neutral / Inconclusive"
    },
    "weak_contradiction": {
        "numeric": -1.0,
        "penalty": 0.60,
        "bonus": 0.0,
        "label": "Weak Contradiction"
    },
    "moderate_contradiction": {
        "numeric": -2.0,
        "penalty": 1.50,
        "bonus": 0.0,
        "label": "Moderate Contradiction"
    },
    "strong_contradiction": {
        "numeric": -3.0,
        "penalty": 2.50,
        "bonus": 0.0,
        "label": "Strong Contradiction"
    }
}

# ==============================================================================
# STEP 2: RELIABILITY RESOLUTION PER EXHIBIT
# ==============================================================================

def resolve_exhibit_reliability(
    exhibit: Dict[str, Any],
    custom_base_configs: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Resolve reliability starting from base value for evidence type,
    then apply legal and forensic integrity modifiers:
      - Hash verified (+0.05)
      - Chain of custody complete (+0.10 if True, -0.15 if False)
      - Sec 65B certificate present (+0.10 if True, -0.15 if missing on digital)
      - Source independent (+0.05 if True, -0.10 if False)
      - Quality rating ((rating - 3.0) * 0.05)
    Clamps between 0.10 and 0.99.
    """
    # 1. Check if analyst supplied manual override
    if exhibit.get("manual_reliability") is not None:
        val = max(0.10, min(0.99, float(exhibit["manual_reliability"])))
        return round(val, 3), {
            "evidence_type": exhibit.get("evidence_type", "document"),
            "base_value": round(val, 3),
            "manual_override": True,
            "modifiers_applied": {"manual_override": 0.0},
            "final_clamped": round(val, 3),
            "rationale": "Analyst manual reliability override"
        }

    evidence_type = str(exhibit.get("evidence_type") or "document")
    base_map = custom_base_configs or DEFAULT_BASE_RELIABILITY
    base_val = base_map.get(evidence_type, base_map.get("document", 0.70))

    modifiers = {}
    current = base_val

    # Hash verified
    if exhibit.get("hash_verified"):
        modifiers["hash_verified"] = +0.05
        current += 0.05

    # Chain of custody
    if exhibit.get("chain_of_custody_complete"):
        modifiers["chain_of_custody_complete"] = +0.08
        current += 0.08
    else:
        modifiers["chain_of_custody_incomplete"] = -0.12
        current -= 0.12

    # Section 65B Indian Evidence Act for electronic media
    is_digital = evidence_type.upper() in ["CCTV", "CDR", "DOCUMENT", "AUDIO", "VIDEO"]
    if is_digital:
        if exhibit.get("sec_65b_certificate_present"):
            modifiers["sec_65b_certified"] = +0.07
            current += 0.07
        else:
            modifiers["sec_65b_missing"] = -0.15
            current -= 0.15

    # Source independence
    if exhibit.get("source_independent", True):
        modifiers["source_independent"] = +0.05
        current += 0.05
    else:
        modifiers["source_dependent"] = -0.10
        current -= 0.10

    # Quality rating (1.0 to 5.0, default 3.0)
    quality = float(exhibit.get("quality_rating") or 3.0)
    quality_mod = (quality - 3.0) * 0.04
    if abs(quality_mod) > 0.001:
        modifiers["quality_rating"] = round(quality_mod, 3)
        current += quality_mod

    final_clamped = max(0.10, min(0.99, current))

    audit = {
        "evidence_type": evidence_type,
        "base_value": round(base_val, 3),
        "manual_override": False,
        "modifiers_applied": modifiers,
        "final_clamped": round(final_clamped, 3),
        "rationale": f"Base {evidence_type} ({base_val}) adjusted by forensic integrity checks."
    }
    return round(final_clamped, 3), audit

# ==============================================================================
# STEP 3: DIAGNOSTICITY CALCULATION
# ==============================================================================

def compute_exhibit_diagnosticity(
    exhibit_ratings: List[float]
) -> Tuple[float, str, float]:
    """
    Computes diagnosticity from the variance of ratings across hypotheses.
    Returns: (diagnosticity_factor, category, variance)
    """
    if len(exhibit_ratings) <= 1:
        return 0.0, "Zero (Single Hypothesis)", 0.0

    mean_val = sum(exhibit_ratings) / len(exhibit_ratings)
    variance = sum((r - mean_val) ** 2 for r in exhibit_ratings) / len(exhibit_ratings)

    if variance < 0.0001:
        # Perfectly uniform across all hypotheses
        return 0.20, "Low (Zero Discrimination)", round(variance, 3)

    # Scale variance into a factor from 0.20 to 2.20
    diag_factor = 0.20 + (variance * 0.50)
    diag_factor = min(2.20, max(0.20, diag_factor))

    if variance >= 2.0:
        cat = "High"
    elif variance >= 0.6:
        cat = "Medium"
    else:
        cat = "Low"

    return round(diag_factor, 3), cat, round(variance, 3)

# ==============================================================================
# STEPS 1-6: CORE ACH SCORING ENGINE
# ==============================================================================

def calculate_ach_scoring(
    hypotheses: List[Dict[str, Any]],
    exhibits: List[Dict[str, Any]],
    assessments: List[Dict[str, Any]],
    custom_base_configs: Optional[Dict[str, float]] = None,
    excluded_exhibit_ids: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Runs the complete 6-step ACH calculation.
    
    Inputs:
      - hypotheses: list of dicts with 'id', 'title'
      - exhibits: list of dicts with 'id', 'title', 'evidence_type', and integrity flags
      - assessments: list of dicts with 'hypothesis_id', 'evidence_id', 'classification', 'llm_confidence'
      - custom_base_configs: optional override dict for evidence base reliabilities
      - excluded_exhibit_ids: optional list of exhibit IDs to exclude (for sensitivity testing)
    
    Returns comprehensive breakdown dict with all intermediate and normalized numbers.
    """
    excluded_set = set(excluded_exhibit_ids or [])
    active_exhibits = [e for e in exhibits if e["id"] not in excluded_set]
    hypo_ids = [h["id"] for h in hypotheses]
    exhibit_ids = [e["id"] for e in active_exhibits]

    # Quick Edge Case: No hypotheses
    if not hypotheses:
        return {
            "success": False,
            "error": "No hypotheses provided for evaluation.",
            "hypotheses": [],
            "matrix": {},
            "exhibit_breakdown": {}
        }

    # Quick Edge Case: Only 1 hypothesis
    if len(hypotheses) == 1:
        h = hypotheses[0]
        return {
            "success": True,
            "edge_case": "single_hypothesis",
            "message": "Only one hypothesis evaluated; relative likelihood is 100.0% by definition.",
            "hypotheses": [{
                "id": h["id"],
                "title": h["title"],
                "support_score": 100.0,
                "relative_likelihood": 100.0,
                "disconfirmation_penalty": 0.0,
                "raw_support": 1.0,
                "status": "Active"
            }],
            "matrix": {},
            "exhibit_breakdown": {},
            "all_zero_diagnosticity": False
        }

    # Step 1: Build matrix mapping: (exhibit_id, hypothesis_id) -> assessment
    assessment_map = {}
    for a in assessments:
        assessment_map[(a["evidence_id"], a["hypothesis_id"])] = a

    # Step 2: Resolve Reliability per Exhibit
    exhibit_reliability = {}
    reliability_audits = {}
    for ev in active_exhibits:
        rel_val, audit = resolve_exhibit_reliability(ev, custom_base_configs)
        exhibit_reliability[ev["id"]] = rel_val
        reliability_audits[ev["id"]] = audit

    # Step 3: Compute Diagnosticity per Exhibit
    exhibit_diagnosticity = {}
    diagnosticity_audits = {}
    total_non_zero_variance = 0.0

    for ev in active_exhibits:
        ratings_for_ev = []
        for h in hypotheses:
            cell = assessment_map.get((ev["id"], h["id"]))
            cls_name = cell.get("classification") if cell else "neutral"
            cfg = CLASSIFICATION_CONFIG.get(cls_name, CLASSIFICATION_CONFIG["neutral"])
            ratings_for_ev.append(cfg["numeric"])

        diag_val, cat, var = compute_exhibit_diagnosticity(ratings_for_ev)
        exhibit_diagnosticity[ev["id"]] = diag_val
        diagnosticity_audits[ev["id"]] = {
            "diagnosticity": diag_val,
            "category": cat,
            "variance": var
        }
        total_non_zero_variance += var

    # Edge Case: Every exhibit has zero diagnosticity
    all_zero_diagnosticity = (total_non_zero_variance < 0.0001 and len(active_exhibits) > 0)

    if all_zero_diagnosticity:
        equal_pct = round(100.0 / len(hypotheses), 2)
        # Ensure exact 100.0 sum
        remainder = round(100.0 - (equal_pct * len(hypotheses)), 2)
        res_hypos = []
        for idx, h in enumerate(hypotheses):
            pct = equal_pct + (remainder if idx == 0 else 0.0)
            res_hypos.append({
                "id": h["id"],
                "title": h["title"],
                "support_score": round(pct, 1),
                "relative_likelihood": round(pct, 1),
                "disconfirmation_penalty": 0.0,
                "raw_support": 0.0,
                "status": "Active"
            })
        return {
            "success": True,
            "edge_case": "zero_diagnosticity",
            "all_zero_diagnosticity": True,
            "message": "The available evidence has zero diagnosticity and cannot separate the hypotheses yet.",
            "hypotheses": res_hypos,
            "matrix": {},
            "exhibit_breakdown": {},
            "reliability_audits": reliability_audits,
            "diagnosticity_audits": diagnosticity_audits
        }

    # Step 4: Compute Contributions & Inconsistencies
    # Per-hypothesis totals
    hypo_disconfirmation = {h["id"]: 0.0 for h in hypotheses}
    hypo_support = {h["id"]: 0.0 for h in hypotheses}

    detailed_matrix = {}  # exhibit_id -> {hypo_id -> cell_breakdown}
    exhibit_hypo_contributions = {}

    for ev in active_exhibits:
        ev_id = ev["id"]
        rel = exhibit_reliability[ev_id]
        diag = exhibit_diagnosticity[ev_id]
        detailed_matrix[ev_id] = {}

        for h in hypotheses:
            h_id = h["id"]
            cell = assessment_map.get((ev_id, h_id))
            cls_name = cell.get("classification") if cell else "neutral"
            cfg = CLASSIFICATION_CONFIG.get(cls_name, CLASSIFICATION_CONFIG["neutral"])
            confidence = float(cell.get("llm_confidence") or 0.85) if cell else 0.85

            # Contradiction / disconfirmation penalty
            cell_penalty = cfg["penalty"] * confidence * rel * diag
            # Support bonus
            cell_bonus = cfg["bonus"] * confidence * rel * diag
            # Signed Net Contribution: numeric (-3 to +3) * confidence * rel * diag
            cell_contrib = cfg["numeric"] * confidence * rel * diag

            hypo_disconfirmation[h_id] += cell_penalty
            hypo_support[h_id] += cell_bonus

            detailed_matrix[ev_id][h_id] = {
                "evidence_id": ev_id,
                "hypothesis_id": h_id,
                "classification": cls_name,
                "classification_label": cfg["label"],
                "numeric_rating": cfg["numeric"],
                "confidence": round(confidence, 2),
                "reliability": rel,
                "diagnosticity": diag,
                "cell_penalty": round(cell_penalty, 3),
                "cell_bonus": round(cell_bonus, 3),
                "contribution": round(cell_contrib, 3),
                "reason": cell.get("reason", "") if cell else "",
                "quoted_source_line": cell.get("quoted_source_line", "") if cell else "",
                "analyst_override": bool(cell.get("analyst_override", False)) if cell else False
            }

    # Step 5 & 6: Likelihood & Normalization
    raw_likelihoods = {}
    for h in hypotheses:
        h_id = h["id"]
        inconsistency = hypo_disconfirmation[h_id]
        support_val = hypo_support[h_id]

        # Heuer ACH Formula: Exponential decay on inconsistency, with marginal support
        # Heavily penalizes contradicting evidence (disconfirmation dominant)
        decay = math.exp(-0.75 * inconsistency)
        likelihood = decay * (1.0 + (0.20 * support_val))
        raw_likelihoods[h_id] = likelihood

    sum_likelihoods = sum(raw_likelihoods.values())
    if sum_likelihoods <= 0.000001:
        # Fallback if everything is severely disproven
        normalized_pcts = {h_id: 100.0 / len(hypotheses) for h_id in hypo_ids}
    else:
        normalized_pcts = {
            h_id: (raw_likelihoods[h_id] / sum_likelihoods) * 100.0
            for h_id in hypo_ids
        }

    # Ensure strictly 100.0% sum by adjusting highest score with remainder
    rounded_pcts = {h_id: round(val, 1) for h_id, val in normalized_pcts.items()}
    current_sum = round(sum(rounded_pcts.values()), 1)
    diff = round(100.0 - current_sum, 1)
    if abs(diff) > 0.001 and len(rounded_pcts) > 0:
        top_h = max(rounded_pcts.items(), key=lambda x: x[1])[0]
        rounded_pcts[top_h] = round(rounded_pcts[top_h] + diff, 1)

    # Build per-hypothesis breakdown
    result_hypotheses = []
    for h in hypotheses:
        h_id = h["id"]
        pct = rounded_pcts[h_id]
        penalty = round(hypo_disconfirmation[h_id], 2)
        sup = round(hypo_support[h_id], 2)

        status = "Active"
        if penalty >= 10.0 and pct < 2.0:
            status = "Discarded"
        elif pct >= 65.0:
            status = "Primary Candidate"

        result_hypotheses.append({
            "id": h_id,
            "title": h.get("title", ""),
            "description": h.get("description", ""),
            "support_score": pct,
            "relative_likelihood": pct,
            "disconfirmation_penalty": penalty,
            "raw_support": sup,
            "raw_likelihood": round(raw_likelihoods[h_id], 4),
            "status": status
        })

    # Sort descending by support_score
    result_hypotheses.sort(key=lambda x: x["support_score"], reverse=True)

    # Build exhibit-by-exhibit table for each hypothesis
    # Including share of total support
    hypothesis_breakdowns = {}
    for h in hypotheses:
        h_id = h["id"]
        tot_pos = sum(
            max(0.0, detailed_matrix[ev["id"]][h_id]["contribution"])
            for ev in active_exhibits
        )
        table_rows = []
        for ev in active_exhibits:
            cell = detailed_matrix[ev["id"]][h_id]
            contrib = cell["contribution"]
            share_pct = round((contrib / tot_pos * 100.0), 1) if (contrib > 0 and tot_pos > 0) else 0.0

            table_rows.append({
                "evidence_id": ev["id"],
                "evidence_title": ev.get("title") or ev.get("file_name", f"Exhibit #{ev['id']}"),
                "evidence_type": reliability_audits[ev["id"]]["evidence_type"],
                "classification": cell["classification"],
                "classification_label": cell["classification_label"],
                "confidence": cell["confidence"],
                "computed_reliability": cell["reliability"],
                "reliability_audit": reliability_audits[ev["id"]],
                "computed_diagnosticity": cell["diagnosticity"],
                "diagnosticity_audit": diagnosticity_audits[ev["id"]],
                "contribution": contrib,
                "share_of_support_pct": share_pct,
                "quoted_source_line": cell["quoted_source_line"],
                "reason": cell["reason"],
                "analyst_override": cell["analyst_override"]
            })
        # Sort exhibits: highest impact first
        table_rows.sort(key=lambda r: abs(r["contribution"]), reverse=True)
        hypothesis_breakdowns[h_id] = table_rows

    return {
        "success": True,
        "all_zero_diagnosticity": False,
        "total_relative_sum": 100.0,
        "hypotheses": result_hypotheses,
        "matrix": detailed_matrix,
        "hypothesis_breakdowns": hypothesis_breakdowns,
        "reliability_audits": reliability_audits,
        "diagnosticity_audits": diagnosticity_audits
    }

# ==============================================================================
# PART 3: SENSITIVITY & ROBUSTNESS ANALYSIS
# ==============================================================================

def calculate_sensitivity_and_robustness(
    hypotheses: List[Dict[str, Any]],
    exhibits: List[Dict[str, Any]],
    assessments: List[Dict[str, Any]],
    custom_base_configs: Optional[Dict[str, float]] = None,
    perturbation_pct: float = 0.20
) -> Dict[str, Any]:
    """
    Runs Leave-One-Out (LOO) sensitivity across exhibits and reliability perturbations.
    Returns:
      - per-exhibit impact metrics
      - critical exhibits list
      - robustness range (min% to max%) per hypothesis
    """
    # 1. Baseline Run
    baseline = calculate_ach_scoring(hypotheses, exhibits, assessments, custom_base_configs)
    if not baseline["success"] or not baseline["hypotheses"]:
        return {
            "success": False,
            "error": "Failed baseline ACH calculation",
            "exhibit_impacts": [],
            "critical_exhibits": [],
            "robustness_ranges": {}
        }

    baseline_top_id = baseline["hypotheses"][0]["id"]
    baseline_scores = {h["id"]: h["support_score"] for h in baseline["hypotheses"]}

    # Track all observed scores per hypothesis across all perturbation & LOO runs
    hypo_observed_scores = {h["id"]: [h["support_score"]] for h in baseline["hypotheses"]}

    # 2. Leave-One-Out (LOO) Per Exhibit
    exhibit_impacts = []
    critical_exhibits = []

    for ev in exhibits:
        ev_id = ev["id"]
        loo_result = calculate_ach_scoring(
            hypotheses, exhibits, assessments, custom_base_configs,
            excluded_exhibit_ids=[ev_id]
        )
        if not loo_result["success"] or not loo_result["hypotheses"]:
            continue

        loo_scores = {h["id"]: h["support_score"] for h in loo_result["hypotheses"]}
        loo_top_id = loo_result["hypotheses"][0]["id"]

        # Record scores into robustness tracking
        for h_id, s in loo_scores.items():
            if h_id in hypo_observed_scores:
                hypo_observed_scores[h_id].append(s)

        # Max delta across hypotheses
        max_delta = 0.0
        score_deltas = {}
        for h_id, b_score in baseline_scores.items():
            delta = round(abs(loo_scores.get(h_id, 0.0) - b_score), 1)
            score_deltas[h_id] = delta
            if delta > max_delta:
                max_delta = delta

        # Rank flip check
        rank_flipped = (loo_top_id != baseline_top_id)

        # Impact classification
        if rank_flipped or max_delta >= 15.0:
            impact_level = "CRITICAL_PIVOT"
        elif max_delta >= 8.0:
            impact_level = "HIGH_IMPACT"
        else:
            impact_level = "ROBUST_INSENSITIVE"

        impact_data = {
            "evidence_id": ev_id,
            "evidence_title": ev.get("title") or ev.get("file_name", f"Exhibit #{ev_id}"),
            "evidence_type": ev.get("evidence_type", "document"),
            "max_score_delta": max_delta,
            "score_deltas": score_deltas,
            "rank_flipped": rank_flipped,
            "impact_level": impact_level,
            "is_critical": (impact_level == "CRITICAL_PIVOT")
        }
        exhibit_impacts.append(impact_data)

        if impact_level == "CRITICAL_PIVOT":
            critical_exhibits.append(impact_data)

    # 3. Reliability Perturbation (+perturbation_pct and -perturbation_pct)
    # Rerun with shifted reliabilities
    for sign in [+1.0, -1.0]:
        perturbed_exhibits = []
        for ev in exhibits:
            ev_copy = dict(ev)
            base_rel, _ = resolve_exhibit_reliability(ev, custom_base_configs)
            shifted = base_rel * (1.0 + (sign * perturbation_pct))
            ev_copy["manual_reliability"] = max(0.10, min(0.99, shifted))
            perturbed_exhibits.append(ev_copy)

        pert_result = calculate_ach_scoring(
            hypotheses, perturbed_exhibits, assessments, custom_base_configs
        )
        if pert_result["success"]:
            for h in pert_result["hypotheses"]:
                if h["id"] in hypo_observed_scores:
                    hypo_observed_scores[h["id"]].append(h["support_score"])

    # 4. Compute Robustness Ranges (min% to max%)
    robustness_ranges = {}
    for h_id, scores in hypo_observed_scores.items():
        min_score = round(min(scores), 1)
        max_score = round(max(scores), 1)
        base_s = baseline_scores.get(h_id, 0.0)
        robustness_ranges[h_id] = {
            "hypothesis_id": h_id,
            "baseline_score": base_s,
            "min_score": min_score,
            "max_score": max_score,
            "range_spread": round(max_score - min_score, 1),
            "range_label": f"{base_s}% (range {min_score}–{max_score}%)"
        }

    # Sort impacts: critical and highest delta first
    exhibit_impacts.sort(key=lambda x: (x["is_critical"], x["max_score_delta"]), reverse=True)

    return {
        "success": True,
        "baseline_top_hypothesis_id": baseline_top_id,
        "exhibit_impacts": exhibit_impacts,
        "critical_exhibits": critical_exhibits,
        "critical_count": len(critical_exhibits),
        "robustness_ranges": robustness_ranges
    }
