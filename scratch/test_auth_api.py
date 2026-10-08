import requests

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("==================================================")
    print(" TESTING PHASE 3: AUTHENTICATION & RBAC ENDPOINTS ")
    print("==================================================")

    # 1. Invalid Password Test
    print("\n[1] Testing invalid password attempt...")
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": "analyst@evidentia.gov.in", "password": "WrongPassword"})
    print("Status:", r.status_code, "Detail:", r.json().get("detail"))
    assert r.status_code == 401, "Expected 401 for bad password"

    # 2. Login as Admin
    print("\n[2] Logging in as Admin (admin@evidentia.gov.in)...")
    r_admin = requests.post(f"{BASE_URL}/auth/login", json={"email": "admin@evidentia.gov.in", "password": "Password123!"})
    print("Status:", r_admin.status_code)
    assert r_admin.status_code == 200
    admin_token = r_admin.json()["access_token"]
    admin_user = r_admin.json()["user"]
    print("Admin User:", admin_user["full_name"], "Role:", admin_user["role"], "Badge:", admin_user["badge_number"])

    # 3. Login as Reviewer
    print("\n[3] Logging in as Reviewer (reviewer@evidentia.gov.in)...")
    r_rev = requests.post(f"{BASE_URL}/auth/login", json={"email": "reviewer@evidentia.gov.in", "password": "Password123!"})
    print("Status:", r_rev.status_code)
    assert r_rev.status_code == 200
    rev_token = r_rev.json()["access_token"]
    rev_user = r_rev.json()["user"]
    print("Reviewer User:", rev_user["full_name"], "Role:", rev_user["role"])
    print("Accessible Cases for Reviewer:", rev_user["accessible_cases"])

    # 4. Case Isolation Test: Reviewer vs Admin
    print("\n[4] Case Isolation: Fetching /cases as Reviewer...")
    r_rev_cases = requests.get(f"{BASE_URL}/cases", headers={"Authorization": f"Bearer {rev_token}"})
    print("Reviewer Case Count:", len(r_rev_cases.json()))
    rev_case_ids = [c["id"] for c in r_rev_cases.json()]
    print("Reviewer Case IDs:", rev_case_ids)

    print("\n[5] Case Isolation: Fetching /cases as Admin...")
    r_admin_cases = requests.get(f"{BASE_URL}/cases", headers={"Authorization": f"Bearer {admin_token}"})
    print("Admin Case Count:", len(r_admin_cases.json()))
    admin_case_ids = [c["id"] for c in r_admin_cases.json()]
    print("Admin Case IDs:", admin_case_ids)
    assert len(admin_case_ids) >= len(rev_case_ids), "Admin must see all cases"

    # 6. RBAC Permission Test: Reviewer attempting deletion
    print("\n[6] Testing RBAC Enforcement: Reviewer attempting delete_case...")
    r_del = requests.delete(f"{BASE_URL}/cases/1", headers={"Authorization": f"Bearer {rev_token}"})
    print("Status:", r_del.status_code, "Detail:", r_del.json().get("detail"))
    assert r_del.status_code == 403, "Reviewer must be blocked with 403 Forbidden"

    # 7. Case Members Endpoint Test
    print("\n[7] Testing /cases/1/members as Admin...")
    r_members = requests.get(f"{BASE_URL}/cases/1/members", headers={"Authorization": f"Bearer {admin_token}"})
    print("Status:", r_members.status_code, "Members Count:", len(r_members.json()))
    for m in r_members.json():
        print(f"  - {m['user_name']} ({m['case_role']}) [Email: {m['user_email']}]")

    # 8. /auth/me Test
    print("\n[8] Testing /auth/me with Bearer token...")
    r_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    print("Current User Me:", r_me.json()["email"], "Role:", r_me.json()["role"])

    print("\n==================================================")
    print(" ALL BACKEND AUTH & RBAC TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
