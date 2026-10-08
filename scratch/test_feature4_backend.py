"""
test_feature4_backend.py
Comprehensive End-to-End Verification for Phase 3 Feature 4: PDF Case-Report Export
"""

import sys
import os
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal
import models
from audit_engine import verify_audit_chain

API_BASE = "http://localhost:8000"

def test_feature4():
    print("\n=======================================================")
    print("TESTING FEATURE 4: PDF CASE-REPORT EXPORT & AUDIT RECORD")
    print("=======================================================")

    # 1. Test PDF Export Endpoint
    print("\n1. Testing GET /cases/1/reports/pdf ...")
    r_pdf = requests.get(f"{API_BASE}/cases/1/reports/pdf")
    print(f"Status Code: {r_pdf.status_code}")
    assert r_pdf.status_code == 200, f"PDF export failed: {r_pdf.text}"
    assert "application/pdf" in r_pdf.headers.get("content-type", "")
    assert r_pdf.content.startswith(b"%PDF-"), "Generated file does not begin with standard PDF magic bytes (%PDF-)!"
    print(f"  => PDF generated successfully: {len(r_pdf.content):,} bytes")
    print(f"  => Content-Disposition header: {r_pdf.headers.get('content-disposition')}")
    assert len(r_pdf.content) > 10000

    # 2. Test Structured Docket Data Endpoint
    print("\n2. Testing GET /cases/1/reports/docket-data ...")
    r_docket = requests.get(f"{API_BASE}/cases/1/reports/docket-data")
    print(f"Status Code: {r_docket.status_code}")
    assert r_docket.status_code == 200
    docket = r_docket.json()
    print("  => Case Title:", docket["case"]["title"])
    print("  => Stats:", docket["stats"])
    print("  => Total Exhibits in Docket:", len(docket["evidence"]))
    print("  => Total Hypotheses in Docket:", len(docket["hypotheses"]))
    print("  => Total Anchored Citations:", len(docket["citations"]))
    assert len(docket["evidence"]) >= 1
    assert len(docket["hypotheses"]) >= 1
    assert "audit_chain" in docket

    # 3. Test Cryptographic Audit Log for REPORT_EXPORT
    print("\n3. Testing Merkle Audit Ledger for REPORT_EXPORT block ...")
    db = SessionLocal()
    try:
        export_logs = db.query(models.AuditLog).filter(
            models.AuditLog.action_type == "REPORT_EXPORT"
        ).order_by(models.AuditLog.id.desc()).all()
        assert len(export_logs) >= 1, "REPORT_EXPORT was not recorded in AuditLog!"
        latest_log = export_logs[0]
        print(f"  => Audit Block ID: #{latest_log.id}")
        print(f"  => Action: {latest_log.action_type}")
        print(f"  => Description: {latest_log.description}")
        print(f"  => Block Hash: {latest_log.current_hash[:24]}...")
        print(f"  => Previous Hash: {latest_log.previous_hash[:24]}...")

        # Verify chain integrity
        chain_res = verify_audit_chain(db)
        print("\n4. Verifying Cryptographic Audit Ledger Integrity:")
        print(f"  => Chain Intact: {chain_res['chain_intact']}")
        print(f"  => Total Blocks: {chain_res['total_entries']}")
        print(f"  => Latest Hash: {chain_res['latest_hash'][:24]}...")
        assert chain_res["chain_intact"] is True
        print("  => PASS: Entire Merkle ledger chain verified 100% intact with zero tampering!")
    finally:
        db.close()

    print("\n=======================================================")
    print("ALL FEATURE 4 TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")

if __name__ == "__main__":
    test_feature4()
