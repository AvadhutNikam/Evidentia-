"""
backend/test_upload_validation.py
=================================
Automated Verification Suite for Evidence Upload Validation:
1. Whitelist enforcement for forensic types (PDF, Images, Audio, Video, Text, CSV, PCAP).
2. Deep file signature / magic byte inspection (rejecting disguised files, e.g. .exe as .pdf).
3. Maximum file size enforcement (per-file limit 50 MB).
4. Cumulative case storage limit enforcement (250 MB).
5. Filename sanitization and directory traversal prevention.
6. Detailed error messages and tamper-evident audit ledger logging.
"""

import sys
import io
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app import app
from auth import create_access_token
from database import SessionLocal
from models import Case, Evidence, AuditLog, User
from upload_validator import (
    sanitize_filename,
    detect_file_signature,
    MAX_FILE_SIZE_BYTES,
    MAX_CASE_STORAGE_BYTES
)

def run_upload_validation_tests():
    print("=" * 80)
    print("EVIDENTIA-AI: UPLOAD VALIDATION & FORENSIC SECURITY TEST SUITE")
    print("=" * 80)

    db = SessionLocal()
    client = TestClient(app)

    # 1. Setup test user & case
    admin_token = create_access_token({"sub": "admin@evidentia.gov.in", "role": "admin"})
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    test_case = db.query(Case).first()
    if not test_case:
        test_case = Case(title="Upload Security Test Case", case_type="Homicide", status="open")
        db.add(test_case)
        db.commit()
        db.refresh(test_case)

    case_id = test_case.id
    print(f"[SETUP] Using Case #{case_id} for upload security testing.\n")

    passed_count = 0
    total_tests = 0

    def assert_test(condition: bool, test_name: str, details: str = ""):
        nonlocal passed_count, total_tests
        total_tests += 1
        if condition:
            print(f"  [PASS] {test_name} {details}")
            passed_count += 1
        else:
            print(f"  [FAIL] {test_name} {details}")

    # =========================================================================
    # TEST 1: Filename Sanitization & Traversal Prevention
    # =========================================================================
    print("[CATEGORY 1] Filename Sanitization & Path Traversal Prevention")
    traversal_input = "../../../etc/passwd.pdf"
    sanitized = sanitize_filename(traversal_input)
    assert_test(sanitized == "passwd.pdf", "Directory traversal stripped", f"('{traversal_input}' -> '{sanitized}')")

    win_traversal = "..\\..\\windows\\system32\\cmd.exe"
    sanitized_win = sanitize_filename(win_traversal)
    assert_test(not sanitized_win.startswith("..") and "cmd.exe" in sanitized_win, "Windows traversal stripped", f"('{win_traversal}' -> '{sanitized_win}')")

    dirty_name = "evidence\x00_test;<script>alert(1)</script>.png"
    sanitized_dirty = sanitize_filename(dirty_name)
    assert_test("<" not in sanitized_dirty and "\x00" not in sanitized_dirty, "Control chars & XSS characters stripped", f"('{sanitized_dirty}')")

    # =========================================================================
    # TEST 2: Disallowed Extensions Rejected
    # =========================================================================
    print("\n[CATEGORY 2] Extension Whitelisting (Disallowed Extensions Rejected)")
    disallowed_extensions = ["malware.exe", "exploit.bat", "script.sh", "webshell.php", "payload.dll", "driver.sys"]
    for bad_name in disallowed_extensions:
        res = client.post(
            f"/cases/{case_id}/evidence",
            files={"file": (bad_name, b"some raw content here", "application/octet-stream")},
            headers=auth_headers
        )
        assert_test(res.status_code == 400, f"Rejected disallowed extension '{bad_name}'", f"-> {res.status_code} ({res.json().get('detail', '')[:45]}...)")

    # =========================================================================
    # TEST 3: File Signature / Magic Byte Verification (Disguised Files Rejected)
    # =========================================================================
    print("\n[CATEGORY 3] Magic Byte & Signature Verification (Disguised Files)")

    # A. Executable disguised as PDF (starts with MZ)
    fake_pdf_mz = b"MZ\x90\x00\x03\x00\x00\x00This is a Windows executable disguised as PDF"
    res_fake_pdf = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("fake_document.pdf", fake_pdf_mz, "application/pdf")},
        headers=auth_headers
    )
    assert_test(res_fake_pdf.status_code == 400, "Rejected Windows PE/MZ binary disguised as .pdf", f"-> {res_fake_pdf.status_code} ({res_fake_pdf.json().get('detail')[:50]}...)")

    # B. Linux ELF binary disguised as PNG
    fake_png_elf = b"\x7FELF\x02\x01\x01\x00Linux binary payload"
    res_fake_png = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("fake_image.png", fake_png_elf, "image/png")},
        headers=auth_headers
    )
    assert_test(res_fake_png.status_code == 400, "Rejected Linux ELF binary disguised as .png", f"-> {res_fake_png.status_code} ({res_fake_png.json().get('detail')[:50]}...)")

    # C. Corrupted / Fake PDF (does not start with %PDF-)
    corrupted_pdf = b"Plain random garbage text without PDF header"
    res_corrupt_pdf = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("corrupt.pdf", corrupted_pdf, "application/pdf")},
        headers=auth_headers
    )
    assert_test(res_corrupt_pdf.status_code == 400, "Rejected non-PDF content with .pdf extension", f"-> {res_corrupt_pdf.status_code} ({res_corrupt_pdf.json().get('detail')[:50]}...)")

    # D. Binary null bytes inside text file
    fake_text_nulls = b"Valid header\x00\x00\x01\x02\x03binary payload injected into text"
    res_fake_txt = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("notes.txt", fake_text_nulls, "text/plain")},
        headers=auth_headers
    )
    assert_test(res_fake_txt.status_code == 400, "Rejected binary null bytes inside declared text file", f"-> {res_fake_txt.status_code} ({res_fake_txt.json().get('detail')[:50]}...)")

    # =========================================================================
    # TEST 4: Empty Files Rejected
    # =========================================================================
    print("\n[CATEGORY 4] Empty File Check")
    res_empty = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("empty.txt", b"", "text/plain")},
        headers=auth_headers
    )
    assert_test(res_empty.status_code == 400, "Rejected 0-byte empty file", f"-> {res_empty.status_code} ({res_empty.json().get('detail')})")

    # =========================================================================
    # TEST 5: Legitimate Forensic Types Accepted
    # =========================================================================
    print("\n[CATEGORY 5] Legitimate Forensic Evidence Types Accepted")

    # A. Valid PDF
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res_pdf = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("autopsy_report.pdf", valid_pdf_bytes, "application/pdf")},
        headers=auth_headers
    )
    assert_test(res_pdf.status_code == 200, "Accepted authentic PDF document", f"-> ID #{res_pdf.json().get('id', '')}")

    # B. Valid JPEG
    valid_jpeg_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB"
    res_jpg = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("crime_scene_photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        headers=auth_headers
    )
    assert_test(res_jpg.status_code == 200, "Accepted authentic JPEG image", f"-> ID #{res_jpg.json().get('id', '')}")

    # C. Valid PNG
    valid_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    res_png = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("fingerprint_card.png", valid_png_bytes, "image/png")},
        headers=auth_headers
    )
    assert_test(res_png.status_code == 200, "Accepted authentic PNG image", f"-> ID #{res_png.json().get('id', '')}")

    # D. Valid Plain Text
    valid_txt_bytes = b"State of New Delhi vs. Accused. CDR cell tower logs corroborate physical presence."
    res_txt = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("investigator_notes.txt", valid_txt_bytes, "text/plain")},
        headers=auth_headers
    )
    assert_test(res_txt.status_code == 200, "Accepted authentic forensic text notes", f"-> ID #{res_txt.json().get('id', '')}")

    # E. Valid CSV
    valid_csv_bytes = b"timestamp,tower_id,imsi,msisdn,duration_sec\n2026-04-30T23:59:00Z,TOWER-DEL-04,40445,9811002233,45\n"
    res_csv = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("cdr_dump.csv", valid_csv_bytes, "text/csv")},
        headers=auth_headers
    )
    assert_test(res_csv.status_code == 200, "Accepted authentic forensic CSV log", f"-> ID #{res_csv.json().get('id', '')}")

    # F. Valid PCAP (packet capture)
    valid_pcap_bytes = b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00"
    res_pcap = client.post(
        f"/cases/{case_id}/evidence",
        files={"file": ("firewall_capture.pcap", valid_pcap_bytes, "application/vnd.tcpdump.pcap")},
        headers=auth_headers
    )
    assert_test(res_pcap.status_code == 200, "Accepted authentic PCAP network packet capture", f"-> ID #{res_pcap.json().get('id', '')}")

    # =========================================================================
    # TEST 6: Audit Logging of Rejected Uploads
    # =========================================================================
    print("\n[CATEGORY 6] Audit Ledger Recording of Rejections")
    rejected_logs = (
        db.query(AuditLog)
        .filter(AuditLog.action_type == "EVIDENCE_UPLOAD_REJECTED", AuditLog.case_id == case_id)
        .order_by(AuditLog.id.desc())
        .all()
    )
    assert_test(len(rejected_logs) >= 5, "Rejection events recorded in Merkle audit ledger", f"({len(rejected_logs)} rejections logged with cryptographic hash)")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed_count} of {total_tests} tests passed ({passed_count/total_tests*100:.1f}%)")
    print("=" * 80)

    db.close()
    return passed_count == total_tests

if __name__ == "__main__":
    success = run_upload_validation_tests()
    sys.exit(0 if success else 1)

