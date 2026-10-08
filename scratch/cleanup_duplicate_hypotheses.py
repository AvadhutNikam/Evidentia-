# scratch/cleanup_duplicate_hypotheses.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import SessionLocal
from models import Case, Hypothesis, EvidenceAssessment
import app

db = SessionLocal()
try:
    for case in db.query(Case).all():
        hyps = db.query(Hypothesis).filter(Hypothesis.case_id == case.id).order_by(Hypothesis.id.asc()).all()
        # Keep distinct by prefix or top 3
        seen_prefixes = set()
        kept = []
        for h in hyps:
            prefix = h.title[:2].upper()
            if prefix in ('H1', 'H2', 'H3'):
                if prefix not in seen_prefixes:
                    seen_prefixes.add(prefix)
                    kept.append(h)
                else:
                    db.delete(h)
            elif len(kept) < 3:
                kept.append(h)
            else:
                db.delete(h)
        db.commit()
        print(f"[+] Case #{case.id} pruned to {len(kept)} hypotheses.")
        app.recalculate_case_ach(case.id, db)
finally:
    db.close()
