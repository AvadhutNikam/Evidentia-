"""
test_feature3_backend.py
Comprehensive End-to-End Verification for Feature 3: Source-Span Citations & Provenance Engine
"""

import sys
import os
import requests
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from citation_engine import (
    chunk_text,
    verify_and_anchor_quote,
    index_exhibit_chunks,
    anchor_fact_citation,
    update_and_reindex_exhibit_text
)
from database import SessionLocal
import models
from audit_engine import verify_audit_chain

API_BASE = "http://localhost:8000"

def test_quote_verification_logic():
    print("\n--- 1. Testing Citation Verification & Anti-Hallucination Engine ---")
    doc_text = """FIRST INFORMATION REPORT (CR NO. 142/2009)
Dated: 08-10-2009. Complainant: Arvind Dnyaneshwar Borde.
Accused No. 1 Yogesh Ashok Raut along with Mahesh Thakur abducted Nayana Pujari from Kharadi Bypass.
A gold ring with initials NP was recovered from the accused's rented room at Mundhwa.
Cash of Rs 61,000 withdrawn from SBI ATM at Vimannagar using deceased's debit card."""

    # Test 1: Exact Substring Match
    res_exact = verify_and_anchor_quote(
        full_text=doc_text,
        raw_quote="A gold ring with initials NP was recovered"
    )
    print("Exact Match Result:", res_exact)
    assert res_exact["verified_match"] is True
    assert res_exact["verification_method"] == "exact_substring"
    assert res_exact["match_confidence"] == 1.0
    assert doc_text[res_exact["char_start"]:res_exact["char_end"]] == "A gold ring with initials NP was recovered"
    print("  => PASS: Exact substring located and anchored precisely.")

    # Test 2: Normalized Substring (whitespace & punctuation tolerance)
    res_norm = verify_and_anchor_quote(
        full_text=doc_text,
        raw_quote="   a  gold  ring  with  initials  np  was  recovered  "
    )
    print("Normalized Match Result:", res_norm)
    assert res_norm["verified_match"] is True
    assert res_norm["verification_method"] == "normalized_substring"
    assert res_norm["match_confidence"] >= 0.95
    print("  => PASS: Normalized match located and anchored.")

    # Test 3: Fuzzy Token Similarity (OCR/ASR minor artifact)
    res_fuzzy = verify_and_anchor_quote(
        full_text=doc_text,
        raw_quote="Yogesh Ashok Raut along with Mahesh Thakur abducted Nayana Pujari from Kharadi Bypas" # typo Bypas
    )
    print("Fuzzy Match Result:", res_fuzzy)
    assert res_fuzzy["verified_match"] is True
    assert res_fuzzy["verification_method"] in ("fuzzy_token", "normalized_substring", "exact_substring")
    assert res_fuzzy["match_confidence"] >= 0.75
    print("  => PASS: Fuzzy OCR artifact successfully anchored with high token similarity.")

    # Test 4: Completely Hallucinated / Fabricated Fact
    res_hallucinated = verify_and_anchor_quote(
        full_text=doc_text,
        raw_quote="The suspect was driving a purple helicopter over the Atlantic Ocean in 1972"
    )
    print("Hallucination Match Result:", res_hallucinated)
    assert res_hallucinated["verified_match"] is False
    assert res_hallucinated["verification_method"] == "unverified"
    assert res_hallucinated["match_confidence"] < 0.75
    print("  => PASS: Hallucinated quote detected, flagged unverified, and rejected from trusted anchors.")


def test_api_endpoints():
    print("\n--- 2. Testing Feature 3 REST Endpoints ---")
    
    # Check chunks endpoint for Exhibit 1
    r_chunks = requests.get(f"{API_BASE}/cases/1/evidence/1/chunks")
    print(f"GET /cases/1/evidence/1/chunks: Status {r_chunks.status_code}")
    assert r_chunks.status_code == 200, f"Failed chunks fetch: {r_chunks.text}"
    chunks_data = r_chunks.json()
    print(f"  => Found {len(chunks_data)} exhibit chunks for Exhibit 1.")
    assert len(chunks_data) >= 1
    sample_chunk = chunks_data[0]
    assert "chunk_index" in sample_chunk
    assert "char_start" in sample_chunk
    assert "char_end" in sample_chunk
    assert "text" in sample_chunk

    # Check citations endpoint for Exhibit 1
    r_cits = requests.get(f"{API_BASE}/cases/1/evidence/1/citations")
    print(f"GET /cases/1/evidence/1/citations: Status {r_cits.status_code}")
    assert r_cits.status_code == 200, f"Failed citations fetch: {r_cits.text}"
    cits_data = r_cits.json()
    print(f"  => Found {len(cits_data)} source citations for Exhibit 1.")
    assert len(cits_data) >= 1
    for c in cits_data[:3]:
        print(f"     * [{c['fact_type'].upper()}] quote='{c['quote'][:40]}...' verified={c['verified_match']} ({c['verification_method']})")

    # Check case-wide citations filter
    r_case_cits = requests.get(f"{API_BASE}/cases/1/citations?fact_type=entity")
    assert r_case_cits.status_code == 200
    case_cits = r_case_cits.json()
    print(f"GET /cases/1/citations?fact_type=entity: Found {len(case_cits)} entity citations.")
    assert len(case_cits) >= 1


def test_analyst_correction_and_audit():
    print("\n--- 3. Testing Analyst OCR Correction & Merkle Audit Trail ---")
    # Get current exhibit 1 text
    r_ev = requests.get(f"{API_BASE}/evidence/1")
    assert r_ev.status_code == 200
    ev_data = r_ev.json()
    original_text = ev_data.get("extracted_text", "")

    # Perform an analyst correction: append an official forensic addendum
    correction_text = original_text + "\n\n[ANALYST CORRECTION NOTE: OCR verified against original prosecution exhibit registry. All character spans re-anchored.]"
    
    # Update via PUT endpoint
    r_put = requests.put(
        f"{API_BASE}/cases/1/evidence/1/extracted-text",
        headers={"Content-Type": "application/json"},
        json={"extracted_text": correction_text, "text": correction_text}
    )
    print(f"PUT /cases/1/evidence/1/extracted-text: Status {r_put.status_code}")
    assert r_put.status_code == 200, f"Correction failed: {r_put.text}"
    put_data = r_put.json()
    print("Correction Response:", put_data)
    assert put_data["success"] is True
    assert put_data["total_chunks"] >= 1
    assert put_data["verified_citations"] >= 1

    # Verify that a TEXT_CORRECTION audit event was chained to the Merkle ledger
    db = SessionLocal()
    try:
        latest_audit = db.query(models.AuditLog).filter(
            models.AuditLog.action_type == "TEXT_CORRECTION"
        ).order_by(models.AuditLog.id.desc()).first()
        assert latest_audit is not None, "TEXT_CORRECTION was not logged in AuditLog!"
        print(f"  => Audit block recorded: ID={latest_audit.id}, hash={latest_audit.current_hash[:24]}...")
        assert "corrected" in latest_audit.description.lower()

        # Verify the entire Merkle ledger chain remains cryptographically intact
        chain_status = verify_audit_chain(db)
        print("  => Cryptographic Audit Ledger Integrity Verification:")
        print(f"     Chain intact: {chain_status['chain_intact']}")
        print(f"     Total entries: {chain_status['total_entries']}")
        print(f"     Latest hash: {chain_status['latest_hash'][:24]}...")
        assert chain_status["chain_intact"] is True
        print("  => PASS: Entire audit chain is intact and uncorrupted after text correction!")
    finally:
        db.close()


if __name__ == "__main__":
    test_quote_verification_logic()
    test_api_endpoints()
    test_analyst_correction_and_audit()
    print("\n=======================================================")
    print("ALL FEATURE 3 BACKEND & CITATION TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")
