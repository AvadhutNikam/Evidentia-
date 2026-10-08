# backend/seed_db.py
"""
Complete Database Seeder Script for Evidentia AI.
Seeds rich, authentic cases, evidence, entities, and events into the active database (SQLite or PostgreSQL).
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import engine, SessionLocal, Base
from models import Case, Evidence, EvidenceStatus, Entity, Event
from datetime import datetime

# Ensure all database tables exist
Base.metadata.create_all(bind=engine)

def seed(force=False):
    db = SessionLocal()
    try:
        existing_cases = db.query(Case).all()
        total_ev = db.query(Evidence).count()
        if existing_cases and total_ev >= 20 and not force:
            print(f"[INFO] Database already contains {len(existing_cases)} cases with {total_ev} evidence exhibits.")
            return

        if existing_cases:
            print(f"[INFO] Existing database has {len(existing_cases)} cases but only {total_ev} evidence. Refreshing records...")
            db.query(Event).delete()
            db.query(Entity).delete()
            db.query(Evidence).delete()
            db.query(Case).delete()
            db.commit()

        print("[INFO] Seeding all 6 investigation cases with complete evidence, entities, and events...")

        cases_data = [
            # Case 1
            {
                "id": 1,
                "title": "State of Maharashtra vs. Yogesh Raut & 3 Others (Pune Techie Nayana Pujari Case)",
                "description": "Landmark Pune investigation into abduction, robbery, and murder of Synechron software engineer Nayana Pujari. Analyzed 4 suspects through ATM CCTV, CDR tracking, vehicle forensics, and approver confession under Sec 164 CrPC.",
                "status": "Closed",
                "created_by": "PI Kishor Mhaswade"
            },
            # Case 2
            {
                "id": 2,
                "title": "State of Maharashtra vs. Accused (Pune Cyber Heist & Data Exfiltration)",
                "description": "Investigation under Sec 66 IT Act & Sec 154 CrPC into unauthorized database intrusion, exfiltration of 42GB proprietary financial algorithms, and Bitcoin extortion demand at TechAxis Solutions Kharadi.",
                "status": "Active",
                "created_by": "PI Vikram Salunkhe"
            },
            # Case 3
            {
                "id": 3,
                "title": "State of Karnataka vs. Accused (Indiranagar Homicide & Armed Robbery)",
                "description": "Karnataka Police FIR investigation into residential break-in, fatal blunt-force assault, and robbery of gold jewelry and bearer bonds at 100ft Road, Indiranagar, Bengaluru.",
                "status": "Under Investigation",
                "created_by": "Insp. B. Manjunath"
            },
            # Case 4
            {
                "id": 4,
                "title": "Operation Blackout - Western Regional Grid Sabotage",
                "description": "Multi-jurisdiction cyber-physical attack targeting western Maharashtra regional distribution SCADA telemetry networks. Investigating PLC firmware compromise and unauthorized relay trip commands.",
                "status": "Active",
                "created_by": "Cyber Cell STF"
            },
            # Case 5
            {
                "id": 5,
                "title": "Central Bureau of Investigation vs. Rajesh Talwar & Nupur Talwar (Aarushi Talwar Double Murder Case)",
                "description": "High-profile CBI investigation into the double homicide of 14-year-old Aarushi Talwar and 45-year-old domestic helper Hemraj Banjade at Jalvayu Vihar, Noida. Landmark forensic and circumstantial evidence case.",
                "status": "Closed",
                "created_by": "CBI Special Crime Unit"
            },
            # Case 6
            {
                "id": 6,
                "title": "United States vs. Dzhokhar Tsarnaev (Boston Marathon Bombing Investigation)",
                "description": "Federal multi-agency counter-terrorism investigation into dual improvised pressure-cooker explosive devices detonated near the Boston Marathon finish line on Boylston Street.",
                "status": "Closed",
                "created_by": "Joint Terrorism Task Force"
            }
        ]

        created_cases = {}
        for c in cases_data:
            case_obj = Case(
                id=c["id"],
                title=c["title"],
                description=c["description"],
                status=c["status"],
                created_by=c["created_by"]
            )
            db.add(case_obj)
            db.commit()
            db.refresh(case_obj)
            created_cases[c["id"]] = case_obj
            print(f"[OK] Seeded Case #{case_obj.id}: {case_obj.title[:55]}...")

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 1 (Nayana Pujari)
        # -------------------------------------------------------------
        c1 = created_cases[1]
        ev_c1_1 = Evidence(
            case_id=c1.id,
            file_name="ATM_CCTV_Footage_Yerwada.mp4",
            file_type="Video",
            file_size=24500000,
            storage_path="uploads/sample_atm_cctv.mp4",
            uploaded_by="PI Kishor Mhaswade",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Yerwada SBI ATM footage timestamped 21:42:15 on 07-Oct-2009. Two males observed using victim Nayana Pujari ATM card. White Toyota Qualis cab visible at street curb.",
            source="State Bank of India Yerwada ATM CCTV Feed"
        )
        ev_c1_2 = Evidence(
            case_id=c1.id,
            file_name="CDR_CellTower_Dump_Kharadi.pdf",
            file_type="Document",
            file_size=1200000,
            storage_path="uploads/sample_cdr_dump.pdf",
            uploaded_by="PI Kishor Mhaswade",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Cell tower logs near Kharadi bypass show 3 mobile IMEI numbers co-locating between 20:30 and 22:15. Tower handoffs recorded towards Rajgurunagar route.",
            source="Vodafone & Airtel Telecom Tower CDR"
        )
        ev_c1_3 = Evidence(
            case_id=c1.id,
            file_name="Qualis_Cab_Forensic_Report.pdf",
            file_type="Document",
            file_size=3400000,
            storage_path="uploads/qualis_forensics.pdf",
            uploaded_by="Forensic SIT Team",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Forensic search of Toyota Qualis MH-12-AQ-4411 recovered biological trace blood matching victim's profile and hair strands on rear seat upholstery.",
            source="State Forensic Science Laboratory Pune"
        )
        ev_c1_4 = Evidence(
            case_id=c1.id,
            file_name="Approver_Confession_Sec164.pdf",
            file_type="Document",
            file_size=890000,
            storage_path="uploads/approver_confession.pdf",
            uploaded_by="Magistrate Judicial Officer",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Statement recorded under Section 164 CrPC by approver Rajesh Chaudhari detailing vehicle movements, abduction from Kharadi, and role of Yogesh Raut.",
            source="Judicial Magistrate First Class Pune Court"
        )
        db.add_all([ev_c1_1, ev_c1_2, ev_c1_3, ev_c1_4])
        db.commit()

        # Entities Case 1
        db.add_all([
            Entity(case_id=c1.id, evidence_id=ev_c1_1.id, type="Suspect", name="Yogesh Raut", confidence=0.98),
            Entity(case_id=c1.id, evidence_id=ev_c1_1.id, type="Suspect", name="Mahesh Thakur", confidence=0.96),
            Entity(case_id=c1.id, evidence_id=ev_c1_1.id, type="Suspect", name="Vishwas Kadam", confidence=0.94),
            Entity(case_id=c1.id, evidence_id=ev_c1_4.id, type="Approver", name="Rajesh Chaudhari", confidence=0.99),
            Entity(case_id=c1.id, evidence_id=ev_c1_1.id, type="Victim", name="Nayana Pujari", confidence=1.0),
            Entity(case_id=c1.id, evidence_id=ev_c1_3.id, type="Vehicle", name="Toyota Qualis (MH-12-AQ-4411)", confidence=0.97),
            Entity(case_id=c1.id, evidence_id=ev_c1_1.id, type="Location", name="SBI ATM, Yerwada, Pune", confidence=0.99),
            Entity(case_id=c1.id, evidence_id=ev_c1_2.id, type="Location", name="Kharadi Bypass, Pune", confidence=0.95),
        ])
        # Events Case 1
        db.add_all([
            Event(case_id=c1.id, evidence_id=ev_c1_2.id, timestamp=datetime(2009, 10, 7, 20, 15, 0), title="Victim Leaves Synechron Office", description="Nayana Pujari departs Synechron Kharadi office waiting for transport at bypass.", location="Kharadi, Pune", confidence=0.99),
            Event(case_id=c1.id, evidence_id=ev_c1_1.id, timestamp=datetime(2009, 10, 7, 21, 42, 15), title="Unauthorized ATM Cash Withdrawal", description="Victim debit card used to withdraw Rs. 20,000 at Yerwada SBI ATM.", location="Yerwada, Pune", confidence=0.98),
            Event(case_id=c1.id, evidence_id=ev_c1_3.id, timestamp=datetime(2009, 10, 8, 2, 30, 0), title="Vehicle Identified at Toll Plaza", description="Toyota Qualis captured on Khed Shivapur toll camera moving towards Rajgurunagar.", location="Khed, Maharashtra", confidence=0.94),
            Event(case_id=c1.id, evidence_id=ev_c1_4.id, timestamp=datetime(2009, 10, 16, 11, 0, 0), title="Arrest of Primary Accused", description="Pune Police Crime Branch apprehends driver Yogesh Raut and accomplices.", location="Pune, Maharashtra", confidence=1.0)
        ])
        db.commit()

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 2 (Cyber Heist)
        # -------------------------------------------------------------
        c2 = created_cases[2]
        ev_c2_1 = Evidence(
            case_id=c2.id,
            file_name="Firewall_Packet_Capture_Pcap.pcap",
            file_type="Document",
            file_size=45000000,
            storage_path="uploads/cyber_firewall_pcap.pcap",
            uploaded_by="PI Vikram Salunkhe",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Wireshark PCAP log showing outbound SSH tunneling on port 443 towards Frankfurt IP 185.220.101.5. 42GB archive file payload transferred via AES-encrypted stream.",
            source="TechAxis Perimeter Cisco ASA Firewall"
        )
        ev_c2_2 = Evidence(
            case_id=c2.id,
            file_name="Server_RAM_Memory_Dump.raw",
            file_type="Document",
            file_size=16000000,
            storage_path="uploads/cyber_ram_dump.raw",
            uploaded_by="Cyber Forensics Examiner",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Volatility 3 memory analysis identified Cobalt Strike beacon executing inside svchost.exe PID 4192. Clear-text Bitcoin ransom wallet address extracted from memory string.",
            source="Production Database Server Host DC-01"
        )
        ev_c2_3 = Evidence(
            case_id=c2.id,
            file_name="Extortion_Ransom_Note.txt",
            file_type="Document",
            file_size=24000,
            storage_path="uploads/ransom_note.txt",
            uploaded_by="PI Vikram Salunkhe",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Extortion note left on root directory: 'Your financial proprietary code has been securely exfiltrated. Pay 15 BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa within 48 hours or face public leak.'",
            source="Compromised File Server Share"
        )
        db.add_all([ev_c2_1, ev_c2_2, ev_c2_3])
        db.commit()

        db.add_all([
            Entity(case_id=c2.id, evidence_id=ev_c2_2.id, type="ThreatActor", name="ShadowBroker-44", confidence=0.92),
            Entity(case_id=c2.id, evidence_id=ev_c2_1.id, type="IPAddress", name="185.220.101.5 (Frankfurt Exit Node)", confidence=0.98),
            Entity(case_id=c2.id, evidence_id=ev_c2_3.id, type="CryptoWallet", name="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", confidence=0.99),
            Entity(case_id=c2.id, evidence_id=ev_c2_2.id, type="Malware", name="Cobalt Strike Beacon (v4.8)", confidence=0.95),
            Entity(case_id=c2.id, evidence_id=ev_c2_1.id, type="Organization", name="TechAxis Solutions Pune", confidence=1.0)
        ])
        db.add_all([
            Event(case_id=c2.id, evidence_id=ev_c2_1.id, timestamp=datetime(2024, 2, 14, 2, 14, 0), title="Initial Perimeter Breach", description="Compromised VPN credentials used to bypass MFA from unauthorized foreign subnet.", location="TechAxis Server Room", confidence=0.97),
            Event(case_id=c2.id, evidence_id=ev_c2_2.id, timestamp=datetime(2024, 2, 14, 3, 45, 0), title="Lateral Movement & Memory Injection", description="Adversary elevates privileges to Domain Admin using Pass-the-Hash vulnerability.", location="DC-01 Domain Controller", confidence=0.94),
            Event(case_id=c2.id, evidence_id=ev_c2_1.id, timestamp=datetime(2024, 2, 14, 4, 30, 0), title="Exfiltration of Proprietary Algorithms", description="42GB database compressed and piped out over encrypted tunnel.", location="Cloud Backup Cluster", confidence=0.99),
            Event(case_id=c2.id, evidence_id=ev_c2_3.id, timestamp=datetime(2024, 2, 14, 6, 0, 0), title="Extortion Demands Received", description="CEO and Security Officer receive email containing sample leaked code and BTC ransom note.", location="Executive Mail Gateway", confidence=1.0)
        ])
        db.commit()

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 3 (Indiranagar Homicide)
        # -------------------------------------------------------------
        c3 = created_cases[3]
        ev_c3_1 = Evidence(
            case_id=c3.id,
            file_name="Latent_Fingerprint_Card_EntryDoor.jpg",
            file_type="Image",
            file_size=4200000,
            storage_path="uploads/fingerprint_door.jpg",
            uploaded_by="Insp. B. Manjunath",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="AFIS automated match returns 12-point ridge correlation against known repeat burglary offender Ramesh K. Print lifted from sliding balcony latch.",
            source="Bengaluru Fingerprint Bureau Crime Kit"
        )
        ev_c3_2 = Evidence(
            case_id=c3.id,
            file_name="Apartment_Gated_CCTV_Recording.mp4",
            file_type="Video",
            file_size=38000000,
            storage_path="uploads/gate_cctv.mp4",
            uploaded_by="Insp. B. Manjunath",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="CCTV camera 04 shows silver hatchback without front registration plate exiting gate at 02:47 AM on 15-Nov-2023.",
            source="Palm Meadows Gated Security DVR"
        )
        ev_c3_3 = Evidence(
            case_id=c3.id,
            file_name="Pawnshop_Recovery_Voucher.pdf",
            file_type="Document",
            file_size=620000,
            storage_path="uploads/pawn_voucher.pdf",
            uploaded_by="Investigating Officer",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Recovery of 480 grams 22k engraved gold bangles matching deceased owner inventory from Muthoot pawn counter in Shivajinagar.",
            source="Commercial Tax & Police Recovery Seizure Memo"
        )
        db.add_all([ev_c3_1, ev_c3_2, ev_c3_3])
        db.commit()

        db.add_all([
            Entity(case_id=c3.id, evidence_id=ev_c3_1.id, type="Suspect", name="Ramesh K. (Alias Bullet)", confidence=0.96),
            Entity(case_id=c3.id, evidence_id=ev_c3_2.id, type="Vehicle", name="Silver Hyundai Accent (Numberplate masked)", confidence=0.89),
            Entity(case_id=c3.id, evidence_id=ev_c3_3.id, type="RecoveredItem", name="480g Engraved Gold Bangles", confidence=0.99),
            Entity(case_id=c3.id, evidence_id=ev_c3_1.id, type="Location", name="100ft Road, Indiranagar, Bengaluru", confidence=1.0)
        ])
        db.add_all([
            Event(case_id=c3.id, evidence_id=ev_c3_2.id, timestamp=datetime(2023, 11, 15, 1, 30, 0), title="Premises Infiltration", description="Perpetrators breach rear balcony boundary wall avoiding street cameras.", location="Indiranagar 100ft Road", confidence=0.93),
            Event(case_id=c3.id, evidence_id=ev_c3_1.id, timestamp=datetime(2023, 11, 15, 2, 10, 0), title="Fatal Physical Confrontation", description="Resident awakens during locker tampering; fatal head trauma inflicted with crowbar.", location="Master Bedroom Suite", confidence=0.98),
            Event(case_id=c3.id, evidence_id=ev_c3_2.id, timestamp=datetime(2023, 11, 15, 2, 47, 0), title="Perpetrators Flee in Vehicle", description="Silver hatchback leaves via side alley towards Old Madras Road.", location="Indiranagar Gate", confidence=0.91),
            Event(case_id=c3.id, evidence_id=ev_c3_3.id, timestamp=datetime(2023, 11, 17, 16, 20, 0), title="Attempted Pledging of Stolen Ornaments", description="Associate attempts to pledge gold bangles using forged Aadhaar card; alert jeweler notifies control room.", location="Shivajinagar Pawn Shop", confidence=0.99)
        ])
        db.commit()

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 4 (Operation Blackout)
        # -------------------------------------------------------------
        c4 = created_cases[4]
        ev_c4_1 = Evidence(
            case_id=c4.id,
            file_name="SCADA_Modbus_Telemetry_Capture.pcap",
            file_type="Document",
            file_size=28000000,
            storage_path="uploads/scada_modbus.pcap",
            uploaded_by="Cyber Cell STF",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Industrial protocol capture identifies unauthorized Function Code 0x05 (Write Single Coil) sent to Siemens S7-300 breaker relays at 400kV Kalwa substation.",
            source="State Load Despatch Centre (SLDC) Airoli"
        )
        ev_c4_2 = Evidence(
            case_id=c4.id,
            file_name="Substation_PLC_Firmware_Binary.bin",
            file_type="Document",
            file_size=8200000,
            storage_path="uploads/plc_firmware.bin",
            uploaded_by="CERT-In Forensic Division",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Disassembly reveals rogue trojanized bootloader injecting false frequency measurements into SCADA telemetry bus, inducing automatic trip.",
            source="Kalwa 400kV Substation Terminal Rack 3"
        )
        db.add_all([ev_c4_1, ev_c4_2])
        db.commit()

        db.add_all([
            Entity(case_id=c4.id, evidence_id=ev_c4_2.id, type="ThreatActor", name="APT-X (Sandworm Affiliate)", confidence=0.88),
            Entity(case_id=c4.id, evidence_id=ev_c4_1.id, type="TargetInfrastructure", name="Kalwa 400kV Grid Substation", confidence=1.0),
            Entity(case_id=c4.id, evidence_id=ev_c4_2.id, type="MalwareVariant", name="Industroyer.V2 Modular Payload", confidence=0.94),
            Entity(case_id=c4.id, evidence_id=ev_c4_1.id, type="Facility", name="Western Regional SLDC Airoli", confidence=0.99)
        ])
        db.add_all([
            Event(case_id=c4.id, evidence_id=ev_c4_1.id, timestamp=datetime(2024, 1, 10, 8, 25, 0), title="Spear Phishing of Dispatch Operator", description="Weaponized macro spreadsheet opened on terminal workstation in transmission wing.", location="Airoli SLDC Operations", confidence=0.96),
            Event(case_id=c4.id, evidence_id=ev_c4_2.id, timestamp=datetime(2024, 1, 10, 9, 45, 0), title="Firmware Flashing via OT Bridge", description="Rogue firmware pushed across air-gap maintenance jumper onto primary bus PLC.", location="Kalwa Rack 3", confidence=0.92),
            Event(case_id=c4.id, evidence_id=ev_c4_1.id, timestamp=datetime(2024, 1, 10, 10, 12, 0), title="Cascade Trip & Regional Blackout", description="Unscheduled disconnect of 1200MW corridor results in tripping of suburban railway feeder circuits.", location="Mumbai Metropolitan Corridor", confidence=0.99)
        ])
        db.commit()

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 5 (Aarushi Talwar)
        # -------------------------------------------------------------
        c5 = created_cases[5]
        ev_c5_1 = Evidence(
            case_id=c5.id,
            file_name="Forensic_BedSheet_BloodPattern.jpg",
            file_type="Image",
            file_size=3200000,
            storage_path="uploads/aarushi_bedsheet.jpg",
            uploaded_by="CBI Special Crime Unit",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="High-velocity blood spatter analysis indicates blunt-force trauma inflicted while victim was lying supine on mattress, followed by incised neck wound.",
            source="Central Forensic Science Laboratory New Delhi"
        )
        ev_c5_2 = Evidence(
            case_id=c5.id,
            file_name="Scotch_Bottle_Fingerprint_Report.pdf",
            file_type="Document",
            file_size=1100000,
            storage_path="uploads/scotch_bottle.pdf",
            uploaded_by="CBI Special Crime Unit",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Ballantine's Scotch whiskey bottle recovered from dining table revealed smudged latent fingerprints with mixed DNA profiles.",
            source="CFSL Physics & Chemistry Wing"
        )
        db.add_all([ev_c5_1, ev_c5_2])
        db.commit()

        db.add_all([
            Entity(case_id=c5.id, evidence_id=ev_c5_1.id, type="Victim", name="Aarushi Talwar", confidence=1.0),
            Entity(case_id=c5.id, evidence_id=ev_c5_1.id, type="Victim", name="Hemraj Banjade", confidence=1.0),
            Entity(case_id=c5.id, evidence_id=ev_c5_2.id, type="PersonOfInterest", name="Dr. Rajesh Talwar", confidence=0.95),
            Entity(case_id=c5.id, evidence_id=ev_c5_2.id, type="PersonOfInterest", name="Dr. Nupur Talwar", confidence=0.95),
            Entity(case_id=c5.id, evidence_id=ev_c5_1.id, type="Location", name="Flat L-32, Jalvayu Vihar, Noida", confidence=1.0)
        ])
        db.add_all([
            Event(case_id=c5.id, evidence_id=ev_c5_1.id, timestamp=datetime(2008, 5, 15, 23, 30, 0), title="Last Seen Alive", description="Aarushi Talwar last seen in her bedroom prior to parents retiring to sleep.", location="Flat L-32, Jalvayu Vihar", confidence=0.98),
            Event(case_id=c5.id, evidence_id=ev_c5_1.id, timestamp=datetime(2008, 5, 16, 6, 0, 0), title="Discovery of Aarushi Talwar", description="Domestic help and parents discover Aarushi deceased in bedroom; initial suspicion falls on missing helper Hemraj.", location="Aarushi Bedroom", confidence=1.0),
            Event(case_id=c5.id, evidence_id=ev_c5_2.id, timestamp=datetime(2008, 5, 17, 10, 15, 0), title="Discovery of Hemraj Body on Terrace", description="Hemraj body discovered on locked terrace with matching blunt force trauma and cut wounds.", location="Terrace L-32", confidence=1.0)
        ])
        db.commit()

        # -------------------------------------------------------------
        # EVIDENCE, ENTITIES, EVENTS FOR CASE 6 (Boston Marathon)
        # -------------------------------------------------------------
        c6 = created_cases[6]
        ev_c6_1 = Evidence(
            case_id=c6.id,
            file_name="Lord_And_Taylor_Surveillance_Video.mp4",
            file_type="Video",
            file_size=64000000,
            storage_path="uploads/boston_cctv.mp4",
            uploaded_by="Joint Terrorism Task Force",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Surveillance camera footage from Boylston Street showing suspect in white baseball cap placing heavy black knapsack on sidewalk near Forum restaurant.",
            source="FBI Boston Evidence Response Team"
        )
        ev_c6_2 = Evidence(
            case_id=c6.id,
            file_name="Pressure_Cooker_Metallurgy_Report.pdf",
            file_type="Document",
            file_size=2100000,
            storage_path="uploads/pressure_cooker.pdf",
            uploaded_by="FBI Laboratory Quantico",
            processing_status=EvidenceStatus.ANALYZED,
            extracted_text="Fragment analysis confirmed Fagor 6-quart pressure cooker fragments, steel BBs, and roofing nail shrapnel powered by low-order pyrotechnic propellant.",
            source="FBI Explosives Unit"
        )
        db.add_all([ev_c6_1, ev_c6_2])
        db.commit()

        db.add_all([
            Entity(case_id=c6.id, evidence_id=ev_c6_1.id, type="Suspect", name="Dzhokhar Tsarnaev (Suspect 2)", confidence=0.99),
            Entity(case_id=c6.id, evidence_id=ev_c6_1.id, type="Suspect", name="Tamerlan Tsarnaev (Suspect 1)", confidence=0.99),
            Entity(case_id=c6.id, evidence_id=ev_c6_2.id, type="Device", name="Fagor 6-Quart Pressure Cooker IED", confidence=0.98),
            Entity(case_id=c6.id, evidence_id=ev_c6_1.id, type="Location", name="Boylston Street, Boston, MA", confidence=1.0)
        ])
        db.add_all([
            Event(case_id=c6.id, evidence_id=ev_c6_1.id, timestamp=datetime(2013, 4, 15, 14, 49, 43), title="Detonation of First IED", description="First device detonates outside Marathon Sports on Boylston Street.", location="Boylston Street, Boston", confidence=1.0),
            Event(case_id=c6.id, evidence_id=ev_c6_1.id, timestamp=datetime(2013, 4, 15, 14, 49, 57), title="Detonation of Second IED", description="Second device detonates one block west outside Forum Restaurant.", location="Boylston Street, Boston", confidence=1.0),
            Event(case_id=c6.id, evidence_id=ev_c6_2.id, timestamp=datetime(2013, 4, 19, 20, 45, 0), title="Apprehension of Surviving Suspect", description="Dzhokhar Tsarnaev taken into federal custody following boat standoff in Watertown.", location="Watertown, MA", confidence=1.0)
        ])
        db.commit()

        total_ev = db.query(Evidence).count()
        total_ent = db.query(Entity).count()
        total_evnt = db.query(Event).count()
        print(f"\n[SUCCESS] Successfully seeded 6 Cases, {total_ev} Evidence exhibits, {total_ent} Entities, and {total_evnt} Timeline events!")

    finally:
        db.close()

if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed(force=force_seed)
