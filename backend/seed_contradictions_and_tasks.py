# backend/seed_contradictions_and_tasks.py
from database import SessionLocal
from models import Case, Contradiction, InvestigationTask

def seed():
    db = SessionLocal()
    try:
        # Check if contradictions already exist
        c_count = db.query(Contradiction).count()
        t_count = db.query(InvestigationTask).count()
        print(f"Current Contradictions: {c_count}, Current Tasks: {t_count}")

        if c_count == 0:
            print("[*] Seeding initial forensic contradictions...")
            initial_contradictions = [
                # Case 1: Nayana Pujari
                Contradiction(
                    case_id=1,
                    statement_a="Suspect Yogesh Raut claimed he dropped the victim safely at Katraj chowk and immediately returned home.",
                    source_a_id="Exhibit #1 (Police Interrogation Memo)",
                    statement_b="ATM CCTV surveillance captures Yogesh Raut personally withdrawing Rs 61,000 using victim's SBI debit card at Swargate at 02:15 AM.",
                    source_b_id="Exhibit #2 (SBI ATM Surveillance Video)",
                    conflict_type="Alibi & Financial Contradiction",
                    confidence=99.0,
                    status="Detected"
                ),
                Contradiction(
                    case_id=1,
                    statement_a="Accused Rajesh Chaudhari was initially suspected as an active in-vehicle attacker during the homicide.",
                    source_a_id="Initial Remand Application",
                    statement_b="Synechron security biometric turnstile logs prove Chaudhari never left his post at Kharadi campus during the physical crime window.",
                    source_b_id="Exhibit #7 (Workplace Biometric Turnstile Logs)",
                    conflict_type="Physical Presence Exoneration",
                    confidence=98.0,
                    status="Resolved"
                ),
                # Case 2: Pune Cyber Heist
                Contradiction(
                    case_id=2,
                    statement_a="Lead Systems Admin claimed he was asleep at home in Kothrud throughout the entire night with device powered off.",
                    source_a_id="Suspect Deposition Memo",
                    statement_b="Cell tower CDR records pinpoint his personal smartphone connected to Hinjewadi Phase 1 cell tower at 02:14 AM concurrent with data exfiltration.",
                    source_b_id="Exhibit #2 (Hinjewadi Tower CDR Dump)",
                    conflict_type="Alibi Discrepancy",
                    confidence=98.0,
                    status="Detected"
                ),
                # Case 3: Indiranagar Homicide
                Contradiction(
                    case_id=3,
                    statement_a="Suspect Suresh Gowda claimed he was in Tumakuru village throughout August 14-15 and never visited Bengaluru.",
                    source_a_id="Interrogation Log Record",
                    statement_b="Latent thumbprint lifted from 1st floor balcony sliding glass door matches Suresh Gowda with 99.4% biometric match score.",
                    source_b_id="Exhibit #2 (Fingerprint Bureau CID Report)",
                    conflict_type="Forensic Alibi Refutation",
                    confidence=99.4,
                    status="Detected"
                ),
                # Case 5: Aarushi Talwar
                Contradiction(
                    case_id=5,
                    statement_a="Initial local police assessment suggested terrace door was bolted with parent key only.",
                    source_a_id="First SIT Police Briefing",
                    statement_b="CBI forensic inspection revealed terrace latch was forcibly jimmied with blunt screwdriver and domestic servant had duplicate key.",
                    source_b_id="Exhibit #1 (CBI Central Forensic Lab Memo)",
                    conflict_type="Physical Access Discrepancy",
                    confidence=89.0,
                    status="Detected"
                ),
                # Case 6: Boston Bombing
                Contradiction(
                    case_id=6,
                    statement_a="Defense counsel claimed Dzhokhar Tsarnaev was an unwitting pawn with no prior knowledge of explosive ideology.",
                    source_a_id="Defense Opening Argument",
                    statement_b="Handwritten manifesto inside Watertown slipway boat detailed pre-meditated operational planning and extremist ideology.",
                    source_b_id="Exhibit #2 (Watertown Boat Inscription Forensics)",
                    conflict_type="Intent & Premeditation Discrepancy",
                    confidence=96.0,
                    status="Detected"
                ),
            ]
            for c in initial_contradictions:
                db.add(c)
            db.commit()
            print(f"[OK] Added {len(initial_contradictions)} forensic contradictions.")

        if t_count == 0:
            print("[*] Seeding initial investigation tasks...")
            initial_tasks = [
                # Case 1: Nayana Pujari
                InvestigationTask(
                    case_id=1,
                    task="Subpoena State Bank ATM CCTV Tapes from Swargate & Hadapsar",
                    reason="Identify physical face of suspect withdrawing cash using victim's SBI debit card",
                    related_evidence_id="1",
                    priority="High",
                    status="Completed",
                    assigned_to="ACP Vinod Satav"
                ),
                InvestigationTask(
                    case_id=1,
                    task="Send Qualis Cab Blood & STR Swabs to FSL Kalina",
                    reason="Confirm biological DNA presence of suspects inside the Toyota Qualis crime vehicle",
                    related_evidence_id="3",
                    priority="High",
                    status="Completed",
                    assigned_to="PI Kishor Mhaswade"
                ),
                InvestigationTask(
                    case_id=1,
                    task="Trace Call Detail Records for Burner Mobile near Zarewadi Forest",
                    reason="Corroborate movement path of accused Yogesh Raut and Mahesh Thakur on night of Oct 7-8",
                    priority="High",
                    status="Pending",
                    assigned_to="Technical Intelligence Cell"
                ),
                # Case 2: Cyber Heist
                InvestigationTask(
                    case_id=2,
                    task="Subpoena ISP Gateway Logs for External IP 185.220.101.5",
                    reason="Determine exit node and physical origin provider for SFTP exfiltration tunnel",
                    related_evidence_id="3",
                    priority="High",
                    status="In Progress",
                    assigned_to="PI Vikram Salunkhe"
                ),
                InvestigationTask(
                    case_id=2,
                    task="Forensic Disk Imaging of Rohan Deshmukh's Workstation",
                    reason="Extract deleted bash history and SSH private key fingerprints",
                    priority="High",
                    status="Pending",
                    assigned_to="Cyber Forensics Unit"
                ),
                # Case 3: Indiranagar Homicide
                InvestigationTask(
                    case_id=3,
                    task="Check Commercial Street Pawn Shops for Stolen Jewelry",
                    reason="Recover physical stolen gold ornaments matching victim inventory",
                    related_evidence_id="2",
                    priority="High",
                    status="In Progress",
                    assigned_to="Insp. B. Manjunath"
                ),
                # Case 5: Aarushi Talwar
                InvestigationTask(
                    case_id=5,
                    task="Examine Touch DNA on Terrace Key and Latch Fixture",
                    reason="Resolve physical access discrepancy between initial SIT theory and CBI findings",
                    related_evidence_id="1",
                    priority="High",
                    status="In Progress",
                    assigned_to="CBI Special Forensics Team"
                ),
                # Case 6: Boston Bombing
                InvestigationTask(
                    case_id=6,
                    task="Ballistic Cross-Match on Watertown Shootout Shell Casings",
                    reason="Match Ruger P95 9mm casings found at MIT shooting scene with recovered Watertown firearm",
                    priority="High",
                    status="Completed",
                    assigned_to="FBI Ballistics Unit"
                )
            ]
            for t in initial_tasks:
                db.add(t)
            db.commit()
            print(f"[OK] Added {len(initial_tasks)} investigation tasks.")

    except Exception as e:
        print(f"[!] Seeding error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
