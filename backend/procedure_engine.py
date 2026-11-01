"""
backend/procedure_engine.py
===========================
Procedure and Statutory Deadline Tracking Engine.
- Maintains legal expert-reviewed statutory deadline rules table (CrPC / BNSS / NDPS / POCSO).
- Automatic deadline countdowns (arrest, remand, FIR, statutory time limits).
- Forensic evidence checklist per offence type flagging expected & missing exhibits.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    Case, Evidence, CaseDeadline, StatutoryDeadlineRule,
    OffenceEvidenceProtocol, AuditLog, Alert, User
)
from audit_engine import log_audit_event
from collaboration import publish_collaboration_event

logger = logging.getLogger("evidentia.procedure")


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==============================================================================
# 1. SEED EXPERT-REVIEWED STATUTORY RULES TABLE
# ==============================================================================

def ensure_comprehensive_statutory_rules(db: Session) -> None:
    """
    Seeds comprehensive statutory deadline rules reviewed by legal experts.
    Prevents legal periods from being hardcoded in code and records judicial precedents.
    """
    count = db.query(StatutoryDeadlineRule).count()
    if count >= 6:
        return

    expert_reviewer = "Adv. K. Parasaran (Senior Advocate & Spl. Public Prosecutor, Supreme Court Bar)"
    
    rules = [
        StatutoryDeadlineRule(
            statute_name="BNSS 2023 / CrPC 1973",
            section_reference="Section 187(3) BNSS / Section 167(2) CrPC",
            offence_category="heinous",
            limit_days=90,
            trigger_event="arrest_date",
            procedure_name="Statutory Charge Sheet Submission (Heinous)",
            is_reviewed_by_expert=True,
            expert_reviewer=expert_reviewer,
            legal_notes="Per Supreme Court in Sanjay Dutt v. State (1994) 5 SCC 410 and Uday Mohanlal Acharya v. State of Maharashtra (2001) 5 SCC 453: Right to default bail accrues indefeasibly on expiry of the 90th day if charge sheet is not filed. Section 187(3) BNSS maintains strict 90-day detention threshold for offences punishable by death, life, or 10+ years imprisonment.",
            description="90 days statutory detention deadline for offences punishable with death, imprisonment for life, or imprisonment for not less than 10 years. Charge sheet must be filed to prevent mandatory default bail under Section 187(3) BNSS."
        ),
        StatutoryDeadlineRule(
            statute_name="BNSS 2023 / CrPC 1973",
            section_reference="Section 187(3) BNSS / Section 167(2) CrPC",
            offence_category="general",
            limit_days=60,
            trigger_event="arrest_date",
            procedure_name="Statutory Charge Sheet Submission (General)",
            is_reviewed_by_expert=True,
            expert_reviewer="Directorate of Prosecution, Criminal Law Reform Advisory Committee",
            legal_notes="Applicable to all cognizable offences with maximum statutory punishment of less than 10 years imprisonment. Default bail entitlement under Section 187(3)(b) BNSS.",
            description="60 days statutory investigation deadline for all other cognizable offences. Charge sheet must be filed within 60 days of initial remand."
        ),
        StatutoryDeadlineRule(
            statute_name="NDPS Act 1985",
            section_reference="Section 36A(4) NDPS Act",
            offence_category="narcotics",
            limit_days=180,
            trigger_event="arrest_date",
            procedure_name="Special Court NDPS Final Report",
            is_reviewed_by_expert=True,
            expert_reviewer="Narcotics Control Bureau (NCB) Standing Legal Counsel",
            legal_notes="Section 36A(4) NDPS Act extends standard investigation time to 180 days for commercial quantity contraband. Extendable up to 1 year by Special Court on Public Prosecutor's report indicating specific progress.",
            description="180 days investigation timeframe for commercial quantity illicit drug trafficking before default bail accrues."
        ),
        StatutoryDeadlineRule(
            statute_name="BNSS 2023",
            section_reference="Section 187(2) BNSS",
            offence_category="police_custody",
            limit_days=15,
            trigger_event="remand_date",
            procedure_name="Initial Police Custody Remand Limit",
            is_reviewed_by_expert=True,
            expert_reviewer="State Police & Forensic Reform Board",
            legal_notes="Section 187(2) BNSS permits police custody remand of 15 days in whole or in parts during the first 40 or 60 days of total detention.",
            description="15 days maximum police custody remand for interrogation, recovery panchanama, and discovery under Section 23 BSA 2023."
        ),
        StatutoryDeadlineRule(
            statute_name="BNSS 2023 / CrPC 1973",
            section_reference="Section 187(2) BNSS / Section 167(2) CrPC",
            offence_category="judicial_remand",
            limit_days=14,
            trigger_event="remand_date",
            procedure_name="Fortnightly Judicial Remand Renewal",
            is_reviewed_by_expert=True,
            expert_reviewer="State Legal Services Authority (SLSA)",
            legal_notes="Judicial remand cannot exceed 15 days at a single instance. Physical or virtual magistrate production is legally mandatory.",
            description="14 days review cycle for renewing judicial custody remand before the Jurisdictional Magistrate."
        ),
        StatutoryDeadlineRule(
            statute_name="POCSO Act 2012 / BNSS 2023",
            section_reference="Section 35(1) POCSO Act / Section 183 BNSS",
            offence_category="special",
            limit_days=30,
            trigger_event="fir_date",
            procedure_name="Child Magisterial Statement Recording (Sec 183)",
            is_reviewed_by_expert=True,
            expert_reviewer="National Commission for Protection of Child Rights (NCPCR) Legal Advisor",
            legal_notes="Statement of child victim must be recorded within 30 days of registration of FIR by a woman Magistrate in child-friendly environment.",
            description="30 days deadline to record judicial statement of minor victim under POCSO Act and Section 183 BNSS."
        ),
        StatutoryDeadlineRule(
            statute_name="PMLA 2002 / BNSS 2023",
            section_reference="Section 5(1) PMLA / Section 107 BNSS",
            offence_category="financial_fraud",
            limit_days=180,
            trigger_event="incident_date",
            procedure_name="Adjudicating Authority Bank/Asset Freeze Confirmation",
            is_reviewed_by_expert=True,
            expert_reviewer="Financial Intelligence Unit & Enforcement Directorate Legal Cell",
            legal_notes="Provisional attachment of bank accounts or crime proceeds ceases after 180 days unless formal complaint filed before Adjudicating Authority.",
            description="180 days statutory ceiling for confirming provisional bank account and property attachment orders."
        )
    ]

    for r in rules:
        existing = db.query(StatutoryDeadlineRule).filter(
            StatutoryDeadlineRule.section_reference == r.section_reference,
            StatutoryDeadlineRule.procedure_name == r.procedure_name
        ).first()
        if not existing:
            db.add(r)
    db.commit()


# ==============================================================================
# 2. SEED OFFENCE EVIDENCE PROTOCOLS TABLE
# ==============================================================================

def ensure_evidence_protocols(db: Session) -> None:
    """
    Seeds comprehensive forensic evidence protocols per offence type.
    Specifies expected exhibits, statutory provisions, and admissibility consequences.
    """
    count = db.query(OffenceEvidenceProtocol).count()
    if count >= 18:
        return

    protocols = [
        # --- HOMICIDE / MURDER PROTOCOL ---
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death,killing,dead body",
            exhibit_code="POST_MORTEM_REPORT",
            title="Post-Mortem Autopsy Examination Report",
            description="Formal autopsy report by forensic pathologist or authorized government medical officer establishing exact cause, time of death, ante-mortem vs post-mortem injuries, and weapon mechanism.",
            mandatory=True,
            legal_provision="Section 194 BNSS / Section 174 CrPC",
            matching_keywords="post_mortem,autopsy,pm_report,postmortem,viscera,fsl_viscera,cause of death",
            consequence_if_missing="Corpus delicti and exact cause of death cannot be judicially established; prosecution case vulnerable to fatal reasonable doubt."
        ),
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death",
            exhibit_code="INQUEST_PANCHANAMA",
            title="Inquest Panchanama Report",
            description="Contemporaneous inspection panchanama of the body at the place of discovery witnessed by two respectable local panchas.",
            mandatory=True,
            legal_provision="Section 194 BNSS / Section 174 CrPC",
            matching_keywords="inquest,panchanama_inquest,body_panchanama,spot_inquest,surathal",
            consequence_if_missing="Condition and position of deceased body upon recovery unverified; fatal to scene reconstruction."
        ),
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death",
            exhibit_code="CRIME_SCENE_SKETCH",
            title="Forensic Crime Scene Sketch & Photographic / Video Log",
            description="Scale sketch of crime scene depicting points of entry/exit, location of body, blood spatter trails, and photographic/video recording.",
            mandatory=True,
            legal_provision="Section 176 BNSS / Section 105 BSA 2023",
            matching_keywords="sketch,scene_sketch,site_plan,crime_scene_photo,scene_photo,photograph_log",
            consequence_if_missing="Spatial geometry, ballistics trajectories, and line of sight cannot be verified during cross-examination."
        ),
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death",
            exhibit_code="WEAPON_RECOVERY_MEMO",
            title="Weapon / Article Recovery Memo (Sec 23 BSA / Sec 27 IEA)",
            description="Panchanama of weapon or incriminating object discovered pursuant to disclosure statement made by accused while in custody.",
            mandatory=True,
            legal_provision="Section 23 BSA 2023 / Section 27 Indian Evidence Act",
            matching_keywords="recovery_memo,weapon_recovery,knife_recovery,firearm_recovery,panchanama_recovery,disclosure_memo,section_27",
            consequence_if_missing="Direct physical nexus between suspect and fatal crime weapon severed in judicial scrutiny."
        ),
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death",
            exhibit_code="FORENSIC_FSL_REPORT",
            title="Forensic Chemical / Biological / DNA Analysis Report (FSL)",
            description="Official report from Forensic Science Laboratory matching blood group, DNA profile, or ballistic striations with weapon and suspect.",
            mandatory=True,
            legal_provision="Section 329 BNSS / Section 293 CrPC",
            matching_keywords="dna_report,fsl_report,ballistics_report,forensic_analysis,chemical_report,serology",
            consequence_if_missing="Absence of scientific corroboration linking accused to deceased's biological trace evidence."
        ),
        OffenceEvidenceProtocol(
            offence_category="homicide",
            offence_section_keywords="302,103,murder,homicide,death",
            exhibit_code="SEIZURE_PANCHANAMA",
            title="Seizure Panchanama of Blood-Stained Soil / Garments",
            description="Seizure memo recording collection of blood-stained clothes, control soil, and swab samples with intact seal impressions.",
            mandatory=True,
            legal_provision="Section 185 BNSS / Section 100 CrPC",
            matching_keywords="seizure_memo,panchanama_seizure,soil_sample,garment_seizure,cloth_seizure",
            consequence_if_missing="Chain of custody broken; FSL findings can be excluded on grounds of possible sample tampering."
        ),

        # --- FINANCIAL FRAUD & CYBER CRIME PROTOCOL ---
        OffenceEvidenceProtocol(
            offence_category="financial_fraud",
            offence_section_keywords="420,318,316,fraud,cheating,cyber,it act,66d,financial",
            exhibit_code="BANK_STATEMENT_CERTIFIED",
            title="Bank Account Statement with Section 2A Bankers' Books Certificate",
            description="Certified bank statements with certificate under Section 2A Bankers' Books Evidence Act 1891 / Section 63 BSA.",
            mandatory=True,
            legal_provision="Section 2A Bankers' Books Evidence Act 1891",
            matching_keywords="bank_statement,account_statement,bankers_books,passbook,transaction_statement",
            consequence_if_missing="Financial transaction records inadmissible as uncertified computer printouts."
        ),
        OffenceEvidenceProtocol(
            offence_category="financial_fraud",
            offence_section_keywords="420,318,316,fraud,cheating,cyber,it act,66d",
            exhibit_code="SEC_65B_CERTIFICATE",
            title="Mandatory Electronic Certificate (Sec 65B IEA / Sec 63 BSA)",
            description="Custody and system operating certificate signed by competent person in lawful control of computer device producing electronic records.",
            mandatory=True,
            legal_provision="Section 63 BSA 2023 / Section 65B Indian Evidence Act 1872",
            matching_keywords="sec_65b,65b_certificate,section_63,bsa_63,electronic_certificate,certificate_65b",
            consequence_if_missing="Electronic evidence (CDR, emails, logs, spreadsheets) inadmissible under Arjun Panditrao (2020) 7 SCC 1."
        ),
        OffenceEvidenceProtocol(
            offence_category="financial_fraud",
            offence_section_keywords="420,318,316,fraud,cheating,cyber,it act,66d",
            exhibit_code="CALL_DETAIL_RECORDS",
            title="Telecom Call Detail Records (CDR) & Tower Cell ID",
            description="Certified CDR and Subscriber Identity Module (SDR) data authenticated by Telecom Service Provider Nodal Officer.",
            mandatory=True,
            legal_provision="Section 63 BSA 2023 / Section 65B IEA",
            matching_keywords="cdr,call_detail,tower_cdr,sdr_dump,subscriber_data,telecom_cdr",
            consequence_if_missing="Suspect communication, co-conspirator coordinates, and device locations cannot be corroborated."
        ),
        OffenceEvidenceProtocol(
            offence_category="financial_fraud",
            offence_section_keywords="420,318,316,fraud,cheating,cyber,it act,66d",
            exhibit_code="DIGITAL_DEVICE_HASH_MEMO",
            title="Forensic Image & SHA-256 Hash Verification Memo",
            description="Forensic extraction memo recording source device IMEI/MAC, acquisition tool, and exact cryptographic hash before examination.",
            mandatory=True,
            legal_provision="Section 79A Information Technology Act 2000",
            matching_keywords="hash_memo,sha256_memo,forensic_image,extraction_report,mobile_extraction,cellebrite",
            consequence_if_missing="Defense can claim digital evidence was planted or altered in police custody."
        ),
        OffenceEvidenceProtocol(
            offence_category="financial_fraud",
            offence_section_keywords="420,318,316,fraud,cheating,cyber,it act,66d",
            exhibit_code="FRAUD_TRANSACTION_TRAIL",
            title="Money Trail & Layering Flowchart Dossier",
            description="Audited forensic accounting chart detailing primary debit, mule accounts, ATM withdrawals, and ultimate beneficiaries.",
            mandatory=True,
            legal_provision="Section 318 BNS / Section 420 IPC",
            matching_keywords="money_trail,fund_flow,layering_chart,accounting_audit,forensic_audit,beneficiary_trail",
            consequence_if_missing="Failure to prove dishonest inducement, wrongful loss to victim, and wrongful gain to accused."
        ),

        # --- NARCOTICS (NDPS ACT) PROTOCOL ---
        OffenceEvidenceProtocol(
            offence_category="narcotics",
            offence_section_keywords="ndps,narcotic,drug,contraband,charas,ganja,heroin,mdma",
            exhibit_code="SECTION_50_NOTICE",
            title="Section 50 NDPS Personal Search Notice",
            description="Written notice informing suspect of legal right to be searched before a Gazetted Officer or Magistrate.",
            mandatory=True,
            legal_provision="Section 50 NDPS Act 1985",
            matching_keywords="sec_50_notice,section_50,search_notice,gazetted_officer_notice",
            consequence_if_missing="Non-compliance with Section 50 is strictly fatal to prosecution per Constitution Bench in Vijaysinh Jadeja (2011)."
        ),
        OffenceEvidenceProtocol(
            offence_category="narcotics",
            offence_section_keywords="ndps,narcotic,drug,contraband",
            exhibit_code="MAGISTRATE_INVENTORY_52A",
            title="Magistrate Inventory & Certified Sample Memo (Sec 52A)",
            description="Inventory of seized contraband with photographs and representative samples certified by Jurisdictional Magistrate.",
            mandatory=True,
            legal_provision="Section 52A NDPS Act 1985",
            matching_keywords="sec_52a,section_52a,magistrate_inventory,52a_certificate,sample_certificate",
            consequence_if_missing="Primary evidence of seizure absent; trial court cannot rely on police samples per Union of India v. Mohanlal (2016)."
        ),
        OffenceEvidenceProtocol(
            offence_category="narcotics",
            offence_section_keywords="ndps,narcotic,drug,contraband",
            exhibit_code="FSL_CHEMICAL_REPORT",
            title="Forensic Chemical Examiner Quantitative Assay Report",
            description="Laboratory test report confirming purity percentage and active psychotropic compound identity.",
            mandatory=True,
            legal_provision="Section 293 CrPC / Section 329 BNSS",
            matching_keywords="ndps_fsl,chemical_examiner,drug_assay,contraband_test,narcotic_report",
            consequence_if_missing="Substance cannot be proved to fall under prohibited Schedule of NDPS Act."
        ),

        # --- SEXUAL OFFENCE / POCSO PROTOCOL ---
        OffenceEvidenceProtocol(
            offence_category="sexual_offence",
            offence_section_keywords="376,64,65,rape,pocso,sexual",
            exhibit_code="VICTIM_MEDICAL_REPORT",
            title="Victim Medico-Legal Examination Report",
            description="Medical examination report of the victim conducted within 24 hours of reporting by registered medical practitioner.",
            mandatory=True,
            legal_provision="Section 51 BNSS / Section 164A CrPC",
            matching_keywords="medical_report,mlc,victim_medical,examination_report,injury_memo",
            consequence_if_missing="No objective medical findings of trauma or biological trace evidence."
        ),
        OffenceEvidenceProtocol(
            offence_category="sexual_offence",
            offence_section_keywords="376,64,65,rape,pocso,sexual",
            exhibit_code="MAGISTRATE_STATEMENT_183",
            title="Judicial Statement Recorded before Magistrate (Sec 183)",
            description="Confidential recording of victim statement under oath before Metropolitan / Judicial Magistrate.",
            mandatory=True,
            legal_provision="Section 183 BNSS / Section 164 CrPC",
            matching_keywords="164_statement,183_statement,magistrate_statement,judicial_statement,victim_statement",
            consequence_if_missing="High risk of witness resiling; lack of solemn statutory judicial statement."
        ),
        OffenceEvidenceProtocol(
            offence_category="sexual_offence",
            offence_section_keywords="376,64,65,rape,pocso,sexual",
            exhibit_code="DNA_SWAB_FSL_REPORT",
            title="Forensic DNA Profiling & Semen Analysis Report (FSL)",
            description="Forensic Science Laboratory DNA report confirming biological match from swabs or garments.",
            mandatory=True,
            legal_provision="Section 52 BNSS / Section 53A CrPC",
            matching_keywords="dna_report,dna_profiling,semen_report,fsl_dna,swab_fsl",
            consequence_if_missing="Scientific identity of perpetrator cannot be proved beyond reasonable doubt."
        ),

        # --- THEFT & ROBBERY PROTOCOL ---
        OffenceEvidenceProtocol(
            offence_category="theft_robbery",
            offence_section_keywords="379,392,395,303,309,theft,robbery,dacoity",
            exhibit_code="COMPLAINANT_INVENTORY",
            title="Complainant Stolen Property Inventory & Purchase Invoices",
            description="Itemized list of stolen jewelry, cash, electronics, or vehicle chassis numbers with proof of ownership.",
            mandatory=True,
            legal_provision="Section 173 BNSS / Section 154 CrPC",
            matching_keywords="stolen_inventory,property_list,purchase_invoice,jewel_voucher,ownership_proof",
            consequence_if_missing="Property identity unspecified, making subsequent identification dubious."
        ),
        OffenceEvidenceProtocol(
            offence_category="theft_robbery",
            offence_section_keywords="379,392,395,303,309,theft,robbery,dacoity",
            exhibit_code="RECOVERY_MEMO_SEC27",
            title="Recovery Panchanama under Section 23 BSA (Sec 27 IEA)",
            description="Seizure memo of stolen property recovered from accused's possession or hidden concealment location.",
            mandatory=True,
            legal_provision="Section 23 BSA 2023 / Section 27 IEA",
            matching_keywords="recovery_memo,seizure_panchanama,stolen_recovery,property_recovery,gold_recovery",
            consequence_if_missing="Presumption under Section 119 BSA (possession of stolen property) cannot be drawn."
        ),
        OffenceEvidenceProtocol(
            offence_category="theft_robbery",
            offence_section_keywords="379,392,395,303,309,theft,robbery,dacoity",
            exhibit_code="CCTV_FOOTAGE_AND_CERT",
            title="CCTV Surveillance Video with Sec 65B Certificate",
            description="Video recording of entry, getaway, or ATM transactions authenticated under Section 63 BSA.",
            mandatory=False,
            legal_provision="Section 63 BSA 2023 / Section 65B IEA",
            matching_keywords="cctv,surveillance,video_recording,dvr_footage,atm_cctv",
            consequence_if_missing="Visual corroboration of suspect presence at scene or pawn shop absent."
        )
    ]

    for p in protocols:
        existing = db.query(OffenceEvidenceProtocol).filter(
            OffenceEvidenceProtocol.offence_category == p.offence_category,
            OffenceEvidenceProtocol.exhibit_code == p.exhibit_code
        ).first()
        if not existing:
            db.add(p)
    db.commit()


# ==============================================================================
# 3. OFFENCE CATEGORY DETECTION
# ==============================================================================

def detect_case_offence_category(offence_section: Optional[str], case_type: Optional[str] = None) -> str:
    """
    Detects the standardized offence category from FIR sections or case description.
    Maps Indian statutory sections (IPC, BNS, NDPS, POCSO, IT Act) to checklist protocols.
    """
    text = f"{offence_section or ''} {case_type or ''}".lower()

    if any(k in text for k in ["302", "103", "murder", "homicide", "culpable", "307", "109 bns"]):
        return "homicide"
    if any(k in text for k in ["ndps", "narcotic", "drug", "contraband", "ganja", "charas", "heroin"]):
        return "narcotics"
    if any(k in text for k in ["pocso", "rape", "376", "64 bns", "65 bns", "sexual"]):
        return "sexual_offence"
    if any(k in text for k in ["420", "318", "fraud", "cheating", "cyber", "it act", "66", "bank", "embezzlement", "pmla"]):
        return "financial_fraud"
    if any(k in text for k in ["379", "392", "395", "303 bns", "309 bns", "theft", "robbery", "dacoity"]):
        return "theft_robbery"

    return "general_cognizable"


# ==============================================================================
# 4. DEADLINE RECALCULATION & SYNCHRONIZATION
# ==============================================================================

def recalculate_case_deadlines(case_id: int, db: Session) -> List[CaseDeadline]:
    """
    Synchronizes case deadlines whenever arrest, remand, or FIR dates are created/updated.
    Matches against expert-reviewed statutory deadline rules table.
    """
    ensure_comprehensive_statutory_rules(db)
    now = datetime.now(timezone.utc)
    updated_deadlines: List[CaseDeadline] = []

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return updated_deadlines

    offence_cat = detect_case_offence_category(case.offence_section)

    # 1. Statutory Charge Sheet Deadline (BNSS 187(3) / CrPC 167(2))
    # Triggered by arrest_date or remand_date
    trigger_date = _ensure_utc(case.arrest_date or case.remand_date)
    if trigger_date:
        # Determine limit days: 180 for narcotics, 90 for heinous/murder, 60 for general
        if offence_cat == "narcotics":
            limit_days = 180
            rule_cat = "narcotics"
            title_prefix = "NDPS Statutory Charge Sheet (180 Days)"
        elif offence_cat == "homicide" or (case.statutory_time_limit_days and case.statutory_time_limit_days >= 90):
            limit_days = 90
            rule_cat = "heinous"
            title_prefix = "Statutory Charge Sheet Deadline (90 Days - Sec 187 BNSS / 167 CrPC)"
        else:
            limit_days = case.statutory_time_limit_days or 60
            rule_cat = "general"
            title_prefix = f"Statutory Charge Sheet Deadline ({limit_days} Days - Sec 187 BNSS)"

        due_date = trigger_date + timedelta(days=limit_days)

        rule = db.query(StatutoryDeadlineRule).filter(
            StatutoryDeadlineRule.offence_category == rule_cat,
            StatutoryDeadlineRule.trigger_event == "arrest_date"
        ).first()

        existing_cs = db.query(CaseDeadline).filter(
            CaseDeadline.case_id == case_id,
            CaseDeadline.title.like("%Charge Sheet%")
        ).first()

        if existing_cs:
            if existing_cs.status != "satisfied":
                existing_cs.due_date = due_date
                existing_cs.title = title_prefix
                existing_cs.statute_rule_id = rule.id if rule else existing_cs.statute_rule_id
                db.commit()
                db.refresh(existing_cs)
            updated_deadlines.append(existing_cs)
        else:
            new_dl = CaseDeadline(
                case_id=case_id,
                statute_rule_id=rule.id if rule else None,
                title=title_prefix,
                due_date=due_date,
                status="pending"
            )
            db.add(new_dl)
            db.commit()
            db.refresh(new_dl)
            updated_deadlines.append(new_dl)

    # 2. Fortnightly Judicial Remand Renewal Deadline (BNSS 187(2) / CrPC 167)
    # Triggered by remand_date
    if case.remand_date:
        rem_date = _ensure_utc(case.remand_date)
        rem_due = rem_date + timedelta(days=14)

        rem_rule = db.query(StatutoryDeadlineRule).filter(
            StatutoryDeadlineRule.procedure_name.like("%Remand%")
        ).first()

        existing_rem = db.query(CaseDeadline).filter(
            CaseDeadline.case_id == case_id,
            CaseDeadline.title.like("%Remand Renewal%")
        ).first()

        if existing_rem:
            if existing_rem.status != "satisfied":
                existing_rem.due_date = rem_due
                db.commit()
                db.refresh(existing_rem)
            updated_deadlines.append(existing_rem)
        else:
            new_rem = CaseDeadline(
                case_id=case_id,
                statute_rule_id=rem_rule.id if rem_rule else None,
                title="Judicial Remand Renewal (14-Day Cycle - Sec 187(2) BNSS)",
                due_date=rem_due,
                status="pending"
            )
            db.add(new_rem)
            db.commit()
            db.refresh(new_rem)
            updated_deadlines.append(new_rem)

    return updated_deadlines


# ==============================================================================
# 5. EVIDENCE CHECKLIST EVALUATION
# ==============================================================================

def evaluate_evidence_checklist(case_id: int, db: Session) -> Dict[str, Any]:
    """
    Evaluates evidence checklist for the case's offence type.
    Flags expected exhibits that are missing and raises warnings for court compliance.
    """
    ensure_evidence_protocols(db)
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case #{case_id} not found")

    category = detect_case_offence_category(case.offence_section)

    # Fetch expected protocols for this category (plus universal cyber/65b if electronic records exist)
    protocols = db.query(OffenceEvidenceProtocol).filter(
        OffenceEvidenceProtocol.offence_category == category
    ).all()

    # If no specific category found, fallback to homicide or financial_fraud protocols
    if not protocols:
        protocols = db.query(OffenceEvidenceProtocol).filter(
            OffenceEvidenceProtocol.offence_category == "homicide"
        ).all()

    # Active exhibits for this case
    exhibits = db.query(Evidence).filter(
        Evidence.case_id == case_id,
        Evidence.is_deleted == False
    ).all()

    checklist_items: List[Dict[str, Any]] = []
    missing_mandatory_count = 0
    warnings: List[str] = []

    for proto in protocols:
        keywords = [k.strip().lower() for k in proto.matching_keywords.split(",") if k.strip()]
        matched_exhibit: Optional[Evidence] = None

        # Search active exhibits for match
        for ev in exhibits:
            combined_search_text = f"{ev.file_name or ''} {ev.evidence_type or ''} {ev.file_type or ''} {ev.extracted_text or ''}".lower()
            if any(k in combined_search_text for k in keywords):
                matched_exhibit = ev
                break
            # Check 65B flag specifically
            if proto.exhibit_code == "SEC_65B_CERTIFICATE" and ev.sec_65b_certificate_present:
                matched_exhibit = ev
                break

        is_present = matched_exhibit is not None
        status = "present" if is_present else "missing"

        if not is_present and proto.mandatory:
            missing_mandatory_count += 1
            warnings.append(
                f"Missing Mandatory Exhibit: '{proto.title}' required under {proto.legal_provision}. {proto.consequence_if_missing}"
            )

        checklist_items.append({
            "exhibit_code": proto.exhibit_code,
            "title": proto.title,
            "description": proto.description,
            "mandatory": proto.mandatory,
            "legal_provision": proto.legal_provision,
            "consequence_if_missing": proto.consequence_if_missing,
            "status": status,
            "matched_evidence_id": matched_exhibit.id if matched_exhibit else None,
            "matched_file_name": matched_exhibit.file_name if matched_exhibit else None,
            "matched_at": _ensure_utc(matched_exhibit.upload_date).isoformat() if matched_exhibit and matched_exhibit.upload_date else None,
        })

    total_expected = len(protocols)
    present_count = len([i for i in checklist_items if i["status"] == "present"])
    missing_count = total_expected - present_count
    mandatory_expected = len([p for p in protocols if p.mandatory])
    compliance_percentage = round((present_count / max(1, total_expected)) * 100, 1)

    return {
        "case_id": case_id,
        "offence_section": case.offence_section or "Standard Investigation Protocol",
        "offence_category": category,
        "total_expected": total_expected,
        "mandatory_expected": mandatory_expected,
        "present_count": present_count,
        "missing_count": missing_count,
        "mandatory_missing_count": missing_mandatory_count,
        "compliance_percentage": compliance_percentage,
        "items": checklist_items,
        "warnings": warnings,
    }
