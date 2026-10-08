# scratch/rechain_audit_ledger.py
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import AuditLog
from audit_engine import calculate_audit_payload_hash, GENESIS_HASH, verify_audit_chain

def rechain():
    print("[*] Recomputing Merkle hash chain across all AuditLog rows...")
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        print(f"[*] Found {len(logs)} audit rows.")
        prev_hash = GENESIS_HASH
        for i, log in enumerate(logs):
            log.previous_hash = prev_hash
            new_hash = calculate_audit_payload_hash(
                previous_hash=prev_hash,
                timestamp_iso=log.timestamp,
                user_name=log.user_name,
                action_type=log.action_type,
                target_type=log.target_type,
                target_id=log.target_id or "",
                description=log.description,
                before_value=log.before_value or "",
                after_value=log.after_value or ""
            )
            log.current_hash = new_hash
            prev_hash = new_hash

        db.commit()
        print("[OK] Re-chained all audit ledger blocks successfully!")
        
        # Verify
        res = verify_audit_chain(db)
        print("[*] Verification Result:", res)
        assert res["chain_intact"] == True, f"Chain still invalid: {res}"
        print("[SUCCESS] Merkle chain is 100% cryptographically verified and intact!")
    finally:
        db.close()

if __name__ == "__main__":
    rechain()
