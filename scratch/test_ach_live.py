# scratch/test_ach_live.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import SessionLocal
from models import Case, Hypothesis, Evidence, EvidenceAssessment
from ach_engine import compute_ach_matrix, run_sensitivity_analysis
import app

db = SessionLocal()
try:
    case = db.query(Case).first()
    if not case:
        print("[!] No case found.")
        sys.exit(0)
    print(f"[+] Testing ACH on Case #{case.id}: {case.title}")

    # Recalculate ACH
    res = app.recalculate_case_ach(case.id, db)
    print("[+] ACH Recalculation Result:")
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case.id).order_by(Hypothesis.support_score.desc()).all()
    total_pct = sum(h.support_score for h in hypotheses)
    print(f"    Total Relative Likelihood Sum: {total_pct:.1f}%")
    for h in hypotheses:
        print(f"    - {h.title[:45]} | Support: {h.support_score}% | Disconfirmation Penalty: {h.disconfirmation_penalty} | Status: {h.status}")

    # Diagnosticity
    print("[+] Evidence Diagnosticity Weights:")
    for ev_id, diag in res.get("diagnosticity", {}).items():
        ev = db.query(Evidence).filter(Evidence.id == ev_id).first()
        fname = ev.file_name if ev else f"Exhibit #{ev_id}"
        print(f"    - {fname[:40]}: Weight={diag['weight']} ({diag['category']}) | Variance={diag['variance']}")

    # Sensitivity Analysis
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == case.id).all()
    evidences = db.query(Evidence).filter(Evidence.case_id == case.id).all()
    sens = run_sensitivity_analysis(hypotheses, assessments, evidences)
    print("\n[+] Sensitivity Analysis:")
    print(f"    Baseline Top Hypothesis: {sens['baseline_top']}")
    print(f"    Most Critical Evidence: {sens['most_critical_evidence_name']} (ID: {sens['most_critical_evidence_id']})")
    for imp in sens['exhibit_impacts'][:4]:
        print(f"    - Exhibit #{imp['evidence_id']} {imp['file_name'][:30]}: Impact={imp['impact_level']} | Critical Pivot={imp['is_critical_pivot']}")
finally:
    db.close()
