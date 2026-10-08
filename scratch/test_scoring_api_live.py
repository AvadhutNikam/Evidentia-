# scratch/test_scoring_api_live.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import SessionLocal
from models import Case, Hypothesis, Evidence, EvidenceAssessment, ReliabilityConfig, ScoringRun
from app import execute_scoring_run

def test_live_scoring():
    db = SessionLocal()
    try:
        case = db.query(Case).first()
        if not case:
            print("[!] No case found.")
            return

        print(f"[+] Testing live scoring on Case #{case.id}: {case.title}")

        # 1. Execute Scoring Run
        res = execute_scoring_run(case.id, db, triggered_by="test_verification")
        assert res["success"] is True
        print(f"[OK] Total relative sum: {res['total_relative_sum']}%")
        assert abs(res["total_relative_sum"] - 100.0) < 0.1

        print("\n--- Hypotheses Normalized Scores & Inconsistency ---")
        for h in res["hypotheses"]:
            print(f" - {h['title'][:45]}: {h['support_score']}% (Inconsistency Penalty: {h['disconfirmation_penalty']}) [{h['status']}]")

        print("\n--- Sensitivity & Robustness Ranges ---")
        for h_id, r in res["robustness_ranges"].items():
            print(f" - H#{h_id}: {r['range_label']}")

        print(f"\n--- Critical Exhibits (Count: {len(res['critical_exhibits'])}) ---")
        for crit in res["critical_exhibits"]:
            print(f" - CRITICAL: {crit['evidence_title']} (Delta: {crit['max_score_delta']}%, Type: {crit['evidence_type']})")

        # 2. Check Breakdown for Top Hypothesis
        top_h_id = res["hypotheses"][0]["id"]
        table = res["hypothesis_breakdowns"].get(top_h_id, [])
        print(f"\n--- Breakdown Table for Top Hypothesis #{top_h_id} (Rows: {len(table)}) ---")
        for row in table[:3]:
            print(f" - Exhibit {row['evidence_id']} [{row['evidence_type']}]: {row['classification_label']} | Rel: {row['computed_reliability']} | Diag: {row['computed_diagnosticity']} | Contrib: {row['contribution']}")

        # 3. Check Reliability Configs
        configs = db.query(ReliabilityConfig).all()
        print(f"\n--- Reliability Configs ({len(configs)} types) ---")
        for cfg in configs:
            print(f" - {cfg.evidence_type}: {cfg.base_reliability} ({cfg.rationale[:60]}...)")

        # 4. Check ScoringRun record
        latest_run = db.query(ScoringRun).filter(ScoringRun.case_id == case.id).order_by(ScoringRun.id.desc()).first()
        assert latest_run is not None
        print(f"\n[OK] ScoringRun recorded in DB: Run ID #{latest_run.id} at {latest_run.run_at} (Trigger: {latest_run.triggered_by})")

        print("\n[SUCCESS] ALL LIVE SCORING API CHECKS PASSED!")

    finally:
        db.close()

if __name__ == "__main__":
    test_live_scoring()
