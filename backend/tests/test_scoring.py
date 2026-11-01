"""
Tests for Evidentia-AI Scoring Engine.
Validates the 4 fundamental scientific guarantees:
1. Percentages sum strictly to 100.0%.
2. Irrelevant evidence changes nothing.
3. Exculpatory evidence lowers suspect posterior probability.
4. Order of exhibits does not matter (permutation invariance).
"""

import pytest
import math
from scoring.bayesian import compute_bayesian_lr_scoring, combine_scores_bayesian
from scoring.evidence_scoring import compute_evidence_scores


@pytest.fixture
def base_case_setup():
    hypotheses = [
        {"id": 1, "title": "Suspect A", "description": "Primary suspect"},
        {"id": 2, "title": "Suspect B", "description": "Secondary suspect"},
        {"id": 3, "title": "Unknown Perpetrator", "description": "Alternative actor", "is_unknown": True}
    ]
    exhibits = [
        {"id": 101, "title": "Fingerprint Partial Match", "evidence_type": "forensic", "confidence_score": 0.85},
        {"id": 102, "title": "CCTV Surveillance Match", "evidence_type": "digital", "confidence_score": 0.80}
    ]
    assessments = [
        {"evidence_id": 101, "hypothesis_id": 1, "classification": "supports", "finding_category": "fingerprint_partial_match", "confidence": 0.85},
        {"evidence_id": 101, "hypothesis_id": 2, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.85},
        {"evidence_id": 102, "hypothesis_id": 1, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.80},
        {"evidence_id": 102, "hypothesis_id": 2, "classification": "supports", "finding_category": "cctv_hd_facial_match", "confidence": 0.80}
    ]
    return hypotheses, exhibits, assessments


def test_percentages_sum_to_100(base_case_setup):
    """Scientific Guarantee 1: Combined posterior probabilities sum strictly to 100.0%."""
    hypotheses, exhibits, assessments = base_case_setup
    result = compute_bayesian_lr_scoring(hypotheses, exhibits, assessments)

    assert result["success"] is True
    scores = [h["posterior_score"] for h in result["hypotheses"]]
    total_posterior = sum(scores)

    # Must equal 100.0% within floating point tolerance
    assert total_posterior == pytest.approx(100.0, abs=0.05)

    # Test edge case: single hypothesis
    single_hypo = [hypotheses[0]]
    single_res = compute_bayesian_lr_scoring(single_hypo, exhibits, assessments)
    assert single_res["success"] is True
    assert single_res["hypotheses"][0]["posterior_score"] == 100.0

    # Test combine_scores_bayesian
    combined = combine_scores_bayesian(
        evidence_scores=[{"id": 1, "evidence_score": 70.0}, {"id": 2, "evidence_score": 30.0}],
        background_scores=[{"id": 1, "background_score": 50.0}, {"id": 2, "background_score": 50.0}]
    )
    assert combined["success"] is True
    comb_sum = sum(h["combined_score"] for h in combined["hypotheses"])
    assert comb_sum == pytest.approx(100.0, abs=0.05)


def test_irrelevant_evidence_changes_nothing(base_case_setup):
    """Scientific Guarantee 2: Adding neutral/irrelevant evidence leaves suspect scores unchanged."""
    hypotheses, exhibits, assessments = base_case_setup

    # Baseline scoring before adding irrelevant evidence
    base_res = compute_bayesian_lr_scoring(hypotheses, exhibits, assessments)
    base_scores = {h["id"]: h["posterior_score"] for h in base_res["hypotheses"]}

    # Add neutral / irrelevant exhibit (LR = 1.0)
    irrelevant_exhibit = {
        "id": 999,
        "title": "Irrelevant Parking Receipt",
        "evidence_type": "documentary",
        "confidence_score": 0.95
    }
    irrelevant_assessments = [
        {"evidence_id": 999, "hypothesis_id": 1, "classification": "neutral", "finding_category": "general_irrelevant_neutral", "confidence": 0.95},
        {"evidence_id": 999, "hypothesis_id": 2, "classification": "neutral", "finding_category": "general_irrelevant_neutral", "confidence": 0.95}
    ]

    updated_exhibits = exhibits + [irrelevant_exhibit]
    updated_assessments = assessments + irrelevant_assessments

    updated_res = compute_bayesian_lr_scoring(hypotheses, updated_exhibits, updated_assessments)
    updated_scores = {h["id"]: h["posterior_score"] for h in updated_res["hypotheses"]}

    # Score for each hypothesis should remain unchanged (within 0.05% rounding threshold)
    for h_id, original_score in base_scores.items():
        assert updated_scores[h_id] == pytest.approx(original_score, abs=0.05)


def test_exculpatory_evidence_lowers_suspect(base_case_setup):
    """Scientific Guarantee 3: Exculpatory evidence sharply decreases suspect posterior probability."""
    hypotheses, exhibits, assessments = base_case_setup

    # Baseline scoring
    base_res = compute_bayesian_lr_scoring(hypotheses, exhibits, assessments)
    base_scores = {h["id"]: h["posterior_score"] for h in base_res["hypotheses"]}
    initial_suspect_a = base_scores[1]

    # Add definitive exculpatory evidence clearing Suspect A (e.g. verified alibi or DNA exclusion)
    exculpatory_exhibit = {
        "id": 201,
        "title": "DNA Definitive Exclusion of Suspect A",
        "evidence_type": "forensic",
        "confidence_score": 0.99
    }
    exculpatory_assessments = [
        {"evidence_id": 201, "hypothesis_id": 1, "classification": "contradicts", "finding_category": "dna_definitive_exclusion", "confidence": 0.99},
        {"evidence_id": 201, "hypothesis_id": 2, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.90}
    ]

    new_exhibits = exhibits + [exculpatory_exhibit]
    new_assessments = assessments + exculpatory_assessments

    exculp_res = compute_bayesian_lr_scoring(hypotheses, new_exhibits, new_assessments)
    exculp_scores = {h["id"]: h["posterior_score"] for h in exculp_res["hypotheses"]}

    # Suspect A's score must decrease dramatically
    assert exculp_scores[1] < initial_suspect_a
    assert exculp_scores[1] < 10.0  # Decisive drop
    # Total must still normalize to 100%
    assert sum(exculp_scores.values()) == pytest.approx(100.0, abs=0.05)


def test_order_of_exhibits_does_not_matter(base_case_setup):
    """Scientific Guarantee 4: Permutation invariance - exhibit order does not affect posteriors."""
    hypotheses, _, _ = base_case_setup

    e1 = {"id": 101, "title": "Exhibit 1 - Fingerprint", "evidence_type": "forensic", "confidence_score": 0.85}
    e2 = {"id": 102, "title": "Exhibit 2 - CCTV", "evidence_type": "digital", "confidence_score": 0.80}
    e3 = {"id": 103, "title": "Exhibit 3 - Alibi Record", "evidence_type": "documentary", "confidence_score": 0.90}

    a1 = [
        {"evidence_id": 101, "hypothesis_id": 1, "classification": "supports", "finding_category": "fingerprint_partial_match", "confidence": 0.85},
        {"evidence_id": 101, "hypothesis_id": 2, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.85}
    ]
    a2 = [
        {"evidence_id": 102, "hypothesis_id": 1, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.80},
        {"evidence_id": 102, "hypothesis_id": 2, "classification": "supports", "finding_category": "cctv_hd_facial_match", "confidence": 0.80}
    ]
    a3 = [
        {"evidence_id": 103, "hypothesis_id": 1, "classification": "contradicts", "finding_category": "verified_alibi_timestamped", "confidence": 0.90},
        {"evidence_id": 103, "hypothesis_id": 2, "classification": "neutral", "finding_category": "neutral_inconclusive", "confidence": 0.70}
    ]
    all_assessments = a1 + a2 + a3

    # Run with original order: [E1, E2, E3]
    res_forward = compute_bayesian_lr_scoring(hypotheses, [e1, e2, e3], all_assessments)
    forward_map = {h["id"]: h["posterior_score"] for h in res_forward["hypotheses"]}

    # Run with reversed order: [E3, E2, E1]
    res_reverse = compute_bayesian_lr_scoring(hypotheses, [e3, e2, e1], all_assessments)
    reverse_map = {h["id"]: h["posterior_score"] for h in res_reverse["hypotheses"]}

    # Run with shuffled order: [E2, E1, E3]
    res_shuffled = compute_bayesian_lr_scoring(hypotheses, [e2, e1, e3], all_assessments)
    shuffled_map = {h["id"]: h["posterior_score"] for h in res_shuffled["hypotheses"]}

    # All permutations must produce identical posteriors
    assert res_forward["order_independence_verified"] is True
    assert forward_map == reverse_map
    assert forward_map == shuffled_map

