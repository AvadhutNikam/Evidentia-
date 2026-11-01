"""
backend/decision_quality_engine.py
==================================
Evidentia AI - Decision-Quality, Cognitive Bias & Devil's Advocate Engine.
Implements:
  1. Devil's-Advocate View: Assembles the strongest counter-case for the runner-up
     hypothesis from the same evidence, conducts suppression stress-testing, and
     synthesizes defense challenge briefs.
  2. Two-Analyst Sign-Off Workflow: Maker-Checker (four-eyes) validation for key
     classifications and final legal reports, enforcing checker != maker.
  3. Cognitive & Evidentiary Bias Alerts: Single exhibit dependency (fragility),
     untested leading alternative (tunnel vision), and source type monoculture.
  4. Plain-Language Explanations: Plain-English non-technical narrative next to each
     hypothesis score for investigating officers and judges.
"""

import json
import math
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    Case, Evidence, Hypothesis, EvidenceAssessment,
    ChargesheetDraft, DecisionSignoff, Alert, User, ScoringRun
)
from audit_engine import log_audit_event
from collaboration import publish_collaboration_event
from scoring.bayesian import calculate_three_layer_ach_scoring
from scoring.sensitivity import calculate_sensitivity_and_robustness

logger = logging.getLogger("evidentia.decision_quality")


# ==============================================================================
# 1. PLAIN-LANGUAGE EXPLANATION GENERATOR
# ==============================================================================

def generate_plain_language_explanation(
    hypothesis: Dict[str, Any],
    all_hypotheses: List[Dict[str, Any]],
    breakdowns: Dict[str, Any],
    critical_exhibits: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Synthesizes a plain-language non-technical explanation for an investigating
    officer (IO), SHO, or magistrate.
    Translates mathematical Bayesian posteriors into clear legal evidentiary terms.
    """
    hypo_id = hypothesis.get("id")
    title = hypothesis.get("title", f"Hypothesis #{hypo_id}")
    score = float(hypothesis.get("combined_score", hypothesis.get("evidence_score", hypothesis.get("support_score", 0.0))))
    is_unknown = bool(hypothesis.get("is_unknown", False))

    # Determine rank
    sorted_hyps = sorted(
        all_hypotheses,
        key=lambda h: float(h.get("combined_score", h.get("evidence_score", h.get("support_score", 0.0)))),
        reverse=True
    )
    rank = 1
    runner_up = None
    for idx, h in enumerate(sorted_hyps):
        if h.get("id") == hypo_id:
            rank = idx + 1
        elif rank == 1 and runner_up is None:
            runner_up = h

    # 1. Verdict Category
    if is_unknown:
        verdict = "Open-World / Unidentified Perpetrator"
    elif score >= 75.0:
        verdict = "Decisive Evidentiary Lead (Primary Candidate)"
    elif score >= 50.0:
        verdict = "Strong Lead with Viable Competing Scenarios"
    elif score >= 30.0:
        verdict = "Moderate Support / Contested Lead"
    elif score >= 12.0:
        verdict = "Secondary Alternative Scenario"
    else:
        verdict = "Weak / Substantially Discredited Scenario"

    # 2. Extract Plain-Language Drivers from breakdowns
    drivers: List[str] = []
    doubts: List[str] = []

    hypo_breakdown = breakdowns.get(hypo_id, [])
    if isinstance(hypo_breakdown, list):
        for row in hypo_breakdown:
            contrib = float(row.get("contribution", 0.0))
            ex_title = row.get("evidence_title") or f"Exhibit #{row.get('evidence_id')}"
            cls_label = row.get("classification_label") or row.get("classification", "")

            if contrib >= 1.5:
                drivers.append(f"Strongly supported by {ex_title}: {cls_label} (high probative weight).")
            elif contrib <= -1.5:
                doubts.append(f"Weakened by {ex_title}: {cls_label} (inconsistent with this scenario).")

    # Check critical exhibit vulnerability
    for crit in critical_exhibits:
        delta = crit.get("score_deltas", {}).get(hypo_id, 0.0)
        crit_title = crit.get("evidence_title", f"Exhibit #{crit.get('evidence_id')}")
        if delta >= 15.0:
            doubts.append(
                f"High Fragility: If {crit_title} is excluded or challenged in court, this hypothesis drops by {delta:.1f}%."
            )

    if not drivers:
        drivers.append("Evidence is currently neutral or low diagnosticity; lacks direct forensic corroboration.")
    if not doubts:
        doubts.append("No direct disconfirming forensic exhibits recorded against this scenario yet.")

    # 3. Plain Narrative Summary
    if is_unknown:
        summary = (
            "The available evidence does not conclusively point to any single named suspect. "
            "Independent forensic traces or unidentified accomplice involvement cannot be ruled out."
        )
    elif rank == 1:
        if runner_up:
            r_score = float(runner_up.get("combined_score", runner_up.get("evidence_score", 0.0)))
            r_title = runner_up.get("title", f"Hypothesis #{runner_up.get('id')}")
            margin = score - r_score
            summary = (
                f"'{title}' is the leading scenario with {score:.1f}% probability, leading over '{r_title}' ({r_score:.1f}%) "
                f"by a margin of {margin:.1f}%. The case against this suspect relies substantially on {drivers[0] if drivers else 'corroborating exhibits'}. "
                f"{'Caution: The lead margin is narrow; further independent testing is advised.' if margin < 15.0 else 'The evidentiary lead is robust.'}"
            )
        else:
            summary = f"'{title}' leads with {score:.1f}% probability based on accumulated forensic and testimonial exhibits."
    else:
        top_h = sorted_hyps[0]
        top_score = float(top_h.get("combined_score", top_h.get("evidence_score", 0.0)))
        summary = (
            f"'{title}' holds {score:.1f}% probability (Rank #{rank}). It remains a secondary alternative compared to the leading "
            f"scenario ('{top_h.get('title')}', {top_score:.1f}%). {doubts[0] if doubts else ''}"
        )

    # 4. Recommended Action for IO
    if rank == 1 and score < 60.0:
        recommended_action = "Seek independent non-testimonial corroboration (DNA, CDR cell tower, or CCTV) to widen separation from runner-up."
    elif rank == 1 and doubts:
        recommended_action = f"Verify chain-of-custody and Sec 65B certification for primary exhibits to withstand defense suppression motions."
    elif rank == 2 and score >= 20.0:
        recommended_action = "Conduct targeted inquiry into this runner-up hypothesis to prevent defense alibi or third-party culpability defenses."
    else:
        recommended_action = "Maintain evidence record; re-evaluate if new forensic reports arrive."

    return {
        "hypothesis_id": hypo_id,
        "rank": rank,
        "score_pct": round(score, 1),
        "verdict": verdict,
        "summary": summary,
        "primary_drivers": drivers[:3],
        "vulnerabilities_and_doubts": doubts[:3],
        "recommended_action": recommended_action
    }


# ==============================================================================
# 2. DEVIL'S-ADVOCATE VIEW: COUNTER-CASE DOSSIER BUILDER
# ==============================================================================

def build_devils_advocate_dossier(
    case_id: int,
    db: Session,
    target_hypothesis_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Assembles the strongest counter-case for the second-ranked hypothesis (or specified
    alternative) from the exact same evidence dossier.
    Conducts suppression stress-testing and synthesizes a structured defense challenge brief.
    """
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    if len(hypotheses) < 2:
        return {
            "success": False,
            "message": "At least two hypotheses are required to construct a Devil's Advocate counter-case.",
            "leading_hypothesis": None,
            "counter_hypothesis": None
        }

    exhibits = db.query(Evidence).filter(Evidence.case_id == case_id, Evidence.is_deleted == False).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == case_id).all()

    # Sort hypotheses by current combined/support score
    sorted_hypos = sorted(
        [h for h in hypotheses if not getattr(h, "is_unknown", False)],
        key=lambda h: float(getattr(h, "combined_score", 0.0) or getattr(h, "support_score", 0.0) or 0.0),
        reverse=True
    )
    if not sorted_hypos:
        sorted_hypos = sorted(hypotheses, key=lambda h: float(h.support_score or 0.0), reverse=True)

    leading_h = sorted_hypos[0]

    # Select counter-hypothesis: specified ID or runner-up (#2)
    counter_h = None
    if target_hypothesis_id:
        counter_h = next((h for h in hypotheses if h.id == target_hypothesis_id), None)
    if not counter_h or counter_h.id == leading_h.id:
        counter_h = sorted_hypos[1] if len(sorted_hypos) > 1 else hypotheses[-1]

    lead_score = float(getattr(leading_h, "combined_score", leading_h.support_score) or 0.0)
    counter_score = float(getattr(counter_h, "combined_score", counter_h.support_score) or 0.0)
    prob_gap = round(lead_score - counter_score, 1)

    # 1. Map assessments
    assess_map = {(a.evidence_id, a.hypothesis_id): a for a in assessments}
    exhibit_map = {ev.id: ev for ev in exhibits}

    # 2. Gather Evidence Corroborating Counter-Hypothesis
    # Exhibits that either:
    #   (a) Positively support Counter-H
    #   (b) Disconfirm / contradict Leading-H
    counter_corroborating_points = []
    total_counter_positive_weight = 0.0

    for ev in exhibits:
        cell_counter = assess_map.get((ev.id, counter_h.id))
        cell_lead = assess_map.get((ev.id, leading_h.id))

        counter_cls = cell_counter.classification if cell_counter else "neutral"
        lead_cls = cell_lead.classification if cell_lead else "neutral"

        is_supporting_counter = "consistent" in counter_cls or "support" in counter_cls
        is_weakening_lead = (
            cell_lead and (bool(cell_lead.is_exculpatory) or "inconsistent" in lead_cls or "contradiction" in lead_cls)
        )

        if is_supporting_counter or is_weakening_lead:
            weight = float(cell_counter.final_contribution if cell_counter else 1.0)
            if weight <= 0:
                weight = 1.0
            total_counter_positive_weight += weight

            point = {
                "evidence_id": ev.id,
                "evidence_title": ev.file_name,
                "evidence_type": ev.evidence_type or "document",
                "counter_classification": counter_cls,
                "lead_classification": lead_cls,
                "role_in_counter_case": (
                    "Direct Support for Alternative" if is_supporting_counter and not is_weakening_lead else
                    "Exculpates Lead Suspect" if is_weakening_lead and not is_supporting_counter else
                    "Dual-Impact (Corroborates Alternative & Disconfirms Lead)"
                ),
                "probative_weight": round(weight, 2),
                "quoted_source_span": cell_counter.quoted_source_line if cell_counter else (cell_lead.quoted_source_line if cell_lead else ""),
                "counter_rationale": cell_counter.reason if cell_counter else (cell_lead.clearing_factor_note if cell_lead else ""),
                "sec_65b_present": bool(ev.sec_65b_certificate_present),
                "hash_verified": bool(ev.hash_verified)
            }
            counter_corroborating_points.append(point)

    counter_corroborating_points.sort(key=lambda p: p["probative_weight"], reverse=True)

    # 3. Analyze Vulnerabilities & Blind Spots in Leading Hypothesis
    lead_vulnerabilities = []
    for ev in exhibits:
        cell_lead = assess_map.get((ev.id, leading_h.id))
        if not cell_lead:
            continue

        lead_cls = cell_lead.classification or "neutral"
        if "consistent" in lead_cls or "support" in lead_cls:
            reasons = []
            if not ev.hash_verified:
                reasons.append("Unverified file hash (potential chain-of-custody challenge)")
            if ev.sec_65b_certificate_present is False:
                reasons.append("Missing Sec. 65B Certificate under Indian Evidence Act (admissibility bar)")
            if getattr(ev, "text_quality_status", None) == "poor_quality" or getattr(ev, "is_poor_audio", False):
                reasons.append("Degraded media/poor scan quality with unreviewed machine interpretation")
            if getattr(ev, "content_type", None) == "handwritten" and not getattr(ev, "current_version_id", None):
                reasons.append("Unreviewed handwritten panchnama/statement")
            if getattr(cell_lead, "analyst_override", False) and not getattr(cell_lead, "second_signoff_by_id", None):
                reasons.append("Sole analyst override without second reviewer sign-off")

            if reasons:
                lead_vulnerabilities.append({
                    "evidence_id": ev.id,
                    "evidence_title": ev.file_name,
                    "evidence_type": ev.evidence_type,
                    "contribution_to_lead": round(float(cell_lead.final_contribution or 1.0), 2),
                    "vulnerabilities": reasons,
                    "defense_challenge_vector": (
                        f"Defense will move to exclude {ev.file_name} under Section 65B/27 IEA; "
                        f"weakens prosecution lead by challenging foundation."
                    )
                })

    lead_vulnerabilities.sort(key=lambda v: v["contribution_to_lead"], reverse=True)

    # 4. Suppression Stress-Testing (Leave-One-Out Simulation)
    # What happens if the single strongest exhibit supporting the lead is suppressed in court?
    suppression_simulation = None
    if counter_corroborating_points or lead_vulnerabilities:
        # Find highest positive contributor to lead
        top_lead_ev = None
        max_lead_contrib = -1.0
        for ev in exhibits:
            c = assess_map.get((ev.id, leading_h.id))
            if c and float(c.final_contribution or 0.0) > max_lead_contrib:
                max_lead_contrib = float(c.final_contribution)
                top_lead_ev = ev

        if top_lead_ev:
            # Simulate scores excluding this top exhibit
            hypo_dicts = [
                {"id": h.id, "title": h.title, "description": h.description, "is_unknown": bool(getattr(h, "is_unknown", False))}
                for h in hypotheses
            ]
            exhibit_dicts = [
                {"id": ev.id, "title": ev.file_name, "evidence_type": ev.evidence_type or "document", "dependency_group": ev.dependency_group}
                for ev in exhibits
            ]
            assess_dicts = [
                {
                    "hypothesis_id": a.hypothesis_id,
                    "evidence_id": a.evidence_id,
                    "classification": a.classification,
                    "llm_confidence": a.llm_confidence or 0.85,
                    "effective_lr": getattr(a, "effective_lr", 1.0),
                    "is_exculpatory": bool(getattr(a, "is_exculpatory", False)),
                    "dependency_group": getattr(a, "dependency_group", None)
                }
                for a in assessments
            ]

            try:
                loo_res = calculate_three_layer_ach_scoring(
                    hypo_dicts, exhibit_dicts, assess_dicts,
                    excluded_exhibit_ids=[top_lead_ev.id]
                )
                loo_hyps = {h["id"]: h for h in loo_res.get("hypotheses", [])}
                new_lead_score = float(loo_hyps.get(leading_h.id, {}).get("combined_score", lead_score))
                new_counter_score = float(loo_hyps.get(counter_h.id, {}).get("combined_score", counter_score))
                new_gap = round(new_lead_score - new_counter_score, 1)
                rank_flipped = new_counter_score >= new_lead_score

                suppression_simulation = {
                    "suppressed_exhibit_id": top_lead_ev.id,
                    "suppressed_exhibit_title": top_lead_ev.file_name,
                    "suppression_legal_ground": "Judicial exclusion under Sec. 25/26/27 IEA or Sec. 65B non-compliance",
                    "original_lead_score": lead_score,
                    "new_lead_score": round(new_lead_score, 1),
                    "original_counter_score": counter_score,
                    "new_counter_score": round(new_counter_score, 1),
                    "score_drop_pct": round(lead_score - new_lead_score, 1),
                    "new_prob_gap": new_gap,
                    "rank_flipped": rank_flipped,
                    "impact_summary": (
                        f"If '{top_lead_ev.file_name}' is ruled inadmissible, the prosecution lead drops from "
                        f"{lead_score:.1f}% to {new_lead_score:.1f}%. "
                        f"{'Hypothesis #2 (' + counter_h.title + ') TAKES THE LEAD!' if rank_flipped else 'The lead margin shrinks to ' + str(new_gap) + '%.'}"
                    )
                }
            except Exception as e:
                logger.warning(f"Error in suppression stress-test: {e}")

    # 5. Required Plausibility Shift (Tipping Point)
    required_shift_points = round(prob_gap / 2.0 + 1.0, 1) if prob_gap > 0 else 0.0

    # 6. Structured Devil's Advocate Legal Challenge Brief
    legal_challenge_brief = {
        "executive_challenge": (
            f"The conclusion that '{leading_h.title}' is the sole perpetrator ({lead_score:.1f}%) rests upon "
            f"evidentiary assumptions that the defense will systematically challenge. '{counter_h.title}' "
            f"({counter_score:.1f}%) cannot be ruled out beyond reasonable doubt on the current record."
        ),
        "counter_case_narrative": (
            f"Under the alternative scenario ('{counter_h.title}'), the sequence of events is corroborated by "
            f"{len(counter_corroborating_points)} substantive points in the existing case file. Specifically, "
            f"{counter_corroborating_points[0]['counter_rationale'] if counter_corroborating_points else 'available circumstantial records'} "
            f"provides an equally plausible hypothesis that remains unrefuted by physical forensics."
        ),
        "defense_cross_examination_angles": [
            f"Highlight lack of independent corroboration for Exhibit #{v['evidence_id']} ({v['evidence_title']}) during cross-examination."
            for v in lead_vulnerabilities[:2]
        ] + [
            f"Demonstrate to the court that cell tower overlap encompasses multi-kilometer radius and fails to prove individual physical presence.",
            f"Argue that investigative team prematurely dismissed '{counter_h.title}' without conducting elimination testing."
        ][:3],
        "stress_test_recommendations": [
            f"Obtain independent forensic verification or CDR co-location to corroborate lead without relying on single confession/witness.",
            f"Issue formal investigative task to establish concrete alibi verification or elimination test for '{counter_h.title}'.",
            f"Secure certified Section 65B Indian Evidence Act certificate for electronic logs to prevent suppression in court."
        ]
    }

    return {
        "success": True,
        "case_id": case_id,
        "leading_hypothesis": {
            "id": leading_h.id,
            "title": leading_h.title,
            "score_pct": lead_score
        },
        "counter_hypothesis": {
            "id": counter_h.id,
            "title": counter_h.title,
            "score_pct": counter_score
        },
        "prob_gap": prob_gap,
        "required_shift_to_overtake": required_shift_points,
        "counter_corroborating_points": counter_corroborating_points,
        "lead_vulnerabilities": lead_vulnerabilities,
        "suppression_simulation": suppression_simulation,
        "legal_challenge_brief": legal_challenge_brief
    }


# ==============================================================================
# 3. COGNITIVE & EVIDENTIARY BIAS ALERTS ENGINE
# ==============================================================================

def evaluate_bias_alerts(case_id: int, db: Session) -> List[Alert]:
    """
    Scans the case evidence and hypothesis scoring state for three key investigative biases:
      1. Single-Exhibit Dependency (Fragility / 'Tower of Cards' Bias)
      2. Untested Leading Alternative (Tunnel Vision / Premature Closure Bias)
      3. Single Source Type Dominance (Monoculture / Corroboration Deficit Bias)
    Deduplicates and creates/updates alerts in the alerts table.
    """
    from alerts_engine import create_or_update_alert, auto_resolve_alert

    alerts_generated: List[Alert] = []

    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    if len(hypotheses) < 2:
        return alerts_generated

    exhibits = db.query(Evidence).filter(Evidence.case_id == case_id, Evidence.is_deleted == False).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == case_id).all()

    sorted_hypos = sorted(
        [h for h in hypotheses if not getattr(h, "is_unknown", False)],
        key=lambda h: float(getattr(h, "combined_score", 0.0) or getattr(h, "support_score", 0.0) or 0.0),
        reverse=True
    )
    if not sorted_hypos:
        return alerts_generated

    lead_h = sorted_hypos[0]
    lead_score = float(getattr(lead_h, "combined_score", lead_h.support_score) or 0.0)
    runner_up_h = sorted_hypos[1] if len(sorted_hypos) > 1 else None

    assess_map = {(a.evidence_id, a.hypothesis_id): a for a in assessments}

    # --------------------------------------------------------------------------
    # BIAS 1: SINGLE-EXHIBIT DEPENDENCY (FRAGILITY BIAS)
    # --------------------------------------------------------------------------
    total_lead_positive = sum(
        max(0.0, float(assess_map[(ev.id, lead_h.id)].final_contribution or 0.0))
        for ev in exhibits if (ev.id, lead_h.id) in assess_map
    )

    fragile_exhibit = None
    for ev in exhibits:
        cell = assess_map.get((ev.id, lead_h.id))
        if not cell:
            continue
        contrib = float(cell.final_contribution or 0.0)
        share = (contrib / total_lead_positive * 100.0) if total_lead_positive > 0 else 0.0

        # Exhibit accounts for > 45% of total lead support
        if share >= 45.0 and total_lead_positive >= 2.0:
            fragile_exhibit = (ev, share, contrib)
            break

    dedup_key_fragility = f"bias_fragility_{case_id}_{lead_h.id}"
    if fragile_exhibit:
        ev, share, contrib = fragile_exhibit
        alert = create_or_update_alert(
            db=db,
            case_id=case_id,
            rule_type="bias_single_exhibit_dependency",
            severity="warning",
            title=f"Bias Alert: Fragility / Single-Exhibit Dependency ({ev.file_name})",
            message=(
                f"The leading hypothesis '{lead_h.title}' ({lead_score:.1f}%) relies heavily on a single piece of evidence: "
                f"'{ev.file_name}' accounts for {share:.1f}% of all corroborating weight. "
                f"If this exhibit is discredited, suppressed under Sec. 65B/27, or reinterpreted, the entire case against the primary suspect collapses."
            ),
            dedup_key=dedup_key_fragility,
            linked_item_type="evidence",
            linked_item_id=str(ev.id)
        )
        alerts_generated.append(alert)
    else:
        auto_resolve_alert(db, case_id, dedup_key_fragility, "Multi-exhibit corroboration established.")

    # --------------------------------------------------------------------------
    # BIAS 2: UNTESTED LEADING ALTERNATIVE (TUNNEL VISION BIAS)
    # --------------------------------------------------------------------------
    dedup_key_untested = f"bias_untested_alt_{case_id}_{runner_up_h.id if runner_up_h else 0}"
    if runner_up_h:
        runner_score = float(getattr(runner_up_h, "combined_score", runner_up_h.support_score) or 0.0)
        # Check how many exhibits have active assessments against runner_up
        assessed_count = sum(1 for ev in exhibits if (ev.id, runner_up_h.id) in assess_map)

        # If runner up has substantial probability (>= 15%) but <= 1 exhibit evaluated
        if runner_score >= 15.0 and assessed_count <= 1:
            alert = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="bias_untested_alternative",
                severity="warning",
                title=f"Bias Alert: Leading Alternative Untested ('{runner_up_h.title}')",
                message=(
                    f"Runner-up hypothesis '{runner_up_h.title}' holds {runner_score:.1f}% probability, yet only "
                    f"{assessed_count} exhibit(s) have been assessed against it. "
                    f"The investigation risks confirmation bias / tunnel vision by focusing exclusively on the primary suspect without actively seeking disconfirming evidence."
                ),
                dedup_key=dedup_key_untested,
                linked_item_type="hypothesis",
                linked_item_id=str(runner_up_h.id)
            )
            alerts_generated.append(alert)
        else:
            auto_resolve_alert(db, case_id, dedup_key_untested, "Alternative hypothesis has received sufficient testing.")

    # --------------------------------------------------------------------------
    # BIAS 3: SINGLE SOURCE TYPE DOMINANCE (MONOCULTURE BIAS)
    # --------------------------------------------------------------------------
    type_totals: Dict[str, float] = {}
    for ev in exhibits:
        cell = assess_map.get((ev.id, lead_h.id))
        if cell and float(cell.final_contribution or 0.0) > 0:
            ev_type = ev.evidence_type or "document"
            type_totals[ev_type] = type_totals.get(ev_type, 0.0) + float(cell.final_contribution)

    dominant_type = None
    if total_lead_positive >= 2.0:
        for t_name, t_val in type_totals.items():
            t_pct = (t_val / total_lead_positive) * 100.0
            if t_pct >= 65.0:
                dominant_type = (t_name, t_pct)
                break

    dedup_key_monoculture = f"bias_monoculture_{case_id}_{lead_h.id}"
    if dominant_type:
        t_name, t_pct = dominant_type
        type_labels = {
            "witness_statement": "Witness / Testimonial Statements",
            "police_report": "Police Internal Notes & Panchnamas",
            "forensic_report": "Forensic Laboratory Reports",
            "cdr_telecom": "Telecom & Cell Tower Records",
            "cctv_digital": "CCTV Footage & Digital Media",
            "financial_records": "Banking & Financial Records"
        }
        human_label = type_labels.get(t_name, t_name)

        alert = create_or_update_alert(
            db=db,
            case_id=case_id,
            rule_type="bias_source_type_dominance",
            severity="info",
            title=f"Bias Alert: Source Type Monoculture ({human_label})",
            message=(
                f"{t_pct:.1f}% of corroborating weight for '{lead_h.title}' originates from a single source type ({human_label}). "
                f"Courts require independent cross-category corroboration (e.g. combining digital/forensic with witness testimony) to sustain conviction."
            ),
            dedup_key=dedup_key_monoculture,
            linked_item_type="hypothesis",
            linked_item_id=str(lead_h.id)
        )
        alerts_generated.append(alert)
    else:
        auto_resolve_alert(db, case_id, dedup_key_monoculture, "Multi-source evidence diversity established.")

    return alerts_generated


# ==============================================================================
# 4. TWO-ANALYST SIGN-OFF WORKFLOW (FOUR-EYES PRINCIPLE)
# ==============================================================================

def request_second_signoff(
    db: Session,
    case_id: int,
    item_type: str,
    item_id: int,
    item_summary: str,
    maker_user_id: int,
    maker_name: str
) -> DecisionSignoff:
    """
    Submits an item (key classification, chargesheet, or final report) for second analyst review.
    Enforces the four-eyes principle.
    """
    # Check if existing pending signoff exists
    existing = db.query(DecisionSignoff).filter(
        DecisionSignoff.case_id == case_id,
        DecisionSignoff.item_type == item_type,
        DecisionSignoff.item_id == item_id,
        DecisionSignoff.status == "pending"
    ).first()

    if existing:
        return existing

    signoff = DecisionSignoff(
        case_id=case_id,
        item_type=item_type,
        item_id=item_id,
        item_summary=item_summary,
        maker_user_id=maker_user_id,
        maker_name=maker_name,
        status="pending",
        requested_at=datetime.now(timezone.utc)
    )
    db.add(signoff)

    # Update target model
    if item_type == "evidence_assessment":
        ea = db.query(EvidenceAssessment).filter(EvidenceAssessment.id == item_id).first()
        if ea:
            ea.second_signoff_status = "pending_signoff"
            ea.is_key_classification = True
    elif item_type == "chargesheet_draft":
        cd = db.query(ChargesheetDraft).filter(ChargesheetDraft.id == item_id).first()
        if cd:
            cd.second_signoff_status = "pending_signoff"

    db.commit()
    db.refresh(signoff)

    # Log to Merkle audit chain
    try:
        log_audit_event(
            db=db,
            action_type="second_analyst_signoff_requested",
            target_type=item_type,
            target_id=str(item_id),
            description=f"Second analyst sign-off requested for {item_type} #{item_id}: {item_summary}",
            user_id=maker_user_id,
            user_name=maker_name,
            user_role="analyst",
            case_id=case_id,
            new_value={"signoff_id": signoff.id, "item_summary": item_summary}
        )
    except Exception as e:
        logger.warning(f"Could not log audit event: {e}")

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="signoff.requested",
        item_type="decision_signoff",
        item_id=str(signoff.id),
        user_name=maker_name,
        summary=f"Second analyst sign-off requested for {item_type} #{item_id} by {maker_name}."
    )

    return signoff


def review_second_signoff(
    db: Session,
    case_id: int,
    signoff_id: int,
    checker_user_id: int,
    checker_name: str,
    checker_role: str,
    approved: bool,
    review_notes: str
) -> Dict[str, Any]:
    """
    Processes second analyst sign-off.
    Enforces checker_user_id != maker_user_id (Four-Eyes Principle).
    """
    signoff = db.query(DecisionSignoff).filter(
        DecisionSignoff.id == signoff_id,
        DecisionSignoff.case_id == case_id
    ).first()

    if not signoff:
        raise ValueError("Sign-off request not found.")

    if signoff.status != "pending":
        raise ValueError(f"Sign-off already finalized with status: {signoff.status}")

    # FOUR-EYES ENFORCEMENT: Maker cannot be Checker
    if signoff.maker_user_id and signoff.maker_user_id == checker_user_id:
        raise ValueError("Four-Eyes Violation: Author/maker cannot sign off as the second reviewer on their own submission.")

    now = datetime.now(timezone.utc)
    signoff.checker_user_id = checker_user_id
    signoff.checker_name = checker_name
    signoff.checker_role = checker_role
    signoff.status = "approved" if approved else "rejected"
    signoff.review_notes = review_notes
    signoff.reviewed_at = now

    # Propagate to underlying item
    if signoff.item_type == "evidence_assessment":
        ea = db.query(EvidenceAssessment).filter(EvidenceAssessment.id == signoff.item_id).first()
        if ea:
            ea.second_signoff_status = "approved" if approved else "rejected"
            ea.second_signoff_by_id = checker_user_id
            ea.second_signoff_by_name = checker_name
            ea.second_signoff_at = now
            ea.second_signoff_notes = review_notes
    elif signoff.item_type == "chargesheet_draft":
        cd = db.query(ChargesheetDraft).filter(ChargesheetDraft.id == signoff.item_id).first()
        if cd:
            cd.second_signoff_status = "approved" if approved else "rejected"
            cd.second_signoff_by_id = checker_user_id
            cd.second_signoff_by_name = checker_name
            cd.second_signoff_at = now
            cd.second_signoff_notes = review_notes
            if approved:
                cd.legal_review_status = "scrutiny_cleared"

    db.commit()
    db.refresh(signoff)

    action_label = "second_analyst_signoff_approved" if approved else "second_analyst_signoff_rejected"
    try:
        log_audit_event(
            db=db,
            action_type=action_label,
            target_type=signoff.item_type,
            target_id=str(signoff.item_id),
            description=f"Sign-off for {signoff.item_type} #{signoff.item_id} {('approved' if approved else 'rejected')} by {checker_name}",
            user_id=checker_user_id,
            user_name=checker_name,
            user_role=checker_role,
            case_id=case_id,
            new_value={"signoff_id": signoff.id, "approved": approved, "review_notes": review_notes}
        )
    except Exception as e:
        logger.warning(f"Could not log audit event: {e}")

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="signoff.finalized",
        item_type="decision_signoff",
        item_id=str(signoff.id),
        user_name=checker_name,
        summary=f"Sign-off for {signoff.item_type} #{signoff.item_id} {('APPROVED' if approved else 'REJECTED')} by {checker_name}."
    )

    return {
        "success": True,
        "signoff_id": signoff.id,
        "status": signoff.status,
        "item_type": signoff.item_type,
        "item_id": signoff.item_id,
        "maker_name": signoff.maker_name,
        "checker_name": checker_name,
        "reviewed_at": now.isoformat(),
        "message": f"Sign-off {'approved' if approved else 'rejected'} successfully under four-eyes protocol."
    }
