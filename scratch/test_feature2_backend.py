# scratch/test_feature2_backend.py
import requests
import io
import hashlib

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("[*] Testing Feature 2: SHA-256 Hashing, Custody & Merkle Audit Ledger...")

    # 1. Login as lead investigator
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "lead@evidentia.gov.in",
        "password": "Password123!"
    })


    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_data = login_res.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Authenticated as {token_data['user']['full_name']} ({token_data['user']['role']})")

    # 2. Upload test evidence with custody form
    test_content = b"EVIDENTIA_FORENSIC_RAW_PAYLOAD_TEST_BYTES_2026"
    expected_hash = hashlib.sha256(test_content).hexdigest()
    print(f"[*] Expected raw byte SHA-256: {expected_hash}")

    files = {
        "file": ("forensic_packet_trace.pcap", io.BytesIO(test_content), "application/octet-stream")
    }
    data = {
        "source": "Cyber Cell Traffic Interceptor 09",
        "collected_by": "Insp. S. Gaikwad (SIT Lead)",
        "collection_date": "2026-10-08T18:00:00Z",
        "custody_notes": "Intercepted packet trace captured under magistrate search warrant #SW-2026-88.",
        "evidence_type": "digital",
        "sec_65b_certificate_present": "true"
    }

    up_res = requests.post(f"{BASE_URL}/cases/1/evidence", headers=headers, files=files, data=data)
    assert up_res.status_code == 200, f"Upload failed: {up_res.text}"
    up_data = up_res.json()
    evidence_id = up_data["id"]
    print(f"[OK] Uploaded exhibit #{evidence_id}. Recorded hash: {up_data['file_hash']}")
    assert up_data["file_hash"] == expected_hash, f"Hash mismatch: expected {expected_hash}, got {up_data['file_hash']}"
    assert up_data["sec_65b_certificate_present"] == True
    assert up_data["collected_by"] == "Insp. S. Gaikwad (SIT Lead)"

    # 3. Verify exhibit integrity endpoint
    verify_res = requests.post(f"{BASE_URL}/cases/1/evidence/{evidence_id}/verify-integrity", headers=headers)
    assert verify_res.status_code == 200, f"Verify integrity failed: {verify_res.text}"
    v_data = verify_res.json()
    print(f"[OK] Integrity check response: status={v_data['status']}, verified={v_data['integrity_verified']}")
    assert v_data["integrity_verified"] == True
    assert v_data["status"] == "VALID_INTACT"

    # 4. Fetch custody timeline
    custody_res = requests.get(f"{BASE_URL}/cases/1/evidence/{evidence_id}/custody-logs", headers=headers)
    assert custody_res.status_code == 200, f"Fetch custody logs failed: {custody_res.text}"
    c_logs = custody_res.json()
    print(f"[OK] Exhibit #{evidence_id} has {len(c_logs)} custody milestones:")
    for log in c_logs:
        print(f"    - [{log['action']}] by {log['actor_name']} ({log['timestamp']}) -> {log['notes'][:50]}...")
    assert len(c_logs) >= 2, "Expected at least SEIZURE and INTAKE milestones"

    # 5. Fetch audit logs
    audit_res = requests.get(f"{BASE_URL}/cases/1/audit-logs", headers=headers)
    assert audit_res.status_code == 200, f"Fetch audit logs failed: {audit_res.text}"
    a_logs = audit_res.json()
    print(f"[OK] Case #1 has {len(a_logs)} audit ledger entries.")
    latest_block = a_logs[0]
    print(f"    Latest Block #{latest_block['id']}: [{latest_block['action_type']}] Hash: {latest_block['current_hash'][:16]}... Prev: {latest_block['previous_hash'][:16]}...")

    # 6. Cryptographically verify the Merkle Audit Chain
    chain_res = requests.get(f"{BASE_URL}/audit/verify-chain", headers=headers)
    assert chain_res.status_code == 200, f"Chain verify failed: {chain_res.text}"
    chain_data = chain_res.json()
    print(f"[OK] Merkle Audit Chain Verification:")
    print(f"    - Chain intact: {chain_data['chain_intact']}")
    print(f"    - Total verified entries: {chain_data['verified_count']} / {chain_data['total_entries']}")
    print(f"    - Genesis Hash: {chain_data['genesis_hash'][:16]}...")
    print(f"    - Tip Hash: {chain_data['latest_hash'][:16]}...")
    print(f"    - Message: {chain_data['message']}")
    assert chain_data["chain_intact"] == True, f"Chain broke! Error: {chain_data.get('error')}"

    # 7. Soft delete exhibit
    del_res = requests.delete(f"{BASE_URL}/evidence/{evidence_id}", headers=headers)
    assert del_res.status_code == 200, f"Soft delete failed: {del_res.text}"
    del_data = del_res.json()
    print(f"[OK] Soft-delete result: {del_data['message']}")

    # 8. Check that active evidence list omits soft-deleted exhibit, but custody and audit chain remain intact
    ev_list_res = requests.get(f"{BASE_URL}/cases/1/evidence", headers=headers)
    active_ids = [e["id"] for e in ev_list_res.json()]
    assert evidence_id not in active_ids, "Soft-deleted exhibit should not be in active list"
    print(f"[OK] Soft-deleted exhibit #{evidence_id} excluded from active list.")

    # Re-verify chain after soft-delete
    chain_res2 = requests.get(f"{BASE_URL}/audit/verify-chain", headers=headers)
    assert chain_res2.status_code == 200
    assert chain_res2.json()["chain_intact"] == True
    print(f"[OK] Merkle chain re-verified intact after soft-deletion ({chain_res2.json()['verified_count']} blocks).")

    print("\n[SUCCESS] ALL FEATURE 2 ENDPOINTS AND CRYPTOGRAPHIC CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
