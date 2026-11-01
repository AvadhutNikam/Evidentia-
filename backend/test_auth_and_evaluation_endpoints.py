"""
backend/test_auth_and_evaluation_endpoints.py
=============================================
Security Verification Suite for:
1. Mandatory JWT_SECRET_KEY validation at startup.
2. Missing secret error handling (halts app startup).
3. Admin-role requirement across all /cases/evaluation/* endpoints.
4. Rejection of unauthenticated requests (401 Unauthorized).
5. Rejection of non-admin roles (403 Forbidden).
6. Success for authenticated admin role (200 OK).
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def test_missing_jwt_secret_halts_startup():
    print("[TEST 1] Testing missing JWT_SECRET_KEY stops app at startup...")
    old_secret = os.environ.get("JWT_SECRET_KEY")
    try:
        # Simulate missing environment variable
        os.environ["JWT_SECRET_KEY"] = ""
        try:
            import auth
            auth.validate_jwt_secret()
            print("  FAIL: Expected RuntimeError when JWT_SECRET_KEY is empty, but none was raised!")
            return False
        except RuntimeError as e:
            print(f"  PASS: App halted at startup with expected error:\n    {str(e).strip().splitlines()[1]}")
            return True
    finally:
        sys.modules.pop('auth', None)
        if old_secret is not None:
            os.environ["JWT_SECRET_KEY"] = old_secret
        else:
            os.environ.pop("JWT_SECRET_KEY", None)

def test_evaluation_endpoints_rbac():
    print("\n[TEST 2] Testing RBAC on all /cases/evaluation/* endpoints...")
    from fastapi.testclient import TestClient
    from app import app
    from auth import create_access_token
    from models import User
    from database import get_db

    client = TestClient(app)

    # Evaluation endpoints to verify
    eval_routes = [
        ("GET", "/cases/evaluation/benchmark-results"),
        ("GET", "/cases/evaluation/dataset"),
        ("GET", "/cases/evaluation/bias-test-results"),
        ("POST", "/cases/evaluation/run"),
        ("POST", "/cases/evaluation/run-bias-tests"),
    ]

    # Create dummy tokens for testing roles
    admin_token = create_access_token({"sub": "admin@evidentia.gov.in", "role": "admin"})
    analyst_token = create_access_token({"sub": "analyst@evidentia.gov.in", "role": "analyst"})
    reviewer_token = create_access_token({"sub": "reviewer@evidentia.gov.in", "role": "reviewer"})

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    all_passed = True

    for method, path in eval_routes:
        # 1. Unauthenticated request (should be 401 Unauthorized)
        if method == "GET":
            unauth_resp = client.get(path)
        else:
            unauth_resp = client.post(path, json={})

        if unauth_resp.status_code == 401:
            print(f"  PASS: {method} {path} -> 401 Unauthorized without token")
        else:
            print(f"  FAIL: {method} {path} -> Expected 401, got {unauth_resp.status_code} ({unauth_resp.text})")
            all_passed = False

        # 2. Non-admin request (should be 403 Forbidden)
        if method == "GET":
            non_admin_resp = client.get(path, headers=analyst_headers)
        else:
            non_admin_resp = client.post(path, json={}, headers=analyst_headers)

        if non_admin_resp.status_code == 403:
            print(f"  PASS: {method} {path} -> 403 Forbidden for analyst role")
        else:
            print(f"  FAIL: {method} {path} -> Expected 403, got {non_admin_resp.status_code} ({non_admin_resp.text})")
            all_passed = False

        # 3. Admin request (should be 200 OK)
        if method == "GET":
            admin_resp = client.get(path, headers=admin_headers)
            if admin_resp.status_code == 200:
                print(f"  PASS: {method} {path} -> 200 OK for admin role")
            else:
                print(f"  FAIL: {method} {path} -> Expected 200 for admin, got {admin_resp.status_code}")
                all_passed = False

    return all_passed

if __name__ == "__main__":
    t1 = test_missing_jwt_secret_halts_startup()
    t2 = test_evaluation_endpoints_rbac()
    if t1 and t2:
        print("\nALL SECURITY TESTS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("\nONE OR MORE SECURITY TESTS FAILED.")
        sys.exit(1)
