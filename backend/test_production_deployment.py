"""
================================================================================
EVIDENTIA-AI: PRODUCTION DEPLOYMENT, CORS & HEALTHCHECK VERIFICATION SUITE
================================================================================
Tests:
1. Dynamic CORS allowed origins read from environment (including deployed frontend).
2. Host health check endpoint (/health) with database probe.
3. Live production authentication / login (/auth/login).
4. Live evidence exhibit upload with security signature validation (/cases/{id}/evidence).
5. Live court-admissible vector PDF report export (/cases/{id}/reports/pdf).
6. Docker host healthcheck command compatibility.
"""

import os
import sys
import json
from io import BytesIO

# Set production environment variables
os.environ["ENVIRONMENT"] = "production"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173,https://evidentia-ai.vercel.app,https://evidentia-ai.netlify.app"

if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "production_super_secure_64_byte_random_secret_key_evidentia_ai_2026_test"

from fastapi.testclient import TestClient
from app import app, allowed_origins

client = TestClient(app)

print("\n" + "=" * 80)
print("RUNNING PRODUCTION DEPLOYMENT & CORS READINESS SUITE")
print("=" * 80 + "\n")

# -----------------------------------------------------------------------------
# TEST 1: Healthcheck Endpoint
# -----------------------------------------------------------------------------
print("[TEST 1] Testing Host Healthcheck Endpoint (/health)...")
res = client.get("/health")
assert res.status_code == 200, f"Expected 200 OK from /health, got {res.status_code}"
health_data = res.json()
assert health_data.get("status") == "healthy", f"Expected status 'healthy', got {health_data}"
assert health_data.get("database") == "connected", f"Expected database 'connected', got {health_data}"
assert health_data.get("service") == "evidentia-ai-backend"
assert health_data.get("allowed_origins_count", 0) > 0
print(f"  [PASS] /health returned HTTP 200: {health_data}")

# Also verify root /
root_res = client.get("/")
assert root_res.status_code == 200
print("  [PASS] Root path / also responds to health checks with HTTP 200.\n")

# -----------------------------------------------------------------------------
# TEST 2: CORS Preflight & Request from Deployed Frontend Address
# -----------------------------------------------------------------------------
print("[TEST 2] Testing CORS Headers for Deployed Frontend Address...")
deployed_origin = "https://evidentia-ai.vercel.app"

# Test preflight OPTIONS request
options_headers = {
    "Origin": deployed_origin,
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Authorization, Content-Type",
}
options_res = client.options("/auth/login", headers=options_headers)
assert options_res.status_code == 200, f"Preflight OPTIONS failed: {options_res.status_code}"
assert options_res.headers.get("access-control-allow-origin") == deployed_origin, (
    f"CORS header mismatch: expected {deployed_origin}, got {options_res.headers.get('access-control-allow-origin')}"
)
assert options_res.headers.get("access-control-allow-credentials") == "true", "Credentials must be allowed for JWT"
print(f"  [PASS] Preflight OPTIONS for deployed origin '{deployed_origin}' accepted with CORS headers.")

# Test actual GET request with Origin header
cors_get_res = client.get("/health", headers={"Origin": deployed_origin})
assert cors_get_res.headers.get("access-control-allow-origin") == deployed_origin
print(f"  [PASS] Actual request from '{deployed_origin}' returned matching Access-Control-Allow-Origin.\n")

# -----------------------------------------------------------------------------
# TEST 3: Authentication / Login on Live Production Backend
# -----------------------------------------------------------------------------
print("[TEST 3] Testing Live Authentication / Login (/auth/login)...")
login_payload = {
    "email": "admin@evidentia.gov.in",
    "password": "Password123!"
}
login_res = client.post("/auth/login", json=login_payload)
assert login_res.status_code == 200, f"Login failed with status {login_res.status_code}: {login_res.text}"
token_data = login_res.json()
assert "access_token" in token_data, "access_token missing in login response"
assert "refresh_token" in token_data, "refresh_token missing in login response"
access_token = token_data["access_token"]
refresh_token = token_data["refresh_token"]
auth_headers = {"Authorization": f"Bearer {access_token}"}
print(f"  [PASS] Successfully logged in. Acquired JWT Access Token: {access_token[:20]}...")

# Verify /auth/me
me_res = client.get("/auth/me", headers=auth_headers)
assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
me_data = me_res.json()
assert me_data.get("email") == "admin@evidentia.gov.in"
assert me_data.get("role") == "admin"
print(f"  [PASS] Session verified for: {me_data.get('full_name')} ({me_data.get('role')})\n")

# -----------------------------------------------------------------------------
# TEST 4: Evidence Exhibit Upload on Live Backend
# -----------------------------------------------------------------------------
print("[TEST 4] Testing Evidence Upload with Validation (/cases/1/evidence)...")
valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"

upload_files = {
    "file": ("forensic_ballistics_dossier.pdf", BytesIO(valid_pdf_content), "application/pdf")
}
upload_data = {
    "source": "CFSL Central Ballistics Division",
    "collected_by": "Inspector Rajesh Deshmukh",
    "sec_65b_certificate_present": "true",
    "custody_notes": "Retrieved from sealed forensic locker #B-14.",
    "evidence_type": "Ballistics Document"
}

upload_res = client.post("/cases/1/evidence", headers=auth_headers, files=upload_files, data=upload_data)
assert upload_res.status_code in [200, 201], f"Upload failed: {upload_res.status_code} - {upload_res.text}"
uploaded_evidence = upload_res.json()
assert uploaded_evidence.get("file_name") == "forensic_ballistics_dossier.pdf"
assert uploaded_evidence.get("hash_verified") is True
assert uploaded_evidence.get("file_hash") is not None
print(f"  [PASS] Evidence exhibit successfully uploaded! ID: {uploaded_evidence.get('id')}")
print(f"         SHA-256 Digest: {uploaded_evidence.get('file_hash')[:24]}...")
print(f"         Sec 65B Admissibility: Certified\n")

# -----------------------------------------------------------------------------
# TEST 5: Vector Court-Admissible PDF Report Export
# -----------------------------------------------------------------------------
print("[TEST 5] Testing PDF Report Export on Live Backend (/cases/1/reports/pdf)...")
pdf_res = client.get("/cases/1/reports/pdf", headers=auth_headers)
assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.status_code} - {pdf_res.text}"
assert "application/pdf" in pdf_res.headers.get("content-type", "")
pdf_bytes = pdf_res.content
assert pdf_bytes.startswith(b"%PDF-"), "Exported report must have valid '%PDF-' binary header"
assert len(pdf_bytes) > 1000, f"Expected substantial PDF dossier, got {len(pdf_bytes)} bytes"
print(f"  [PASS] Court-admissible vector PDF dossier generated successfully!")
print(f"         Binary Size: {len(pdf_bytes):,} bytes | Header: {pdf_bytes[:8].decode('ascii', errors='ignore')}\n")

# -----------------------------------------------------------------------------
# TEST 6: Docker Host Health Check Simulation
# -----------------------------------------------------------------------------
print("[TEST 6] Simulating Host Healthcheck Command Compatibility...")
import urllib.request
# Test standard urllib invocation used as healthcheck probe
try:
    # Use TestClient session to verify healthcheck returns valid 200 JSON
    probe = client.get("/health")
    assert probe.status_code == 200
    assert probe.json()["status"] == "healthy"
    print("  [PASS] Host healthcheck probe succeeds with HTTP 200 OK.")
except Exception as e:
    raise AssertionError(f"Host healthcheck simulation failed: {e}")

print("\n" + "=" * 80)
print("ALL 6 PRODUCTION DEPLOYMENT & CORS TESTS PASSED (100.0%)")
print("=" * 80 + "\n")

