# scratch/test_ach_scoring.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from ach_scoring import calculate_ach_scoring, calculate_sensitivity_and_robustness

def run_tests():
    print("=== TEST 1: Standard ACH Multi-Hypothesis ===")
    hypos = [
        {"id": 1, "title": "Suspect A Primary Actor"},
        {"id": 2, "title": "Suspect B Opportunistic Accomplice"},
        {"id": 3, "title": "Third-Party Stranger Crime"}
    ]
    exhibits = [
        {
            "id": 101, "title": "CCTV Footage Yerwada", "evidence_type": "CCTV",
            "hash_verified": True, "chain_of_custody_complete": True,
            "sec_65b_certificate_present": True, "quality_rating": 4.5
        },
        {
            "id": 102, "title": "Tower Dump CDR Logs", "evidence_type": "CDR",
            "hash_verified": True, "chain_of_custody_complete": True,
            "sec_65b_certificate_present": True, "quality_rating": 4.0
        },
        {
            "id": 103, "title": "Cab Forensic Blood Report", "evidence_type": "document",
            "chain_of_custody_complete": True, "quality_rating": 4.5
        }
    ]
    assessments = [
        # CCTV: Strongly supports H1, contradicts H3
        {"evidence_id": 101, "hypothesis_id": 1, "classification": "strong_support", "llm_confidence": 0.95},
        {"evidence_id": 101, "hypothesis_id": 2, "classification": "weak_support", "llm_confidence": 0.80},
        {"evidence_id": 101, "hypothesis_id": 3, "classification": "strong_contradiction", "llm_confidence": 0.90},

        # CDR: Strongly supports H1, contradicts H3
        {"evidence_id": 102, "hypothesis_id": 1, "classification": "strong_support", "llm_confidence": 0.90},
        {"evidence_id": 102, "hypothesis_id": 2, "classification": "moderate_contradiction", "llm_confidence": 0.85},
        {"evidence_id": 102, "hypothesis_id": 3, "classification": "strong_contradiction", "llm_confidence": 0.95},

        # Forensic: Strongly supports H1, neutral on H2, contradicts H3
        {"evidence_id": 103, "hypothesis_id": 1, "classification": "strong_support", "llm_confidence": 0.90},
        {"evidence_id": 103, "hypothesis_id": 2, "classification": "neutral", "llm_confidence": 0.70},
        {"evidence_id": 103, "hypothesis_id": 3, "classification": "strong_contradiction", "llm_confidence": 0.90},
    ]

    res = calculate_ach_scoring(hypos, exhibits, assessments)
    assert res["success"] is True
    scores = [h["support_score"] for h in res["hypotheses"]]
    print(f"Scores: {scores} -> Sum = {sum(scores)}")
    assert abs(sum(scores) - 100.0) < 0.01, "Scores must sum to 100.0"
    print(f"[OK] H1 score: {res['hypotheses'][0]['support_score']}%, Top is: {res['hypotheses'][0]['title']}")

    print("\n=== TEST 2: Edge Case 1 - Single Hypothesis ===")
    single_res = calculate_ach_scoring([hypos[0]], exhibits, assessments)
    assert single_res["success"] is True
    assert single_res["edge_case"] == "single_hypothesis"
    assert single_res["hypotheses"][0]["support_score"] == 100.0
    print(f"[OK] Single hypothesis score is 100.0%: {single_res['message']}")

    print("\n=== TEST 3: Edge Case 2 - Zero Diagnosticity ===")
    zero_diag_assessments = [
        {"evidence_id": 101, "hypothesis_id": 1, "classification": "neutral", "llm_confidence": 0.8},
        {"evidence_id": 101, "hypothesis_id": 2, "classification": "neutral", "llm_confidence": 0.8},
        {"evidence_id": 101, "hypothesis_id": 3, "classification": "neutral", "llm_confidence": 0.8},
    ]
    zero_res = calculate_ach_scoring(hypos, [exhibits[0]], zero_diag_assessments)
    assert zero_res["success"] is True
    assert zero_res["all_zero_diagnosticity"] is True
    print(f"[OK] Zero diagnosticity recognized: {zero_res['message']}")
    print(f"Equalized scores: {[h['support_score'] for h in zero_res['hypotheses']]}")

    print("\n=== TEST 4: Sensitivity & Robustness Analysis ===")
    sens = calculate_sensitivity_and_robustness(hypos, exhibits, assessments)
    assert sens["success"] is True
    print(f"[OK] Critical exhibits detected: {sens['critical_count']}")
    for exp in sens["exhibit_impacts"]:
        print(f" - {exp['evidence_title']}: Max Delta={exp['max_score_delta']}% | Impact={exp['impact_level']}")
    for h_id, r in sens["robustness_ranges"].items():
        print(f" - H{h_id} Robustness: {r['range_label']}")

    print("\nALL SCORING ENGINE TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
