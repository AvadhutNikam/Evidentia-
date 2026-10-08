# backend/ach_engine.py
"""
True ACH (Analysis of Competing Hypotheses) Engine
Implements Richards J. Heuer Jr.'s methodology:
1. Diagnosticity Weighting: Evidence consistent with all hypotheses counts for little;
   evidence that separates hypotheses counts for significantly more.
2. Disconfirmation First: Hypotheses are evaluated and ranked primarily by inconsistency
   (disproving hypotheses), not confirmation bias.
3. Normalized Relative Likelihoods: Scores across all hypotheses sum to 100.0%.
4. Sensitivity Analysis: Evaluates the impact of removing individual exhibits to find
   which single piece of evidence the investigative conclusion hinges upon.
5. Full Exhibit Text: Processes complete evidentiary documents without lossy truncation.
6. Analyst Override: Preserves the AI's original classification while allowing investigators
   to adjust assessments and trigger immediate ACH recalculation.
"""

import math
from typing import List, Dict, Any, Optional, Set

# Heuer ACH Matrix Inconsistency Penalties & Consistency Weights
# Heuer Principle: Rejection of hypotheses by inconsistent data is logically superior to confirmation.
ACH_CLASSIFICATION_CONFIG = {
    "strong_contradiction": {
        "value": -2.0,
        "penalty": 2.5,   # Heavy disconfirmation penalty
        "support": 0.0,
        "label": "Strong Contradiction (--)"
    },
    "moderate_contradiction": {
        "value": -1.0,
        "penalty": 1.5,   # Substantial disconfirmation penalty
        "support": 0.0,
        "label": "Moderate Contradiction (-)"
    },
    "weak_contradiction": {
        "value": -0.4,
        "penalty": 0.6,   # Slight disconfirmation penalty
        "support": 0.0,
        "label": "Weak Contradiction"
    },
    "neutral": {
        "value": 0.0,
        "penalty": 0.0,
        "support": 0.0,
        "label": "Inconclusive / Neutral (0)"
    },
    "weak_support": {
        "value": 0.3,
        "penalty": 0.0,
        "support": 0.25,  # Marginal corroboration bonus
        "label": "Weak Support"
    },
    "moderate_support": {
        "value": 0.8,
        "penalty": 0.0,
        "support": 0.60,  # Consistent corroboration bonus
        "label": "Moderate Support (+)"
    },
    "strong_support": {
        "value": 1.5,
        "penalty": 0.0,
        "support": 1.10,  # Highly consistent corroboration bonus
        "label": "Strong Support (++)"
    }
}


def get_classification_config(classification: str) -> Dict[str, Any]:
    cls_key = (classification or "neutral").lower().strip()
    return ACH_CLASSIFICATION_CONFIG.get(cls_key, ACH_CLASSIFICATION_CONFIG["neutral"])


def calculate_evidence_diagnosticity(
    assessments_by_evidence: Dict[int, List[Any]],
    active_hypothesis_ids: Set[int]
) -> Dict[int, Dict[str, Any]]:
    """
    Computes Diagnosticity Weighting (D_i) for each evidence exhibit.
    Heuer Principle:
    Evidence is diagnostic when it influences the relative likelihood of hypotheses.
    If an item of evidence is consistent with ALL hypotheses, or neutral with ALL hypotheses,
    its diagnosticity is LOW / ZERO (it should count for little).
    If it separates hypotheses (consistent with some, inconsistent with others), its diagnosticity is HIGH.
    """
    diagnosticity_map = {}
    num_hyp = len(active_hypothesis_ids)

    for ev_id, assess_list in assessments_by_evidence.items():
        # Collect values only for currently active hypotheses
        values = []
        for a in assess_list:
            h_id = getattr(a, "hypothesis_id", None)
            if h_id in active_hypothesis_ids:
                cfg = get_classification_config(getattr(a, "classification", "neutral"))
                values.append(cfg["value"])

        if num_hyp <= 1 or len(values) <= 1:
            diagnosticity_map[ev_id] = {
                "weight": 1.0,
                "score": 1.0,
                "category": "Medium",
                "variance": 0.0
            }
            continue

        # If some hypotheses were unassessed, assume neutral (0.0)
        while len(values) < num_hyp:
            values.append(0.0)

        # Calculate standard deviation and value spread across hypotheses
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        val_range = max(values) - min(values)

        # If all hypotheses have the exact same classification (e.g. all neutral or all support)
        # val_range is 0 -> Evidence fits every hypothesis equally -> Low diagnosticity!
        if val_range < 0.1:
            weight = 0.2  # Counts for very little
            category = "Low"
        elif std_dev >= 0.9 or val_range >= 2.0:
            # High discriminative power across competing theories
            weight = round(min(2.0, 1.2 + 0.6 * std_dev), 2)
            category = "High"
        else:
            weight = round(0.5 + 0.8 * std_dev, 2)
            category = "Medium"

        diagnosticity_map[ev_id] = {
            "weight": weight,
            "score": round(std_dev, 2),
            "category": category,
            "variance": round(variance, 2),
            "range": round(val_range, 2)
        }

    return diagnosticity_map


def compute_ach_matrix(
    hypotheses: List[Any],
    assessments: List[Any],
    excluded_evidence_ids: Optional[Set[int]] = None
) -> Dict[str, Any]:
    """
    Computes a true Heuer ACH Matrix:
    1. Filters excluded exhibits (for Sensitivity Analysis).
    2. Computes Diagnosticity Weighting for each exhibit.
    3. Calculates Disconfirmation Penalty (I_j) for each hypothesis.
    4. Computes Normalized Relative Likelihoods summing to exactly 100.0%.
    """
    if not hypotheses:
        return {"hypotheses": {}, "diagnosticity": {}}

    excluded = excluded_evidence_ids or set()
    active_hyp_ids = {h.id for h in hypotheses}

    # Group assessments by evidence ID (ignoring excluded exhibits)
    assessments_by_evidence: Dict[int, List[Any]] = {}
    for a in assessments:
        ev_id = getattr(a, "evidence_id", None)
        if ev_id is not None and ev_id not in excluded:
            assessments_by_evidence.setdefault(ev_id, []).append(a)

    # 1. Diagnosticity weighting
    diagnosticity_map = calculate_evidence_diagnosticity(assessments_by_evidence, active_hyp_ids)

    # 2. Compute Disconfirmation Penalty & Support for each hypothesis
    hyp_scores = {}
    for h in hypotheses:
        h_assessments = [
            a for a in assessments
            if getattr(a, "hypothesis_id", None) == h.id and getattr(a, "evidence_id", None) not in excluded
        ]

        total_penalty = 0.0
        total_support = 0.0

        for a in h_assessments:
            ev_id = getattr(a, "evidence_id", None)
            diag_info = diagnosticity_map.get(ev_id, {"weight": 1.0})
            diag_weight = diag_info["weight"]

            conf = getattr(a, "llm_confidence", 0.9) or 0.9
            rel = getattr(a, "reliability", 1.0) or 1.0
            eff_weight = diag_weight * conf * rel

            cfg = get_classification_config(getattr(a, "classification", "neutral"))
            total_penalty += cfg["penalty"] * eff_weight
            total_support += cfg["support"] * eff_weight

        # 3. Raw Likelihood dominated by Disconfirmation
        # As total_penalty increases, raw likelihood decreases exponentially
        raw_likelihood = math.exp(-0.75 * total_penalty) * (1.0 + 0.15 * (total_support / (1.0 + total_support)))

        hyp_scores[h.id] = {
            "disconfirmation_penalty": round(total_penalty, 2),
            "support_bonus": round(total_support, 2),
            "raw_likelihood": raw_likelihood,
        }

    # 4. Normalized Scores across all hypotheses (Relative Likelihoods sum to 100%)
    total_raw = sum(info["raw_likelihood"] for info in hyp_scores.values())
    if total_raw <= 0:
        total_raw = 1.0

    normalized_results = {}
    total_percentage = 0.0
    hyp_list_sorted = sorted(hypotheses, key=lambda h: hyp_scores[h.id]["raw_likelihood"], reverse=True)

    for idx, h in enumerate(hyp_list_sorted):
        raw = hyp_scores[h.id]["raw_likelihood"]
        pct = round((raw / total_raw) * 100.0, 1)
        total_percentage += pct

        # Determine status based on relative likelihood and disconfirmation
        penalty = hyp_scores[h.id]["disconfirmation_penalty"]
        if pct >= 55.0 and penalty <= 1.5:
            status = "Proven"
        elif penalty >= 4.5 or pct <= 10.0:
            status = "Discarded"
        else:
            status = "Active"

        normalized_results[h.id] = {
            "relative_likelihood": pct,
            "support_score": pct,
            "disconfirmation_penalty": penalty,
            "support_bonus": hyp_scores[h.id]["support_bonus"],
            "status": status,
            "rank": idx + 1
        }

    # Normalize minor rounding drift so sum is exactly 100.0
    if hyp_list_sorted:
        drift = round(100.0 - sum(res["support_score"] for res in normalized_results.values()), 1)
        top_h_id = hyp_list_sorted[0].id
        normalized_results[top_h_id]["support_score"] = round(normalized_results[top_h_id]["support_score"] + drift, 1)
        normalized_results[top_h_id]["relative_likelihood"] = normalized_results[top_h_id]["support_score"]

    return {
        "hypotheses": normalized_results,
        "diagnosticity": diagnosticity_map
    }


def run_sensitivity_analysis(
    hypotheses: List[Any],
    assessments: List[Any],
    evidences: List[Any]
) -> Dict[str, Any]:
    """
    Performs Heuer ACH Sensitivity Analysis:
    Simulates the exclusion of every individual evidence exhibit one-by-one.
    Identifies:
    - Whether the #1 Top Hypothesis flips (Critical Pivot!).
    - The probability shift for each hypothesis.
    - How fragile or robust the overall investigative conclusion is.
    """
    if not hypotheses or not evidences:
        return {
            "baseline_ranking": [],
            "exhibit_impacts": [],
            "most_critical_evidence_id": None
        }

    # 1. Baseline calculation with all evidence included
    baseline_ach = compute_ach_matrix(hypotheses, assessments)
    baseline_scores = baseline_ach["hypotheses"]
    diagnosticity = baseline_ach["diagnosticity"]

    # Identify baseline top hypothesis
    sorted_baseline = sorted(hypotheses, key=lambda h: baseline_scores[h.id]["support_score"], reverse=True)
    baseline_top_hyp = sorted_baseline[0] if sorted_baseline else None
    baseline_top_title = baseline_top_hyp.title if baseline_top_hyp else "None"

    exhibit_impacts = []
    most_critical_id = None
    highest_pivot_shift = 0.0

    for ev in evidences:
        diag_info = diagnosticity.get(ev.id, {"score": 1.0, "category": "Medium"})

        # Recalculate ACH with THIS exhibit excluded
        sim_ach = compute_ach_matrix(hypotheses, assessments, excluded_evidence_ids={ev.id})
        sim_scores = sim_ach["hypotheses"]

        sorted_sim = sorted(hypotheses, key=lambda h: sim_scores[h.id]["support_score"], reverse=True)
        sim_top_hyp = sorted_sim[0] if sorted_sim else None
        sim_top_title = sim_top_hyp.title if sim_top_hyp else "None"

        is_critical_pivot = (sim_top_hyp and baseline_top_hyp and sim_top_hyp.id != baseline_top_hyp.id)

        # Compute shift on top hypothesis and overall max shift
        score_shifts = {}
        max_shift = 0.0
        for h in hypotheses:
            base_val = baseline_scores[h.id]["support_score"]
            sim_val = sim_scores[h.id]["support_score"]
            shift = round(sim_val - base_val, 1)
            score_shifts[str(h.id)] = shift
            if abs(shift) > max_shift:
                max_shift = abs(shift)

        # Categorize impact
        if is_critical_pivot:
            impact_level = "CRITICAL_PIVOT"
        elif max_shift >= 15.0:
            impact_level = "HIGH_IMPACT"
        elif max_shift >= 5.0:
            impact_level = "MODERATE_IMPACT"
        else:
            impact_level = "ROBUST_INSENSITIVE"

        if (is_critical_pivot and max_shift > highest_pivot_shift) or (not most_critical_id and max_shift > highest_pivot_shift):
            highest_pivot_shift = max_shift
            most_critical_id = ev.id

        exhibit_impacts.append({
            "evidence_id": ev.id,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "diagnosticity_score": diag_info["score"],
            "diagnosticity_category": diag_info["category"],
            "is_critical_pivot": is_critical_pivot,
            "top_hypothesis_with": baseline_top_title,
            "top_hypothesis_without": sim_top_title,
            "impact_level": impact_level,
            "score_shifts": score_shifts
        })

    # Sort exhibit impacts so CRITICAL_PIVOT and HIGH_IMPACT appear first
    priority_order = {"CRITICAL_PIVOT": 0, "HIGH_IMPACT": 1, "MODERATE_IMPACT": 2, "ROBUST_INSENSITIVE": 3}
    exhibit_impacts.sort(key=lambda item: priority_order.get(item["impact_level"], 4))

    most_critical_name = None
    if most_critical_id:
        found_ev = next((e for e in evidences if e.id == most_critical_id), None)
        if found_ev:
            most_critical_name = found_ev.file_name

    return {
        "baseline_top": baseline_top_title,
        "exhibit_impacts": exhibit_impacts,
        "most_critical_evidence_id": most_critical_id,
        "most_critical_evidence_name": most_critical_name
    }


def format_full_exhibit_for_ach_prompt(ev: Any, max_chars: int = 50000) -> str:
    """
    Formats complete exhibit text for LLM ACH prompt WITHOUT artificial 800-character caps.
    Preserves all forensic timestamps, IMEI numbers, DNA markers, statements, and panchnamas.
    """
    raw_text = (getattr(ev, "extracted_text", "") or "").strip()
    if not raw_text:
        raw_text = f"Exhibit File: {ev.file_name} ({ev.file_type}). Forensic exhibit logged on record."
    
    # Allow full text up to 50,000 characters (well within Gemini Flash Lite's 1M context)
    text_content = raw_text[:max_chars]
    
    return f"""Exhibit ID #{ev.id}: {ev.file_name} [Type: {ev.file_type}]
Full Evidentiary Text:
\"\"\"
{text_content}
\"\"\""""
