import sys, os
from database import SessionLocal
from models import Case, Hypothesis
from app import execute_scoring_run

def recompute_all():
    db = SessionLocal()
    try:
        cases = db.query(Case).all()
        print(f"Found {len(cases)} cases in DB.")
        for c in cases:
            hyps = db.query(Hypothesis).filter(Hypothesis.case_id == c.id).all()
            if hyps:
                print(f"\nRecalculating 3-layer scoring for Case #{c.id}: '{c.title}' ({len(hyps)} hypotheses)...")
                execute_scoring_run(c.id, db)
                db.commit()
                # Verify
                updated_hyps = db.query(Hypothesis).filter(Hypothesis.case_id == c.id).all()
                for uh in updated_hyps:
                    print(f"  H#{uh.id}: '{uh.title[:45]}' -> Evidence: {uh.evidence_score}%, Bg: {uh.background_score}%, Combined: {uh.combined_score}%")
        print("\nAll cases recalculated successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    recompute_all()
