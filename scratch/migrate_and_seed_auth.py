import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from database import engine, SessionLocal, Base
from models import User, CaseMember, Case
from auth import hash_password

def migrate_and_seed():
    print("[MIGRATION] Creating users and case_members tables if not existing...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if users already exist
        existing_users = db.query(User).all()
        print(f"[AUTH SEED] Found {len(existing_users)} existing users.")

        demo_users = [
            {
                "email": "admin@evidentia.gov.in",
                "full_name": "Superintendent S. Roy",
                "role": "admin",
                "badge_number": "IPS-9041",
                "department": "State Cyber & Forensics Directorate",
                "password": "Password123!"
            },
            {
                "email": "lead@evidentia.gov.in",
                "full_name": "PI Vikram Salunkhe",
                "role": "lead_investigator",
                "badge_number": "MH-CID-441",
                "department": "Crime Investigation Department (CID)",
                "password": "Password123!"
            },
            {
                "email": "analyst@evidentia.gov.in",
                "full_name": "Dr. Ananya Sen",
                "role": "analyst",
                "badge_number": "FSL-DNA-108",
                "department": "Forensic Science Laboratory (FSL)",
                "password": "Password123!"
            },
            {
                "email": "reviewer@evidentia.gov.in",
                "full_name": "Adv. Ramesh Sharma (Special Public Prosecutor)",
                "role": "reviewer",
                "badge_number": "BAR-MH-8812",
                "department": "Directorate of Public Prosecutions",
                "password": "Password123!"
            }
        ]

        user_map = {}
        for u_data in demo_users:
            u_obj = db.query(User).filter(User.email == u_data["email"]).first()
            if not u_obj:
                u_obj = User(
                    email=u_data["email"],
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    badge_number=u_data["badge_number"],
                    department=u_data["department"],
                    hashed_password=hash_password(u_data["password"]),
                    is_active=True
                )
                db.add(u_obj)
                db.commit()
                db.refresh(u_obj)
                print(f"  [+] Created user {u_obj.email} (Role: {u_obj.role})")
            else:
                # Update password hash just in case
                u_obj.hashed_password = hash_password(u_data["password"])
                u_obj.role = u_data["role"]
                db.commit()
                print(f"  [*] Updated user {u_obj.email} (Role: {u_obj.role})")
            user_map[u_data["role"]] = u_obj

        # Assign case memberships
        cases = db.query(Case).all()
        print(f"[AUTH SEED] Assigning case memberships across {len(cases)} cases...")

        # Case 1 (Nayana Pujari): Assigned to Lead, Analyst, Reviewer
        # Case 2 (Cyber Heist): Assigned to Lead, Analyst
        # Case 3 (Indiranagar): Assigned to Analyst only
        # Case 4 (Operation Blackout): Assigned to Lead only
        # Case 5 (Aarushi): Assigned to Reviewer only
        assignments = [
            (1, "lead_investigator"),
            (1, "analyst"),
            (1, "reviewer"),
            (2, "lead_investigator"),
            (2, "analyst"),
            (3, "analyst"),
            (4, "lead_investigator"),
            (5, "reviewer")
        ]

        for case_id, role_key in assignments:
            u = user_map.get(role_key)
            if not u:
                continue
            # Check if case exists
            c = db.query(Case).filter(Case.id == case_id).first()
            if not c:
                continue
            existing_m = db.query(CaseMember).filter(
                CaseMember.case_id == case_id,
                CaseMember.user_id == u.id
            ).first()
            if not existing_m:
                m = CaseMember(
                    case_id=case_id,
                    user_id=u.id,
                    case_role=role_key,
                    added_by="System Provisioning"
                )
                db.add(m)
                print(f"  [+] Added member {u.full_name} ({role_key}) to Case #{case_id}")

        db.commit()
        print("[AUTH SEED] Migration and initial provisioning completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_and_seed()
