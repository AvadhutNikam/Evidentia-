"""
backend/police_case_file_engine.py
==================================
Core operational engine for Police Case File architecture:
1. Document Type Registry & Gap Verification Engine (10 Standard Police Memos).
2. Case Diary (Section 192 BNSS / 172 CrPC) Auto-Drafting from Audit Trail.
3. Statement Improvement & Contradiction Analyzer (Section 145 / 162 CrPC).
4. Penal Sections Register (BNS & IPC) & Element-by-Element Proof Matrix.
5. Per-Accused Statutory Remand & Default Bail Clocks.
"""

import json
import hashlib
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Case, Evidence, AuditLog, User, PoliceStationLookup, CasePerson,
    AccusedStatusHistory, PersonStatement, DocumentTypeDefinition,
    CaseDiaryEntry, CaseSection, SectionElement, CaseDeadline
)
from procedure_engine import recalculate_case_deadlines
from audit_engine import log_audit_event

# ==============================================================================
# 1. DOCUMENT TYPE DEFINITIONS REGISTRY & GAP ENGINE
# ==============================================================================

STANDARD_DOCUMENT_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "code": "fir",
        "label": "First Information Report (FIR)",
        "legal_provision": "Section 173 BNSS / Section 154 CrPC",
        "category": "investigation",
        "standard_guidance": "Official registration of cognizable offence initiating police investigation.",
        "required_fields": [
            {"key": "fir_number", "label": "FIR Number", "type": "string", "required": True},
            {"key": "police_station", "label": "Police Station", "type": "string", "required": True},
            {"key": "date_time_reported", "label": "Date & Time Reported", "type": "datetime", "required": True},
            {"key": "date_time_incident", "label": "Date & Time of Occurrence", "type": "datetime", "required": True},
            {"key": "place_of_occurrence", "label": "Place of Occurrence / Distance from PS", "type": "string", "required": True},
            {"key": "informant_name", "label": "Complainant / Informant Full Name", "type": "string", "required": True},
            {"key": "acts_and_sections", "label": "Acts and Sections Applied", "type": "string", "required": True},
            {"key": "general_diary_ref", "label": "General Diary (GD/Sanha) Reference", "type": "string", "required": True},
            {"key": "delay_reason", "label": "Reason for Delay in Reporting (if any)", "type": "string", "required": False}
        ]
    },
    {
        "code": "spot_panchnama",
        "label": "Spot Panchnama (Scene of Crime Inspection)",
        "legal_provision": "Section 185 BNSS / Section 100 CrPC",
        "category": "panchnama",
        "standard_guidance": "Contemporaneous record of crime scene physical features in presence of independent panch witnesses.",
        "required_fields": [
            {"key": "scene_address", "label": "Exact Crime Scene Location / Landmarks", "type": "string", "required": True},
            {"key": "inspection_start_time", "label": "Inspection Commencement Time", "type": "datetime", "required": True},
            {"key": "inspection_end_time", "label": "Inspection Conclusion Time", "type": "datetime", "required": True},
            {"key": "panch_witness_1_name", "label": "First Independent Panch Witness Name", "type": "string", "required": True},
            {"key": "panch_witness_2_name", "label": "Second Independent Panch Witness Name", "type": "string", "required": True},
            {"key": "physical_features_observed", "label": "Physical Condition / Ingress & Egress", "type": "text", "required": True},
            {"key": "sketches_prepared", "label": "Rough Scene Sketch / Map Drawn", "type": "boolean", "required": True},
            {"key": "blood_stains_observed", "label": "Presence of Blood Stains / Biological Marks", "type": "boolean", "required": True},
            {"key": "panch_signatures_obtained", "label": "Signatures of Both Panch Witnesses Obtained", "type": "boolean", "required": True}
        ]
    },
    {
        "code": "seizure_memo",
        "label": "Property Seizure Memo (Panchnama of Seizure)",
        "legal_provision": "Section 105 BNSS / Section 102 CrPC",
        "category": "panchnama",
        "standard_guidance": "Mandatory recovery memo detailing exact articles seized, sealed on spot with specimen seal impression.",
        "required_fields": [
            {"key": "seized_from_person_or_place", "label": "Seized From (Person Name / Location)", "type": "string", "required": True},
            {"key": "seizure_date_time", "label": "Date and Time of Seizure", "type": "datetime", "required": True},
            {"key": "seizing_officer", "label": "Seizing Officer Name & Rank", "type": "string", "required": True},
            {"key": "panch_witness_1_name", "label": "Panch Witness 1 Name", "type": "string", "required": True},
            {"key": "panch_witness_2_name", "label": "Panch Witness 2 Name", "type": "string", "required": True},
            {"key": "item_description", "label": "Complete Item Description & Markings", "type": "text", "required": True},
            {"key": "quantity", "label": "Quantity / Weight / Dimension", "type": "string", "required": True},
            {"key": "seal_impression_number", "label": "Specimen Seal Impression Number / Lacquer Seal", "type": "string", "required": True},
            {"key": "malkhana_entry_number", "label": "Malkhana Register Inward Number", "type": "string", "required": False}
        ]
    },
    {
        "code": "arrest_memo",
        "label": "Memo of Arrest & Inspection Memo",
        "legal_provision": "Section 35 BNSS / Section 41B CrPC (D.K. Basu Guidelines)",
        "category": "custody",
        "standard_guidance": "Strict constitutional safeguards: intimation of grounds, intimation to relative, medical checkup.",
        "required_fields": [
            {"key": "arrestee_name", "label": "Arrestee Legal Name", "type": "string", "required": True},
            {"key": "arrest_date_time", "label": "Date and Exact Time of Arrest", "type": "datetime", "required": True},
            {"key": "arrest_location", "label": "Exact Place of Arrest", "type": "string", "required": True},
            {"key": "arresting_officer", "label": "Arresting Officer Name, Rank & Station", "type": "string", "required": True},
            {"key": "grounds_of_arrest_communicated", "label": "Written Grounds of Arrest Communicated to Accused", "type": "boolean", "required": True},
            {"key": "relative_or_friend_informed", "label": "Relative / Nominated Friend Intimated", "type": "boolean", "required": True},
            {"key": "relative_name_and_contact", "label": "Name & Contact of Person Informed", "type": "string", "required": True},
            {"key": "medical_examination_done", "label": "Medical Examination Conducted (Sec 54 CrPC)", "type": "boolean", "required": True},
            {"key": "medical_officer_name", "label": "Examining Medical Officer / Civil Hospital", "type": "string", "required": True},
            {"key": "arrestee_signature_obtained", "label": "Arrestee Signature / Thumb Impression Obtained", "type": "boolean", "required": True},
            {"key": "attesting_witness_name", "label": "Attesting Witness / Respected Inhabitant", "type": "string", "required": True}
        ]
    },
    {
        "code": "medico_legal_certificate",
        "label": "Medico-Legal Certificate (MLC)",
        "legal_provision": "Section 51 & 52 BNSS / Section 53 & 54 CrPC",
        "category": "medico_legal",
        "standard_guidance": "Clinical examination of injured victim or accused by certified medical practitioner.",
        "required_fields": [
            {"key": "hospital_name", "label": "Hospital / Government Medical College", "type": "string", "required": True},
            {"key": "examining_doctor", "label": "Examining Doctor Name & Reg No.", "type": "string", "required": True},
            {"key": "examined_date_time", "label": "Examination Date & Time", "type": "datetime", "required": True},
            {"key": "injuries_detailed", "label": "Detailed Anatomical Injury Description", "type": "text", "required": True},
            {"key": "age_of_injuries", "label": "Estimated Age of Injuries", "type": "string", "required": True},
            {"key": "weapon_category_suggested", "label": "Weapon Type (Blunt, Sharp, Firearm, Burn)", "type": "string", "required": True},
            {"key": "sobriety_opinion", "label": "Evidence of Alcohol / Intoxication", "type": "string", "required": False}
        ]
    },
    {
        "code": "post_mortem_report",
        "label": "Post-Mortem Examination Report (Autopsy)",
        "legal_provision": "Section 196 BNSS / Section 174 CrPC",
        "category": "medico_legal",
        "standard_guidance": "Inquest autopsy report establishing cause, mechanism, and approximate time since death.",
        "required_fields": [
            {"key": "autopsy_number", "label": "Post-Mortem / Autopsy Number", "type": "string", "required": True},
            {"key": "performing_surgeon", "label": "Forensic Medicine Specialist / Surgeon Name", "type": "string", "required": True},
            {"key": "examination_date_time", "label": "Autopsy Date & Time", "type": "datetime", "required": True},
            {"key": "cause_of_death", "label": "Conclusive / Probable Cause of Death", "type": "text", "required": True},
            {"key": "time_since_death", "label": "Estimated Time Since Death", "type": "string", "required": True},
            {"key": "viscera_preserved", "label": "Viscera Samples Preserved for Chemical Analysis", "type": "boolean", "required": True},
            {"key": "viscera_forwarded_to_fsl", "label": "Viscera Bottle Forwarded to FSL", "type": "boolean", "required": True},
            {"key": "antemortem_vs_postmortem_injuries", "label": "Antemortem vs Postmortem Injuries Delineated", "type": "text", "required": True}
        ]
    },
    {
        "code": "inquest_report",
        "label": "Inquest Panchnama (Dead Body Inspection)",
        "legal_provision": "Section 194 BNSS / Section 174 CrPC",
        "category": "panchnama",
        "standard_guidance": "Immediate scene inspection of deceased body by Executive Magistrate or Police Officer in presence of panchas.",
        "required_fields": [
            {"key": "inquest_officer", "label": "Inquest Conducting Officer Name & Rank", "type": "string", "required": True},
            {"key": "body_found_location", "label": "Exact Location Where Body Was Discovered", "type": "string", "required": True},
            {"key": "body_position", "label": "Position and State of Body", "type": "text", "required": True},
            {"key": "panch_witness_1", "label": "First Inquest Panch Name", "type": "string", "required": True},
            {"key": "panch_witness_2", "label": "Second Inquest Panch Name", "type": "string", "required": True},
            {"key": "apparent_cause_of_death", "label": "Apparent Cause / Manner of Death Observed", "type": "text", "required": True},
            {"key": "body_forwarded_for_autopsy_officer", "label": "Constable Escorting Body to Mortuary", "type": "string", "required": True}
        ]
    },
    {
        "code": "fsl_request",
        "label": "Forensic Laboratory Requisition (Forwarding Memo)",
        "legal_provision": "Section 52 & 329 BNSS / Section 53A CrPC",
        "category": "technical",
        "standard_guidance": "Official police forwarding memo sending physical exhibits to State FSL under intact seal.",
        "required_fields": [
            {"key": "fsl_lab_name", "label": "Target Forensic Science Laboratory (e.g. FSL Kalina)", "type": "string", "required": True},
            {"key": "forwarding_letter_number", "label": "Forwarding Letter / Outward Number", "type": "string", "required": True},
            {"key": "dispatch_date", "label": "Date of Dispatch", "type": "datetime", "required": True},
            {"key": "samples_listed", "label": "List of Parcel Samples & Parcel Marks", "type": "text", "required": True},
            {"key": "seal_intact_certificate", "label": "Certificate of Specimen Seal Intactness", "type": "boolean", "required": True},
            {"key": "specific_tests_requested", "label": "Specific Forensic Tests Requested (DNA, Ballistics, Toxicology)", "type": "text", "required": True}
        ]
    },
    {
        "code": "fsl_report",
        "label": "Forensic Science Laboratory (FSL) Final Analysis",
        "legal_provision": "Section 329 BNSS / Section 293 CrPC",
        "category": "technical",
        "standard_guidance": "Admissible scientific expert report signed by government scientific expert under Section 293 CrPC.",
        "required_fields": [
            {"key": "fsl_report_number", "label": "FSL Report / Directorate Dispatch Number", "type": "string", "required": True},
            {"key": "reporting_scientist", "label": "Reporting Scientist Name & Division", "type": "string", "required": True},
            {"key": "report_date", "label": "Date of Analysis Report", "type": "datetime", "required": True},
            {"key": "results_summary", "label": "Scientific Findings & Conclusive Opinion", "type": "text", "required": True},
            {"key": "specimen_returned", "label": "Remnant Evidence Parcels Sealed & Returned", "type": "boolean", "required": True}
        ]
    },
    {
        "code": "section_65b_certificate",
        "label": "Electronic Record Certificate (Sec 65B IEA / 63 BSA)",
        "legal_provision": "Section 63 Bharatiya Sakshya Adhiniyam / Section 65B Indian Evidence Act",
        "category": "technical",
        "standard_guidance": "Mandatory admissibility certificate for electronic evidence (CCTV, CDR, WhatsApp, emails, server logs).",
        "required_fields": [
            {"key": "certifying_person_name", "label": "Person in Lawful Management of Device Name", "type": "string", "required": True},
            {"key": "certifying_person_designation", "label": "Designation / Official Capacity", "type": "string", "required": True},
            {"key": "device_make_model", "label": "Source Computer / Server / DVR Device Spec", "type": "string", "required": True},
            {"key": "source_media_description", "label": "Output Media Description (Hard Disk, CD-R, Pen Drive)", "type": "string", "required": True},
            {"key": "hash_sha256_verified", "label": "Cryptographic Hash (SHA-256) Verified & Stated", "type": "boolean", "required": True},
            {"key": "lawful_custody_statement", "label": "Statement of Regular & Lawful Operation Affirmed", "type": "boolean", "required": True},
            {"key": "reproduction_accuracy_statement", "label": "Affirmation that Copy is Faithful Reproduction", "type": "boolean", "required": True}
        ]
    }
]


def ensure_document_type_definitions(db: Session) -> None:
    """Seeds document type definitions if not already present."""
    for definition in STANDARD_DOCUMENT_DEFINITIONS:
        existing = db.query(DocumentTypeDefinition).filter(
            DocumentTypeDefinition.code == definition["code"]
        ).first()
        if not existing:
            new_def = DocumentTypeDefinition(
                code=definition["code"],
                label=definition["label"],
                legal_provision=definition["legal_provision"],
                category=definition["category"],
                required_fields_json=json.dumps(definition["required_fields"]),
                standard_guidance=definition.get("standard_guidance")
            )
            db.add(new_def)
    db.commit()


def evaluate_document_completeness(
    doc_type_code: str,
    type_details_dict: Optional[Dict[str, Any]],
    db: Session
) -> Dict[str, Any]:
    """
    Evaluates completeness percentage and identifies missing mandatory elements
    against the formal DocumentTypeDefinition.
    """
    definition = db.query(DocumentTypeDefinition).filter(
        DocumentTypeDefinition.code == doc_type_code
    ).first()

    if not definition:
        return {
            "completeness_pct": 100.0,
            "is_complete": True,
            "missing_required_fields": [],
            "gap_reasons": [],
            "legal_guidance": "Standard document format"
        }

    try:
        fields = json.loads(definition.required_fields_json)
    except Exception:
        fields = []

    details = type_details_dict or {}
    required_fields = [f for f in fields if f.get("required", False)]
    total_required = len(required_fields)

    if total_required == 0:
        return {
            "completeness_pct": 100.0,
            "is_complete": True,
            "missing_required_fields": [],
            "gap_reasons": [],
            "legal_guidance": definition.standard_guidance
        }

    missing_fields = []
    gap_reasons = []
    satisfied_count = 0

    for f in required_fields:
        key = f["key"]
        val = details.get(key)
        # Check presence
        if val is None or val == "" or (isinstance(val, bool) and val is False):
            missing_fields.append({"key": key, "label": f["label"]})
            gap_reasons.append(f"Required element '{f['label']}' is not recorded.")
        else:
            satisfied_count += 1

    completeness_pct = round((satisfied_count / total_required) * 100, 1)
    is_complete = completeness_pct >= 100.0

    return {
        "completeness_pct": completeness_pct,
        "is_complete": is_complete,
        "missing_required_fields": missing_fields,
        "gap_reasons": gap_reasons,
        "legal_guidance": definition.standard_guidance or definition.legal_provision
    }


# ==============================================================================
# 2. POLICE STATIONS LOOKUP DIRECTORY
# ==============================================================================

SEED_POLICE_STATIONS = [
    {"name": "Yerwada Police Station", "district": "Pune City", "state": "Maharashtra", "station_code": "PUN-YER-01", "sp_office": "DCP Zone 4 Pune"},
    {"name": "Khadki Police Station", "district": "Pune City", "state": "Maharashtra", "station_code": "PUN-KHD-02", "sp_office": "DCP Zone 4 Pune"},
    {"name": "Bund Garden Police Station", "district": "Pune City", "state": "Maharashtra", "station_code": "PUN-BGD-03", "sp_office": "DCP Zone 2 Pune"},
    {"name": "Swargate Police Station", "district": "Pune City", "state": "Maharashtra", "station_code": "PUN-SWG-04", "sp_office": "DCP Zone 2 Pune"},
    {"name": "Hinjewadi Police Station", "district": "Pimpri-Chinchwad", "state": "Maharashtra", "station_code": "PCMC-HNJ-01", "sp_office": "DCP Zone 2 PCMC"},
    {"name": "Shivajinagar Police Station", "district": "Pune City", "state": "Maharashtra", "station_code": "PUN-SHV-05", "sp_office": "DCP Zone 1 Pune"},
    {"name": "Colaba Police Station", "district": "Mumbai City", "state": "Maharashtra", "station_code": "MUM-COL-01", "sp_office": "DCP Zone 1 Mumbai"},
    {"name": "Bandra Police Station", "district": "Mumbai Suburban", "state": "Maharashtra", "station_code": "MUM-BND-02", "sp_office": "DCP Zone 9 Mumbai"},
    {"name": "Sector 20 Police Station", "district": "Gautam Buddha Nagar", "state": "Uttar Pradesh", "station_code": "UP-NOI-01", "sp_office": "DCP Noida"}
]


def ensure_police_station_lookups(db: Session) -> None:
    """Seeds directory of police stations."""
    for st in SEED_POLICE_STATIONS:
        exists = db.query(PoliceStationLookup).filter(PoliceStationLookup.name == st["name"]).first()
        if not exists:
            db.add(PoliceStationLookup(**st))
    db.commit()


# ==============================================================================
# 3. CASE DIARY AUTO-DRAFTING (Section 192 BNSS / Section 172 CrPC)
# ==============================================================================

def generate_case_diary_auto_draft(
    case_id: int,
    entry_date: date,
    user: User,
    db: Session
) -> Dict[str, Any]:
    """
    Collects audit logs, exhibit uploads, witness statements, and custody events
    for the selected date, automatically synthesizing a draft Roznamcha entry.
    """
    start_dt = datetime(entry_date.year, entry_date.month, entry_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    # 1. Query audit logs for that calendar day
    logs = db.query(AuditLog).filter(
        AuditLog.case_id == case_id,
        AuditLog.timestamp >= start_dt,
        AuditLog.timestamp < end_dt
    ).order_by(AuditLog.timestamp.asc()).all()

    # 2. Query statements recorded on that day
    statements = db.query(PersonStatement).filter(
        PersonStatement.case_id == case_id,
        PersonStatement.statement_date >= start_dt,
        PersonStatement.statement_date < end_dt
    ).all()

    # 3. Query evidence uploaded on that day
    evidence_items = db.query(Evidence).filter(
        Evidence.case_id == case_id,
        Evidence.upload_date >= start_dt,
        Evidence.upload_date < end_dt,
        Evidence.is_deleted == False
    ).all()

    # 4. Query accused status changes
    accused_history = db.query(AccusedStatusHistory).filter(
        AccusedStatusHistory.case_id == case_id,
        AccusedStatusHistory.status_date >= start_dt,
        AccusedStatusHistory.status_date < end_dt
    ).all()

    # Determine serial number for the day
    existing_entries_count = db.query(CaseDiaryEntry).filter(
        CaseDiaryEntry.case_id == case_id,
        CaseDiaryEntry.entry_date == entry_date
    ).count()
    serial_number = existing_entries_count + 1

    # Formulate activities narrative
    activity_paragraphs = []
    time_prefix = "09:30 IST"

    if not logs and not statements and not evidence_items and not accused_history:
        activities = f"Investigation docket reviewed by {user.full_name or user.email}. Verification of case file records; case diary maintained pursuant to Section 192 BNSS."
        persons_examined = []
        places_visited = ["Police Station Investigation Room"]
        items_seized = []
    else:
        activities_list = []
        persons_examined = []
        places_visited = []
        items_seized = []

        for st in statements:
            person_name = st.person.name if st.person else f"Person #{st.person_id}"
            st_time = st.statement_time or "11:00 IST"
            sec_label = "Section 180 BNSS" if "180" in st.statement_type else "Section 183 BNSS" if "183" in st.statement_type else "Sec 161 CrPC"
            activities_list.append(f"At {st_time}, examined witness/accused {person_name} at {st.place or 'Police Station'} and recorded detailed statement under {sec_label}.")
            persons_examined.append({"person_id": st.person_id, "name": person_name, "type": st.statement_type})
            if st.place and st.place not in places_visited:
                places_visited.append(st.place)

        for ev in evidence_items:
            doc_type = ev.document_type or ev.evidence_type or "Physical Exhibit"
            activities_list.append(f"Ingested and sealed exhibit #{ev.id} ('{ev.file_name}') classified as {doc_type}. Source: {ev.collected_by or 'Investigating Team'}.")
            items_seized.append({"evidence_id": ev.id, "title": ev.file_name, "type": doc_type})

        for acc in accused_history:
            acc_name = acc.person.name if acc.person else f"Accused #{acc.person_id}"
            activities_list.append(f"Recorded custody update for {acc_name}: status changed to '{acc.status}' pursuant to order '{acc.order_reference or 'Court Order'}'.")

        for log in logs:
            act_type = (getattr(log, "action_type", "") or "").lower()
            if "override" in act_type or "evidence" in act_type:
                activities_list.append(f"Forensic audit: {log.description}.")

        activities = " \n".join(activities_list)
        if not places_visited:
            places_visited = ["Police Station Investigation Room"]

    return {
        "case_id": case_id,
        "entry_date": entry_date.isoformat(),
        "serial_number": serial_number,
        "time_from": "09:30",
        "time_to": "18:30",
        "place": places_visited[0] if places_visited else "Police Station",
        "officer_id": user.id,
        "officer_name": user.full_name or user.email,
        "activities": activities,
        "persons_examined_json": json.dumps(persons_examined),
        "places_visited_json": json.dumps(places_visited),
        "items_seized_json": json.dumps(items_seized),
        "instructions_given": "Pursue independent corroboration of telecommunication dumps and dispatch physical exhibits under intact seal to FSL.",
        "next_steps": "Record statements of remaining panch witnesses and produce accused before learned CJM Court for remand extension.",
        "status": "draft"
    }


def digitally_sign_diary_entry(entry: CaseDiaryEntry, user: User, db: Session) -> CaseDiaryEntry:
    """
    Digitally signs and locks a diary entry. Creates tamper-evident SHA-256 signature hash.
    Once locked, subsequent modifications are strictly rejected.
    """
    if entry.status == "signed" or entry.status == "locked":
        raise ValueError("Diary entry is already signed and locked.")

    now = datetime.now(timezone.utc)
    entry.signature_timestamp = now
    entry.status = "signed"

    # Compute digital signature hash over content
    raw_payload = f"{entry.case_id}:{entry.entry_date}:{entry.serial_number}:{entry.officer_name}:{entry.activities}:{now.isoformat()}"
    entry.signature_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    # Write to audit log
    log_audit_event(
        db=db,
        case_id=entry.case_id,
        user_id=user.id,
        user_name=user.full_name or user.email,
        action_type="CASE_DIARY_SIGNED",
        target_type="case_diary",
        target_id=str(entry.id),
        description=f"Case Diary Entry #{entry.serial_number} for date {entry.entry_date} digitally signed by {user.full_name or user.email} (Hash: {entry.signature_hash[:16]}...)",
        commit=False
    )
    db.commit()
    db.refresh(entry)
    return entry


# ==============================================================================
# 4. STATEMENT IMPROVEMENT & CONTRADICTION ANALYZER
# ==============================================================================

def analyze_person_statement_improvements(
    case_id: int,
    person_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Compares all recorded statements by the same person across dates.
    Detects additions (improvements), omissions, and discrepancies
    pursuant to Section 145 / 162 CrPC & Section 148 BSA cross-examination rules.
    """
    statements = db.query(PersonStatement).filter(
        PersonStatement.case_id == case_id,
        PersonStatement.person_id == person_id
    ).order_by(PersonStatement.statement_date.asc()).all()

    person = db.query(CasePerson).filter(CasePerson.id == person_id).first()
    person_name = person.name if person else f"Person #{person_id}"

    if len(statements) < 2:
        return {
            "person_id": person_id,
            "person_name": person_name,
            "has_comparisons": False,
            "statement_count": len(statements),
            "improvements": [],
            "omissions": [],
            "message": "At least two statements are required to perform an improvement and omission cross-analysis."
        }

    first_st = statements[0]
    second_st = statements[-1]

    # Extract claims or use text lines
    def extract_terms(st: PersonStatement):
        if st.key_claims:
            try:
                parsed = json.loads(st.key_claims)
                if isinstance(parsed, list):
                    return set(p.strip().lower() for p in parsed)
            except Exception:
                pass
        text = st.statement_text or st.notes or ""
        words = set(re_clean(w) for w in text.split() if len(w) > 4)
        return words

    def re_clean(w: str):
        return "".join(ch for ch in w.lower() if ch.isalnum())

    terms_1 = extract_terms(first_st)
    terms_2 = extract_terms(second_st)

    added_terms = list(terms_2 - terms_1)[:10]
    omitted_terms = list(terms_1 - terms_2)[:10]

    improvements = []
    if added_terms:
        improvements.append({
            "type": "addition_improvement",
            "earlier_statement_id": first_st.id,
            "earlier_date": first_st.statement_date.isoformat(),
            "later_statement_id": second_st.id,
            "later_date": second_st.statement_date.isoformat(),
            "description": f"Later statement contains {len(added_terms)} new assertions/terms not present in initial statement.",
            "terms": added_terms,
            "legal_note": "Significant additions made in subsequent statement may be challenged as an 'improved version' under Sec 145 Evidence Act."
        })

    omissions = []
    if omitted_terms:
        omissions.append({
            "type": "material_omission",
            "earlier_statement_id": first_st.id,
            "later_statement_id": second_st.id,
            "description": f"{len(omitted_terms)} points from initial statement were omitted in subsequent testimony.",
            "terms": omitted_terms,
            "legal_note": "Omission of crucial facts mentioned in early police statement amounts to contradiction if material."
        })

    return {
        "person_id": person_id,
        "person_name": person_name,
        "has_comparisons": True,
        "statement_count": len(statements),
        "first_statement": {
            "id": first_st.id,
            "type": first_st.statement_type,
            "date": first_st.statement_date.isoformat()
        },
        "latest_statement": {
            "id": second_st.id,
            "type": second_st.statement_type,
            "date": second_st.statement_date.isoformat()
        },
        "improvements": improvements,
        "omissions": omissions
    }


# ==============================================================================
# 5. PENAL SECTIONS & AUTOMATIC STATUTORY RECALCULATION
# ==============================================================================

# Standard BNS / IPC Mapping & Punishment Tiers
PENAL_SECTIONS_DATABASE = {
    "103(1)": {
        "act": "BNS",
        "ipc_equivalent": "302",
        "description": "Murder (Punishable with death or imprisonment for life and fine)",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Causing death of a human being",
            "Act done with intention of causing death or bodily injury sufficient in ordinary course of nature to cause death",
            "Absence of exceptions under Section 103 BNS (grave and sudden provocation, self-defense)"
        ]
    },
    "109": {
        "act": "BNS",
        "ipc_equivalent": "307",
        "description": "Attempt to Murder (Imprisonment up to 10 years / Life if hurt caused)",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Act done with intention or knowledge to cause death",
            "Act fell short of causing death",
            "Hurt caused to person by such act"
        ]
    },
    "64": {
        "act": "BNS",
        "ipc_equivalent": "376",
        "description": "Rape (Rigorous imprisonment not less than 10 years to life)",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Sexual assault committed against will / without consent",
            "Medical / DNA corroboration",
            "Absence of lawful consent"
        ]
    },
    "309": {
        "act": "BNS",
        "ipc_equivalent": "392",
        "description": "Robbery (Imprisonment up to 10 years / 14 years if on highway)",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Theft or extortion committed",
            "Wrongful restraint or fear of instant hurt or death caused intentionally",
            "Property removed from victim's possession"
        ]
    },
    "318": {
        "act": "BNS",
        "ipc_equivalent": "420",
        "description": "Cheating and dishonestly inducing delivery of property (Up to 7 years)",
        "punishment_tier": "under_10_years",
        "elements": [
            "Deception practiced upon victim",
            "Dishonest inducement to deliver property",
            "Causal connection between deception and property delivery"
        ]
    },
    "61": {
        "act": "BNS",
        "ipc_equivalent": "120B",
        "description": "Criminal Conspiracy (Punishable according to offence conspired)",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Agreement between two or more persons to do an illegal act",
            "Meeting of minds or common objective",
            "Overt act done in furtherance of conspiracy"
        ]
    },
    "3(5)": {
        "act": "BNS",
        "ipc_equivalent": "34",
        "description": "Joint liability / Acts done by several persons in furtherance of common intention",
        "punishment_tier": "life_or_death_over_10_years",
        "elements": [
            "Criminal act done by multiple persons",
            "Pre-arranged plan or common intention prior to act",
            "Active physical or coordinating participation in commission"
        ]
    }
}


def sync_case_sections_from_offence_text(case_id: int, db: Session) -> List[CaseSection]:
    """
    Parses existing offence_section string (e.g. 'IPC 302 / BNS 103') and populates
    case_sections and section_elements tables if empty.
    """
    existing_sections = db.query(CaseSection).filter(CaseSection.case_id == case_id).all()
    if existing_sections:
        return existing_sections

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return []

    offence_text = str(case.offence_section or "302, 34").lower()
    created = []

    # Map sections
    for sec_code, meta in PENAL_SECTIONS_DATABASE.items():
        ipc_eq = meta.get("ipc_equivalent", "")
        if sec_code.lower() in offence_text or (ipc_eq and ipc_eq in offence_text):
            cs = CaseSection(
                case_id=case_id,
                act=meta["act"],
                section_code=f"{sec_code} BNS / {ipc_eq} IPC" if ipc_eq else f"{sec_code} BNS",
                description=meta["description"],
                punishment_tier=meta["punishment_tier"],
                status="initial",
                reason="Initial section registered in FIR docket.",
                deciding_officer=getattr(case, "investigating_officer_name", None) or "Lead Investigating Officer",
                supervisor_approval=True
            )
            db.add(cs)
            db.flush()
            created.append(cs)

            # Add constituent elements
            for elem_txt in meta.get("elements", []):
                elem = SectionElement(
                    case_section_id=cs.id,
                    element_text=elem_txt,
                    status="partial" if "302" in offence_text else "missing"
                )
                db.add(elem)

    if not created:
        # Default fallback section
        cs = CaseSection(
            case_id=case_id,
            act="BNS",
            section_code="103(1) BNS / 302 IPC",
            description="Murder / Heinous Offence",
            punishment_tier="life_or_death_over_10_years",
            status="initial",
            reason="FIR substantive investigation",
            deciding_officer="Lead Investigating Officer",
            supervisor_approval=True
        )
        db.add(cs)
        db.flush()
        created.append(cs)
        for elem_txt in PENAL_SECTIONS_DATABASE["103(1)"]["elements"]:
            db.add(SectionElement(case_section_id=cs.id, element_text=elem_txt, status="partial"))

    db.commit()
    return created


def recalculate_sections_statutory_impact(case_id: int, db: Session) -> Dict[str, Any]:
    """
    Evaluates active sections in case_sections. If any section carries death, life imprisonment,
    or >= 10 years, statutory limit is 90 days. If all active sections carry < 10 years,
    statutory limit drops to 60 days. Triggers deadline recalculation immediately.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    active_sections = db.query(CaseSection).filter(
        CaseSection.case_id == case_id,
        CaseSection.status.in_(["initial", "added"])
    ).all()

    has_heinous_tier = any(
        s.punishment_tier == "life_or_death_over_10_years" for s in active_sections
    )

    new_limit_days = 90 if has_heinous_tier or not active_sections else 60
    old_limit_days = case.statutory_time_limit_days or 90

    limit_changed = new_limit_days != old_limit_days
    case.statutory_time_limit_days = new_limit_days

    # Reconstruct summary offence_section string
    active_codes = [s.section_code for s in active_sections]
    if active_codes:
        case.offence_section = ", ".join(active_codes)

    db.commit()

    # Trigger statutory deadlines re-evaluation
    recalculate_case_deadlines(case_id, db)

    return {
        "case_id": case_id,
        "old_limit_days": old_limit_days,
        "new_limit_days": new_limit_days,
        "limit_changed": limit_changed,
        "active_sections_count": len(active_sections),
        "statutory_rule": "Section 187(3) BNSS / 167(2) CrPC (90 days for death/life/>=10yrs, 60 days for other offences)"
    }


# ==============================================================================
# 6. PER-ACCUSED STATUTORY CLOCKS
# ==============================================================================

def get_per_accused_statutory_clocks(case_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Evaluates individual custody and arrest dates per accused person.
    Statutory filing and remand clocks run per accused, not globally.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    limit_days = getattr(case, "statutory_time_limit_days", 90) or 90

    accused_persons = db.query(CasePerson).filter(
        CasePerson.case_id == case_id,
        CasePerson.role == "accused"
    ).all()

    results = []
    now = datetime.now(timezone.utc)

    for person in accused_persons:
        # Find latest custody status
        latest_status = db.query(AccusedStatusHistory).filter(
            AccusedStatusHistory.case_id == case_id,
            AccusedStatusHistory.person_id == person.id
        ).order_by(AccusedStatusHistory.status_date.desc()).first()

        # Find initial arrest date
        arrest_record = db.query(AccusedStatusHistory).filter(
            AccusedStatusHistory.case_id == case_id,
            AccusedStatusHistory.person_id == person.id,
            AccusedStatusHistory.status.in_(["arrested", "police_custody", "judicial_custody"])
        ).order_by(AccusedStatusHistory.status_date.asc()).first()

        arrest_dt = arrest_record.status_date if arrest_record else None
        current_status = latest_status.status if latest_status else "not_identified"
        order_ref = latest_status.order_reference if latest_status else None

        if arrest_dt:
            # Ensure UTC
            if arrest_dt.tzinfo is None:
                arrest_dt = arrest_dt.replace(tzinfo=timezone.utc)

            chargesheet_deadline = arrest_dt + timedelta(days=limit_days)
            remand_deadline = arrest_dt + timedelta(days=15)

            cs_seconds_left = (chargesheet_deadline - now).total_seconds()
            cs_days_left = max(0, int(cs_seconds_left // 86400))
            is_cs_overdue = cs_seconds_left < 0

            rem_seconds_left = (remand_deadline - now).total_seconds()
            rem_days_left = max(0, int(rem_seconds_left // 86400))
            is_rem_overdue = rem_seconds_left < 0

            # Band calculation
            if is_cs_overdue:
                cs_band = "overdue"
            elif cs_days_left <= 3:
                cs_band = "critical"
            elif cs_days_left <= 7:
                cs_band = "urgent"
            elif cs_days_left <= 14:
                cs_band = "watch"
            else:
                cs_band = "calm"
        else:
            chargesheet_deadline = None
            remand_deadline = None
            cs_days_left = None
            rem_days_left = None
            cs_band = "missing_dates"

        results.append({
            "person_id": person.id,
            "name": person.name,
            "aliases": person.aliases,
            "current_status": current_status,
            "order_reference": order_ref,
            "arrest_date": arrest_dt.isoformat() if arrest_dt else None,
            "chargesheet_deadline": chargesheet_deadline.isoformat() if chargesheet_deadline else None,
            "chargesheet_days_left": cs_days_left,
            "chargesheet_band": cs_band,
            "remand_deadline": remand_deadline.isoformat() if remand_deadline else None,
            "remand_days_left": rem_days_left,
            "is_custody_active": current_status in ["arrested", "police_custody", "judicial_custody"]
        })

    return results
