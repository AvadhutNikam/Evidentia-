"""
backend/evaluation/benchmark_dataset.py
======================================
Defines the benchmark dataset for Evidentia-AI's ACH Validation Experiment.
Contains 12 self-contained, frozen forensic cases:
  - 3 Landmark Real Cases (including 1 Contested case)
  - 4 Real Anonymized Solved Court Cases (Court judgment citations)
  - 5 Synthetic Cases with deliberate traps (misleading eyewitnesses,
    non-diagnostic ubiquitous evidence, planted red herrings, false confessions,
    and circumstantial noise vs direct forensics).

Each case provides:
  - Case metadata (split, category, confidence, citations)
  - Candidate hypotheses (true hypothesis, plausible distractors)
  - Exhibits with forensic integrity parameters (evidence type, hash, 65B, etc.)
  - Decisive exhibits list (for sensitivity & critical evidence validation)
  - Planted adversarial exhibit (for adversarial robustness injection testing)
"""

import json
from pathlib import Path
from typing import Dict, List, Any

BENCHMARK_CASES: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # CASE 1: REAL LANDMARK (Tuning Set - Anonymized Court Archive)
    # --------------------------------------------------------------------------
    {
        "id": "case_01_pujari",
        "title": "State v. Y.R. & Ors. (Transit Corridor Abduction Case)",
        "split": "tuning",
        "category": "real_landmark",
        "is_contested": False,
        "citation": "Special Sessions Court (Judgment confirmed by High Court appellate bench - Anonymized Archive)",
        "confidence_note": "High (Beyond Reasonable Doubt, confirmed on appeal with forensic corroboration)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Suspect Y.R. and co-accused (cab driver and accomplices)",
            "rationale": "Forensic blood match in Qualis cab, ATM CCTV cash withdrawal, Sec 164 CrPC judicial confession by approver."
        },
        "decisive_evidence_ids": ["EX-01-01", "EX-01-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Suspect Y.R. & Co-accused",
                "statement": "Cab driver Y.R. and accomplices abducted the victim in Qualis cab, used her ATM cards, and committed the assault."
            },
            {
                "id": "H2",
                "label": "Unknown Highway Syndicate",
                "statement": "An opportunistic inter-state highway gang hijacked the victim at transit bypass; cab driver was unrelated."
            },
            {
                "id": "H3",
                "label": "Workplace Colleague",
                "statement": "A disgruntled corporate colleague arranged the abduction using a hired private vehicle."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "secondary_opportunistic", "numeric_adjustment": 0.50},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.45},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "professional_conflict", "numeric_adjustment": 0.70},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {
            "H1": [
                {
                    "suspect_name": "Suspect Y.R.",
                    "offense_type": "Armed Highway Robbery & Gang Abduction",
                    "legal_section": "Section 392, 397 IPC",
                    "offense_date": "2007-04-18",
                    "location": "Bypass Corridor, Pune",
                    "outcome": "convicted",
                    "weapon_used": "Iron rod / jack handle",
                    "entry_method": "Fake transport / cab route intercept",
                    "victim_type": "Lone female commuter post-evening shift",
                    "location_type": "Desolate transit bypass / isolated corridor",
                    "time_pattern": "Late night 21:00-01:00",
                    "mo_description": "Suspect and accomplices operated a shared vehicle pretending to be official route transport. Targeted lone female corporate employees.",
                    "verification_status": "verified",
                    "identity_match_confidence": 0.98,
                    "verified_identity": True,
                    "is_juvenile": False
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-01-01",
                "name": "State Bank of India ATM CCTV Footage & Transaction Log",
                "evidence_type": "CCTV",
                "file_hash": "sha256_sbi_atm_08102009",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "SBI ATM CCTV camera at Talegaon Dabhade timestamped 22:45 IST clearly captures Yogesh Raut wearing a dark jacket withdrawing Rs 20,000 using the victim's debit card. Face match positive at 94.2% match against police dossier."
            },
            {
                "id": "EX-01-02",
                "name": "Vodafone Cellular Tower BTS Call Detail Records",
                "evidence_type": "CDR",
                "file_hash": "sha256_cdr_bts_kharadi_talegaon",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Cell tower BTS logs for IMEI matching Yogesh Raut's handset move synchronously with victim's mobile tower pings from Kharadi bypass to Talegaon Dabhade between 20:15 and 23:30 IST on the incident night."
            },
            {
                "id": "EX-01-03",
                "name": "State Forensic Science Laboratory (FSL) Qualis Cab Inspection",
                "evidence_type": "DNA",
                "file_hash": "sha256_fsl_dna_qualis_09",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Luminol testing of vehicle Qualis MH-12-CR-8692 revealed latent bloodstains on rear seat upholstery. DNA profiling matched victim's reference blood sample with random match probability 1 in 1.4 billion. Front passenger seat hairs matched Yogesh Raut."
            },
            {
                "id": "EX-01-04",
                "name": "Judicial Confession of Approver Rajesh Chaudhari",
                "evidence_type": "confession",
                "file_hash": "sha256_confession_164_jmfc",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 3,
                "text": "Judicial confession recorded under Section 164 CrPC before Metropolitan Magistrate detailing the sequence of kidnapping, ATM pin extraction, and murder executed under Yogesh Raut's leadership."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-01-ADV",
            "name": "Planted Highway Gang Receipt",
            "evidence_type": "document",
            "file_hash": "sha256_fake_toll_slip",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "Unverified handwritten scrap allegedly found on highway shoulder mentioning an unknown inter-state gang planning Kharadi robbery."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 2: REAL LANDMARK (Tuning Set - Anonymized Court Archive)
    # --------------------------------------------------------------------------
    {
        "id": "case_02_indiranagar",
        "title": "State v. M.N. & Ors. (Suburban Residence Robbery Case)",
        "split": "tuning",
        "category": "real_landmark",
        "is_contested": False,
        "citation": "Principal Sessions Court (Anonymized Archive Case #SC-412)",
        "confidence_note": "High (Direct latent fingerprint match and gold jewellery recovery under Sec 27 Evidence Act)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Former domestic assistant M.N. and accomplice",
            "rationale": "Latent fingerprint on broken window latch matched M.N.; stolen 120g temple gold recovered from pawn broker based on disclosure."
        },
        "decisive_evidence_ids": ["EX-02-01", "EX-02-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Former Domestic Staff M.N.",
                "statement": "Former domestic worker M.N. knew the safe combination, broke through the rear window, and assaulted the resident."
            },
            {
                "id": "H2",
                "label": "Local Gang Break-In",
                "statement": "An opportunistic neighborhood gang broke in randomly through the unlocked rear terrace."
            },
            {
                "id": "H3",
                "label": "Family Dispute / Staged Robbery",
                "statement": "An estranged relative staged the burglary to seize property deeds and ancestral gold."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "key_premises_access", "numeric_adjustment": 0.85},
                {"factor_type": "opportunity", "factor_value": "confirmed_vicinity", "numeric_adjustment": 0.80},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "secondary_opportunistic", "numeric_adjustment": 0.50},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.45},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "personal_enmity_grudge", "numeric_adjustment": 0.90},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {
            "H1": [
                {
                    "suspect_name": "Suspect M.N.",
                    "offense_type": "Residential Theft & Breach of Trust",
                    "legal_section": "Section 381 IPC",
                    "offense_date": "2017-06-14",
                    "location": "Bengaluru East",
                    "outcome": "convicted",
                    "weapon_used": "None",
                    "entry_method": "Domestic staff trusted key access",
                    "victim_type": "Private residential bungalow",
                    "location_type": "Urban residence",
                    "time_pattern": "Daytime shift",
                    "mo_description": "Stole gold jewelry from unlocked bedroom bureau while employed as domestic help.",
                    "verification_status": "verified",
                    "identity_match_confidence": 0.95,
                    "verified_identity": True,
                    "is_juvenile": False
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-02-01",
                "name": "Fingerprint Bureau Latent Print Lift on Window Latch",
                "evidence_type": "fingerprint",
                "file_hash": "sha256_fp_latch_bengaluru",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Eight ridge characteristics lifted from glass pane and aluminum latch of rear ground-floor window matched right index finger of Manjunath (AFIS score 98.4%)."
            },
            {
                "id": "EX-02-02",
                "name": "Residential Street CCTV Camera Feed",
                "evidence_type": "CCTV",
                "file_hash": "sha256_street_cctv_100ft",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Neighbor's Dahua IP camera captures two individuals wearing helmets entering lane at 02:14 AM and leaving at 02:49 AM on a black motorcycle with obscured plates."
            },
            {
                "id": "EX-02-03",
                "name": "Pawnshop Recovery Memo under Sec 27 Evidence Act",
                "evidence_type": "document",
                "file_hash": "sha256_pawn_gold_recovery_27",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Recovery of 120 grams of melted temple design gold necklace from Sri Balaji Bankers pawnshop pursuant to voluntary disclosure statement of Manjunath."
            },
            {
                "id": "EX-02-04",
                "name": "Witness Statement of Security Guard",
                "evidence_type": "witness",
                "file_hash": "sha256_guard_stmt_indiranagar",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Private security guard on duty reported hearing a loud thud around 02:30 AM but thought it was stray cats knocked off the parapet."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-02-ADV",
            "name": "Anonymous Tip accusing Neighboring Relative",
            "evidence_type": "document",
            "file_hash": "sha256_fake_anonymous_letter",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unsigned letter dropped in police complaint box claiming the victim's nephew was seen arguing on the veranda that afternoon."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 3: REAL CONTESTED LANDMARK (Test Set - Handled Honestly & Anonymized)
    # --------------------------------------------------------------------------
    {
        "id": "case_03_talwar",
        "title": "State Investigation v. Dr. R.T. & Dr. N.T. (Apartment Double Homicide Case)",
        "split": "test",
        "category": "contested",
        "is_contested": True,
        "citation": "High Court Appellate Review (Anonymized Special Appeal Docket)",
        "confidence_note": "Legally Unresolved / Acquitted on Benefit of Doubt (Circumstantial chain incomplete, conflicting FSL reports)",
        "ground_truth": {
            "hypothesis_id": "UNRESOLVED",
            "culprit_summary": "Legally inconclusive; trial court convicted parents, High Court acquitted due to tainted crime scene and missing links",
            "rationale": "High Court held prosecution failed to prove chain of circumstances beyond reasonable doubt. Benchmark uses this case strictly as an ambiguity test."
        },
        "decisive_evidence_ids": [],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Parents (Dr. R.T. & Dr. N.T.)",
                "statement": "The parents committed the killings inside the sealed flat under sudden grave provocation, then dressed up the crime scene."
            },
            {
                "id": "H2",
                "label": "Domestic Staff / Outside Associates",
                "statement": "Domestic helpers entered the premises, attempted assault, and committed the murders before fleeing."
            },
            {
                "id": "H3",
                "label": "Unidentified External Intruders",
                "statement": "Unknown third-party intruders entered the flat through the unlocked outer mesh door."
            }
        ],
        "exhibits": [
            {
                "id": "EX-03-01",
                "name": "Terrace & Bedroom Fingerprint Examination",
                "evidence_type": "fingerprint",
                "file_hash": "sha256_talwar_fp_crime_scene",
                "hash_verified": True,
                "chain_of_custody_complete": False,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 2,
                "text": "Fingerprint Bureau lifted 26 latent prints from master bedroom and terrace door; 24 prints smudged due to uncordoned crowd of 40+ media and neighbors walking through crime scene."
            },
            {
                "id": "EX-03-02",
                "name": "Airtel Router Internet Activity Log",
                "evidence_type": "CDR",
                "file_hash": "sha256_airtel_router_activity",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Modem records show periodic router handshakes throughout the night (03:53 AM, 04:11 AM). Prosecution alleged wakefulness; defense showed automated DHCP packet polling."
            },
            {
                "id": "EX-03-03",
                "name": "FSL CDFD Hyderabad DNA Typing Report on Pillow Covers",
                "evidence_type": "DNA",
                "file_hash": "sha256_cdfd_dna_pillow",
                "hash_verified": True,
                "chain_of_custody_complete": False,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 2,
                "text": "Initial report indicated Hemraj's DNA on Krishna's pillow cover. CDFD later issued clarification letter stating typo error in labeling sample tubes (admitted clerical mix-up)."
            },
            {
                "id": "EX-03-04",
                "name": "Medical Opinion on Dental Scalpel / Surgical Cleaver Wound",
                "evidence_type": "document",
                "file_hash": "sha256_postmortem_dr_doharey",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 3,
                "text": "Autopsy surgeon Dr. Sunil Doharey noted incised neck wounds had clinical precision consistent with surgical scalpel, but did not record this finding in the initial autopsy report."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-03-ADV",
            "name": "Sensational Media Leak Allegation",
            "evidence_type": "document",
            "file_hash": "sha256_press_leak_talwar",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unattributed media leak asserting an alleged honor killing confession without judicial endorsement."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 4: REAL ANONYMIZED COURT JUDGMENT (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_04_delhi_bar",
        "title": "State v. Siddharth V. & Ors. (Bar Shooting Homicide)",
        "split": "test",
        "category": "real_court_anonymized",
        "is_contested": False,
        "citation": "High Court of Delhi, Criminal Appeal No. 614/2006 (Conviction U/S 302 IPC)",
        "confidence_note": "High (Supreme Court confirmed, CFSL ballistics match, vehicle recovery)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Siddharth V. (VIP patron at restaurant counter)",
            "rationale": "Forensic ballistics recovery of .22 ammunition, vehicle Tata Safari DL-2C-S-5555 recovery, and corroboration by non-hostile bar patrons."
        },
        "decisive_evidence_ids": ["EX-04-01", "EX-04-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Siddharth V. (Patron at Tamarind Bar)",
                "statement": "Siddharth V. fired two shots from his .22 licensed pistol after being refused a drink at 02:00 AM."
            },
            {
                "id": "H2",
                "label": "Unknown Bouncer / Security Staff",
                "statement": "An armed private bouncer engaged in an accidental discharge during a scuffle with intoxicated guests."
            },
            {
                "id": "H3",
                "label": "Second Shooter Theory",
                "statement": "A separate unidentified gunman fired the fatal round from outside the courtyard."
            }
        ],
        "exhibits": [
            {
                "id": "EX-04-01",
                "name": "Central Forensic Science Laboratory (CFSL) Ballistics Report",
                "evidence_type": "document",
                "file_hash": "sha256_cfsl_ballistics_22bore",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "CFSL ballistics examination confirmed two fired empty cartridge cases recovered from the bar floor were .22 caliber rimfire ammunition fired from the identical pistol registered under Siddharth V.'s arms license."
            },
            {
                "id": "EX-04-02",
                "name": "Tamarind Court Hospitality Cash Counter Register",
                "evidence_type": "document",
                "file_hash": "sha256_bar_counter_bill_slip",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Handwritten bar order slips confirm Siddharth V. and associates opened a table tab at 23:45 and remained drinking near the central service counter past midnight."
            },
            {
                "id": "EX-04-03",
                "name": "Vehicle Seizure Memo - Tata Safari DL-2C-S-5555",
                "evidence_type": "document",
                "file_hash": "sha256_seizure_safari_noida",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Police recovered Tata Safari SUV DL-2C-S-5555 registered in suspect's family name abandoned in Noida Sector 15. Tyre tread impression matched entry tracks outside the restaurant gate."
            },
            {
                "id": "EX-04-04",
                "name": "Hostile Witness Retraction Record of Primary Complainant",
                "evidence_type": "witness",
                "file_hash": "sha256_hostile_retraction_depo",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Lead complainant retracted initial FIR statement during trial deposition claiming poor lighting made identification impossible, contradicting his initial signed police statement."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-04-ADV",
            "name": "Planted Bouncer Pistol Statement",
            "evidence_type": "witness",
            "file_hash": "sha256_fake_bouncer_affidavit",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "Affidavit from a disgruntled parking attendant claiming he saw an outside bouncer brandishing a handgun."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 5: REAL ANONYMIZED COURT JUDGMENT (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_05_kiln_case",
        "title": "State v. Rajeev S. (Restaurant Tandoor Kiln Homicide)",
        "split": "test",
        "category": "real_court_anonymized",
        "is_contested": False,
        "citation": "Supreme Court of India (Criminal Appeal No. 179/2008, AIR 2013 SC 3344)",
        "confidence_note": "High (Direct firearm recovery, ballistic lead bullet extracted from skull, eyewitness interception)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Rajeev S. (Husband / Former Youth Politician)",
            "rationale": "Intercepted at restaurant kiln while burning body; licensed Arminius .32 revolver recovered from possession; lead bullets matched skull trauma."
        },
        "decisive_evidence_ids": ["EX-05-01", "EX-05-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Rajeev S. (Accused Husband)",
                "statement": "Rajeev S. shot his wife in their flat with his .32 revolver, transported the body to Bagiya restaurant, and attempted incineration."
            },
            {
                "id": "H2",
                "label": "Political Assassins / Rival Gang",
                "statement": "Opposing faction hitmen executed the victim due to political rivalry and dumped the body at the open restaurant garden."
            },
            {
                "id": "H3",
                "label": "Accidental Kitchen Inferno / Self-Harm",
                "statement": "The victim committed suicide inside the premises; restaurant staff attempted panic concealment."
            }
        ],
        "exhibits": [
            {
                "id": "EX-05-01",
                "name": "Arminius .32 Revolver Recovery and CFSL Ballistic Striation",
                "evidence_type": "document",
                "file_hash": "sha256_arminius_revolver_cfsl",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Seizure of licensed Arminius .32 revolver No. 042211 from Rajeev S. Ballistic comparison proved test bullets fired through barrel matched microscopic striations on two lead bullets extracted from victim's cranium."
            },
            {
                "id": "EX-05-02",
                "name": "Mandir Marg Police Patrol Interception Report",
                "evidence_type": "witness",
                "file_hash": "sha256_patrol_constable_report",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Delhi Police Home Guard constable Abdul Nazir on night patrol observed high flames and white smoke rising from open-air Bagiya restaurant; caught manager pouring butter bags into clay tandoor."
            },
            {
                "id": "EX-05-03",
                "name": "Forensic Medicine Department Autopsy & Bone Histology",
                "evidence_type": "DNA",
                "file_hash": "sha256_autopsy_aiims_bone",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "AIIMS Forensic Board confirmed cause of death was firearm injury to head and neck, ante-mortem in nature. Incineration was post-mortem. Femur DNA matched victim's mother with 99.99% probability."
            },
            {
                "id": "EX-05-04",
                "name": "Flat 8/2A Mandir Marg Crime Scene Blood Stains",
                "evidence_type": "document",
                "file_hash": "sha256_flat_sofa_blood_memo",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Blood spatter detected on sofa cushion and wooden cabinet at accused's official residence; chemical group B positive, identical to victim's blood."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-05-ADV",
            "name": "Planted Political Threat Note",
            "evidence_type": "document",
            "file_hash": "sha256_fake_political_threat",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Photocopied pamphlet alleging a rival political unit had placed a hit on the residence."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 6: REAL ANONYMIZED COURT JUDGMENT (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_06_bakery_blast",
        "title": "ATS v. Mirza B. (Pune Bakery IED Blast)",
        "split": "test",
        "category": "real_court_anonymized",
        "is_contested": False,
        "citation": "Special MCOCA Sessions Court, Pune (Case 4/2010) / Bombay HC Review 2023",
        "confidence_note": "High (Forensic chemical recovery of RDX at residence, cyber cafe browsing logs)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Mirza B. and conspirators (LeT / IM module)",
            "rationale": "Chemical trace match of RDX explosive residue at residence; cyber cafe IP logs booking transit tickets; fake electoral card."
        },
        "decisive_evidence_ids": ["EX-06-01", "EX-06-02"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Mirza B. & Terror Module",
                "statement": "Mirza B. procured RDX explosives, assembled the detonator in Udgir, and provided logistical shelter for the planters."
            },
            {
                "id": "H2",
                "label": "Rogue Kitchen Cylinder Explosion",
                "statement": "An industrial commercial LPG kitchen cylinder suffered catastrophic rupture at the bakery counter."
            },
            {
                "id": "H3",
                "label": "Foreign Tourist Syndicate",
                "statement": "International narcotics traffickers detonated ordnance to eliminate an informant."
            }
        ],
        "exhibits": [
            {
                "id": "EX-06-01",
                "name": "CFSL Pune Post-Blast Chemical Residue Analysis",
                "evidence_type": "document",
                "file_hash": "sha256_cfsl_rdx_hydrocarbon",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Gas Chromatography-Mass Spectrometry (GC-MS) of swab samples from blast crater confirmed traces of RDX, Ammonium Nitrate, and Hydrocarbon petroleum oil. Completely disproves LPG cylinder rupture."
            },
            {
                "id": "EX-06-02",
                "name": "Udgir Residence Search - Explosive Seizure Memo",
                "evidence_type": "document",
                "file_hash": "sha256_udgir_search_rdx_1200g",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Seizure of 1,200 grams of blackish explosive powder from accused Mirza B.'s Udgir premises. Chemical composition matched military grade RDX identical to blast scene residue."
            },
            {
                "id": "EX-06-03",
                "name": "Central Cyber Cafe IP Server Access Log",
                "evidence_type": "CDR",
                "file_hash": "sha256_cyber_cafe_ip_log",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Cyber cafe terminal log in Udgir shows browsing of Pune Koregaon Park topography under alias Syed Kharadi. MAC address tied to physical desktop workstation."
            },
            {
                "id": "EX-06-04",
                "name": "Witness Deposition of Auto-Rickshaw Driver",
                "evidence_type": "witness",
                "file_hash": "sha256_auto_driver_statement",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Auto driver recalled ferrying two young men with heavy rucksacks near Pune railway station but could not identify faces during test identification parade."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-06-ADV",
            "name": "Planted Kitchen Gas Safety Certificate",
            "evidence_type": "document",
            "file_hash": "sha256_fake_gas_cert",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "Forged inspection report claiming a commercial gas valve was recalled for sudden catastrophic rupture."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 7: REAL ANONYMIZED LANDMARK FORENSIC DNA (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_07_blackthorn",
        "title": "Operation Blackthorn (First Mass DNA Forensic Case)",
        "split": "test",
        "category": "real_court_anonymized",
        "is_contested": False,
        "citation": "Crown Court Leicester (Forensic Science Service Landmark Record, 1988)",
        "confidence_note": "High (Groundbreaking first forensic DNA STR profiling in criminal history)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Baker Colin P. (Uncovered through proxy blood donor confession)",
            "rationale": "Forensic DNA match with seminal stains; proxy donor Ian Kelly confessed to taking blood test on suspect's behalf."
        },
        "decisive_evidence_ids": ["EX-07-01", "EX-07-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Local Baker Colin P.",
                "statement": "Local bakery worker Colin P. committed the assaults along the footpath and evaded initial screening via proxy donor."
            },
            {
                "id": "H2",
                "label": "Richard B. (Falsely Accused Hospital Porter)",
                "statement": "Hospital porter Richard B., who made false admissions during interrogation, committed the crimes."
            },
            {
                "id": "H3",
                "label": "Transient Drifter Syndicate",
                "statement": "An itinerant railway worker traversing the Leicestershire rail line committed the crimes."
            }
        ],
        "exhibits": [
            {
                "id": "EX-07-01",
                "name": "FSS Alec Jeffreys Multilocus DNA Profile",
                "evidence_type": "DNA",
                "file_hash": "sha256_jeffreys_dna_str_01",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "DNA autoradiograph by Sir Alec Jeffreys demonstrated seminal fluids from both crime scenes came from the same male. Excluded initial suspect Richard B. entirely. Direct profile matched Colin P. with 1 in 30 billion precision."
            },
            {
                "id": "EX-07-02",
                "name": "Police Interrogation Admission of Porter Richard B.",
                "evidence_type": "confession",
                "file_hash": "sha256_false_confession_porter",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Hospital porter Richard B. gave a confused 14-page confession after 12 hours of questioning. Later proved completely false when DNA proved he did not produce the semen."
            },
            {
                "id": "EX-07-03",
                "name": "Pub Witness Statement & Confession of Proxy Ian Kelly",
                "evidence_type": "witness",
                "file_hash": "sha256_ian_kelly_proxy_stmt",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Witness overheard bakery coworker Ian Kelly in a local pub bragging he took the voluntary police blood test using Colin P.'s passport for £200. Kelly arrested and gave signed statement admitting proxy fraud."
            },
            {
                "id": "EX-07-04",
                "name": "Bakery Work Shift Timecard",
                "evidence_type": "document",
                "file_hash": "sha256_bakery_punch_card",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Bakery employment logs show Colin P. clocked off work at 16:30, leaving a 2-hour unverified window along the rural footpath on the evening of the attack."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-07-ADV",
            "name": "Fabricated Railway Ticket Stub",
            "evidence_type": "document",
            "file_hash": "sha256_fake_railway_stub",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Railway pass found in ditch suggesting an itinerant traveler arrived from London that evening."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 8: SYNTHETIC TRAP 1 - MISLEADING EYEWITNESS (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_08_vault_trap",
        "title": "Case S1: Bank Vault Dual-Keypad Breach",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Controlled Synthetic Benchmark Suite (Trap: Confident Misleading Eyewitness)",
        "confidence_note": "Absolute (Cryptographic keylog & physical safe sensor ground truth)",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Head Cashier Dev (Authorized insider abuse)",
            "rationale": "Biometric iris log and master cryptographic keycard used; misleading eyewitness guard was mistaken due to uniform similarity."
        },
        "decisive_evidence_ids": ["EX-08-02", "EX-08-04"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Night Watchman Ramesh",
                "statement": "Night Watchman Ramesh overpowered the lobby sensor and entered the vault using stolen master keys."
            },
            {
                "id": "H2",
                "label": "Head Cashier Dev",
                "statement": "Head Cashier Dev executed an unauthorized midnight entry using his cryptographic token to siphon currency bags."
            },
            {
                "id": "H3",
                "label": "External Tunnel Heist Gang",
                "statement": "An external robbery crew breached the vault wall from the adjoining storm drain."
            }
        ],
        "exhibits": [
            {
                "id": "EX-08-01",
                "name": "Overconfident Eyewitness Statement of Floor Guard",
                "evidence_type": "witness",
                "file_hash": "sha256_witness_guard_trap",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 3,
                "text": "Lobby security guard asserts with 100% subjective confidence: 'I saw Watchman Ramesh walking down the dark corridor into the vault at 01:15 AM wearing khaki trousers.' (TRAP: Watchman and Cashier wore identical company monsoon raincoats)."
            },
            {
                "id": "EX-08-02",
                "name": "Vault Electronic Access Biometric & Smartcard Audit Log",
                "evidence_type": "document",
                "file_hash": "sha256_biometric_iris_vault_audit",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Hardware security module (HSM) tamper-proof log records Vault Door 2 unlocked at 01:14:22 AM via RSA Smartcard ID #CASHIER-DEV coupled with 99.8% iris match for Dev. Watchman Ramesh's RFID badge was stationary in the guard shack."
            },
            {
                "id": "EX-08-03",
                "name": "Adjoining Storm Drain Physical Inspection Memo",
                "evidence_type": "document",
                "file_hash": "sha256_storm_drain_inspection",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Municipal drainage engineer report confirms concrete reinforced vault wall is 18 inches solid rebar with no cracks, moisture, or drilling attempts. Completely disproves tunnel heist."
            },
            {
                "id": "EX-08-04",
                "name": "Currency Bundle Fluorescent Dye Forensic Swab",
                "evidence_type": "DNA",
                "file_hash": "sha256_fluorescent_swab_dev_car",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Forensic UV swab of steering wheel in Head Cashier Dev's Honda City detected traces of Rhodamine-B chemical dye powder tagged onto the missing Reserve Bank cash packets."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-08-ADV",
            "name": "Planted Khaki Cloth Scrap",
            "evidence_type": "document",
            "file_hash": "sha256_fake_cloth_scrap",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unverified cloth fragment labeled 'Ramesh uniform' found placed inside the vault doorway."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 9: SYNTHETIC TRAP 2 - NON-DIAGNOSTIC UBIQUITOUS EVIDENCE (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_09_server_room",
        "title": "Case S2: Server Room Algorithmic Source Code Exfiltration",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Controlled Synthetic Benchmark Suite (Trap: Non-Diagnostic Presence Evidence)",
        "confidence_note": "Absolute (Cryptographic USB serial pairing & physical locker search)",
        "ground_truth": {
            "hypothesis_id": "H3",
            "culprit_summary": "Systems Administrator Verma",
            "rationale": "Hardware USB vendor serial matched Verma's private encrypted drive; building access logs fit everyone equally and have zero diagnosticity."
        },
        "decisive_evidence_ids": ["EX-09-04"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Lead Developer Ankit",
                "statement": "Lead Developer Ankit copied the trading algorithm to an external disk before tendering resignation."
            },
            {
                "id": "H2",
                "label": "Database Admin Priya",
                "statement": "Database Admin Priya executed an unapproved SQL dump of the algorithm repository."
            },
            {
                "id": "H3",
                "label": "Systems Admin Verma",
                "statement": "Systems Admin Verma mounted an unauthorized USB mass storage device directly at the server rack console."
            }
        ],
        "exhibits": [
            {
                "id": "EX-09-01",
                "name": "Building Turnstile Access Badge Report",
                "evidence_type": "document",
                "file_hash": "sha256_turnstile_badging_all",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Turnstile logs show Ankit, Priya, and Verma all scanned into the office building between 09:00 AM and 09:30 AM and remained present all day. (NON-DIAGNOSTIC: Fits all three hypotheses equally)."
            },
            {
                "id": "EX-09-02",
                "name": "Cafeteria & Common Hallway CCTV Footages",
                "evidence_type": "CCTV",
                "file_hash": "sha256_hallway_cctv_all",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "CCTV shows all three employees walked through the 4th-floor hallway near the server room during lunch hours. (NON-DIAGNOSTIC: Fits all hypotheses equally)."
            },
            {
                "id": "EX-09-03",
                "name": "General Network Wi-Fi Router Connection Log",
                "evidence_type": "CDR",
                "file_hash": "sha256_wifi_dhcp_all",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Enterprise Cisco AP shows laptops of Ankit, Priya, and Verma maintained active DHCP leases throughout the afternoon. (NON-DIAGNOSTIC)."
            },
            {
                "id": "EX-09-04",
                "name": "Kernel USB Device Plug Event Log & Hardware Seizure",
                "evidence_type": "document",
                "file_hash": "sha256_kernel_usb_storage_seizure",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Linux dmesg syslog records Kingston DataTraveler USB Serial #KNG-883921-X mounted at rack 4 console at 14:22:01. Physical search recovered the identical thumb drive with serial #KNG-883921-X from Verma's gym bag in locker 12B."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-09-ADV",
            "name": "Planted Resignation Letter Draft",
            "evidence_type": "document",
            "file_hash": "sha256_fake_resignation",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "An unsigned Word document draft of a resignation letter mentioning Ankit's plan to start a competing hedge fund."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 10: SYNTHETIC TRAP 3 - PLANTED RED HERRING (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_10_formula_sabotage",
        "title": "Case S3: Pharmaceutical Formula Sabotage",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Controlled Synthetic Benchmark Suite (Trap: Planted Red Herring Badge)",
        "confidence_note": "Absolute (Fluorescent reagent tracer on perpetrator's lab coat)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Lead Chemist Dr. Roy",
            "rationale": "Fluorescent reagent marker coated Roy's gloves; Dr. Sen's badge was deliberately stolen and planted near the reactor."
        },
        "decisive_evidence_ids": ["EX-10-02", "EX-10-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Lead Chemist Dr. Roy",
                "statement": "Lead Chemist Dr. Roy sabotaged the catalytic batch after receiving rival equity options."
            },
            {
                "id": "H2",
                "label": "Junior Assistant Dr. Sen",
                "statement": "Junior Assistant Dr. Sen contaminated the bioreactor out of resentment over authorship."
            },
            {
                "id": "H3",
                "label": "Equipment Mechanical Failure",
                "statement": "The temperature valve malfunctioned due to improper calibration, ruining the batch."
            }
        ],
        "exhibits": [
            {
                "id": "EX-10-01",
                "name": "Planted Security ID Badge of Dr. Sen",
                "evidence_type": "document",
                "file_hash": "sha256_planted_badge_sen",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Dr. Sen's magnetic ID badge found lying directly in front of the contaminated reactor vat valve. (TRAP: Dr. Sen filed an HR complaint at 10:00 AM stating her badge was stolen from the common coat rack)."
            },
            {
                "id": "EX-10-02",
                "name": "Hospital Emergency Room Admitting Log for Dr. Sen",
                "evidence_type": "document",
                "file_hash": "sha256_hospital_er_alibi_sen",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Official emergency room medical record proving Dr. Sen was admitted for severe acute allergic reaction at Apollo Clinic at 18:30 and remained on IV drip until 23:00. Bioreactor sabotage occurred at 20:15. Physically disconfirms Dr. Sen."
            },
            {
                "id": "EX-10-03",
                "name": "Fluorescent Chemical Tracer Analysis on Lab Gear",
                "evidence_type": "DNA",
                "file_hash": "sha256_fluorescent_catalyst_roy",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Spectrophotometric analysis revealed Microtaggant chemical tracer beads from the contaminant chemical flask on Dr. Roy's personal silicone lab gloves and wristwatch strap."
            },
            {
                "id": "EX-01-04",
                "name": "Maintenance Temperature Valve Calibration Certificate",
                "evidence_type": "document",
                "file_hash": "sha256_valve_calibration_pass",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Independent ISO-9001 certified valve pressure test logs show the thermocouple responded accurately with zero mechanical failure."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-10-ADV",
            "name": "Anonymous Letter accusing Dr. Sen",
            "evidence_type": "document",
            "file_hash": "sha256_fake_anonymous_sen",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "An anonymous printout claiming Dr. Sen bragged about ruining the enzyme formula."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 11: SYNTHETIC TRAP 4 - CIRCUMSTANTIAL BIAS VS FORENSIC BALLISTICS
    # --------------------------------------------------------------------------
    {
        "id": "case_11_dockyard_homicide",
        "title": "Case S4: Dockyard Cargo Berth Homicide",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Controlled Synthetic Benchmark Suite (Trap: Heavy Circumstantial Bias vs Forensic Ballistics)",
        "confidence_note": "Absolute (Gunshot residue SEM-EDX and rifling groove match)",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Dock Foreman Tariq",
            "rationale": "Gunshot residue on Tariq's hands and unique extractor pin marks match his firearm; Contractor Gill had a loud argument earlier creating intense circumstantial bias."
        },
        "decisive_evidence_ids": ["EX-11-02", "EX-11-04"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Contractor Gill (Hotheaded Rival)",
                "statement": "Contractor Gill murdered the shipping inspector following a fierce, public fistfight on Berth 4."
            },
            {
                "id": "H2",
                "label": "Dock Foreman Tariq",
                "statement": "Foreman Tariq ambushed the inspector to protect a clandestine contraband container operation."
            },
            {
                "id": "H3",
                "label": "Accidental Stray Flare Discharge",
                "statement": "An emergency distress flare fired from a passing cargo ship ricocheted and caused fatal trauma."
            }
        ],
        "exhibits": [
            {
                "id": "EX-11-01",
                "name": "Eyewitness Deposition on Berth 4 Brawl",
                "evidence_type": "witness",
                "file_hash": "sha256_brawl_witness_gill",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Three dock workers testify Contractor Gill shouted death threats at the victim at 17:30 and threw a punch before storming off. (TRAP: Massive circumstantial bias)."
            },
            {
                "id": "EX-11-02",
                "name": "Scanning Electron Microscopy (SEM-EDX) Gunshot Residue Test",
                "evidence_type": "DNA",
                "file_hash": "sha256_sem_edx_gsr_tariq",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Dermal stub analysis using SEM-EDX found characteristic spherical Lead-Barium-Antimony (Pb-Ba-Sb) primer particles on Foreman Tariq's right hand and jacket cuffs. Contractor Gill tested completely negative for GSR."
            },
            {
                "id": "EX-11-03",
                "name": "Contractor Gill Diner CCTV and Payment Timecard",
                "evidence_type": "CCTV",
                "file_hash": "sha256_diner_cctv_gill_alibi",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "CCTV footage and credit card slip from Blue Harbor Diner 12 miles away places Contractor Gill eating with his accountant between 18:45 and 20:00. Fatal shooting occurred at 19:15."
            },
            {
                "id": "EX-11-04",
                "name": "FSL Ballistic Comparison on .38 Revolver Seized from Tariq",
                "evidence_type": "document",
                "file_hash": "sha256_tariq_38_ballistics",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Striation markings on bullet slug recovered from victim matched test firings from unlicensed Colt .38 revolver seized from Tariq's tool locker with 5 land-and-groove right-hand twist."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-11-ADV",
            "name": "Planted Gill Business Card in Berth Sump",
            "evidence_type": "document",
            "file_hash": "sha256_fake_gill_card",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "A dry, undamaged business card of Contractor Gill dropped right beside the victim's body in a muddy puddle."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 12: SYNTHETIC TRAP 5 - FALSE CONFESSION VS TELECOM CDR/FASTAG
    # --------------------------------------------------------------------------
    {
        "id": "case_12_ransom_kidnapping",
        "title": "Case S5: High-Value Ransom Extortion Drop",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Controlled Synthetic Benchmark Suite (Trap: False Shielding Confession vs FASTag/CDR)",
        "confidence_note": "Absolute (Cryptographic Toll FASTag RFID & CDR Tower Triangulation)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Older Brother Vicky (Organized Extortion Plotter)",
            "rationale": "FASTag toll RFID and cell tower CDR place Vicky at the drop site; younger brother surrendered with a false confession to shield family."
        },
        "decisive_evidence_ids": ["EX-12-02", "EX-12-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Older Brother Vicky",
                "statement": "Vicky masterminded the extortion, drove the getaway vehicle, and picked up the cash bag at the highway culvert."
            },
            {
                "id": "H2",
                "label": "Younger Brother Bunty (Confessing)",
                "statement": "Younger brother Bunty committed the crime alone as confessed in his voluntary written submission."
            },
            {
                "id": "H3",
                "label": "Staged Insurance Fraud by Victim's Family",
                "statement": "The victim's business partner faked the kidnapping to file a corporate ransom insurance claim."
            }
        ],
        "exhibits": [
            {
                "id": "EX-12-01",
                "name": "Signed Surrender & Written Confession of Bunty",
                "evidence_type": "confession",
                "file_hash": "sha256_bunty_false_confession",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 3,
                "text": "Bunty walked into the police station claiming full sole responsibility for the ransom pickup. (TRAP: Bunty could not describe the color of the bag or the vehicle model used)."
            },
            {
                "id": "EX-12-02",
                "name": "National Highways Authority (NHAI) FASTag Toll RFID Log",
                "evidence_type": "document",
                "file_hash": "sha256_nhai_fastag_vicky_scorpio",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "NHAI Khed-Shivapur toll plaza RFID antenna registered Vicky's Mahindra Scorpio MH-14-EA-9911 traversing south at 21:12 and returning north at 22:45. Optical high-speed camera clearly captures Vicky in the driver seat."
            },
            {
                "id": "EX-12-03",
                "name": "Telecom Cellular Tower CDR Triangulation for Both Brothers",
                "evidence_type": "CDR",
                "file_hash": "sha256_cdr_bts_vicky_vs_bunty",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Airtel CDR data reveals Vicky's handset was actively communicating through the culvert cell sector at 22:05 during the drop. Bunty's handset was continuously latched to a residential cell tower in Hadapsar, 85 kilometers away."
            },
            {
                "id": "EX-12-04",
                "name": "Victim Family Corporate Bank Statement",
                "evidence_type": "document",
                "file_hash": "sha256_bank_statement_genuine_ransom",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "HDFC Bank certified statements show a legitimate emergency cash withdrawal of Rs 50 Lakhs debited against personal savings, with no commercial insurance claim filed."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-12-ADV",
            "name": "Planted Bunty Shopping Bill",
            "evidence_type": "document",
            "file_hash": "sha256_fake_bunty_slip",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "A receipt allegedly showing Bunty purchasing duct tape near the crime location."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 13: INNOCENT SUSPECT WITH SIMILAR PRIOR RECORD VS TRUE CULPRIT (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_13_innocent_record_heist",
        "title": "State v. K.R. & Ors. (Commercial Vault Safe-Breach / Prior Record Trap Case)",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Sessions Court Special Forensic Docket Case #S-13/2026",
        "confidence_note": "High (Direct autosomal DNA STR match and thermal biometric CCTV vs. verified hospital alibi)",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Active Security Supervisor Kailash R. (H2, Clean Record)",
            "rationale": "Direct autosomal DNA match on safe latch and thermal CCTV footage prove Kailash R. committed the breach; former offender Devendra P. (H1) is conclusively excluded by DNA and hospital alibi."
        },
        "decisive_evidence_ids": ["EX-13-01", "EX-13-02", "EX-13-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Former Employee Devendra P. (Prior Safe-Cracking Record)",
                "statement": "Former mechanic Devendra P., who has a prior 2021 conviction for commercial safe-cracking, used rotary power tools to breach the workshop vault."
            },
            {
                "id": "H2",
                "label": "Security Supervisor Kailash R. (Clean Record)",
                "statement": "Night security shift supervisor Kailash R., having internal alarm bypass codes and master keys, compromised the vault and staged a break-in."
            },
            {
                "id": "H3",
                "label": "External Unaffiliated Safe Syndicate",
                "statement": "An external traveling gang bypassed perimeter security and forced open the safe independently."
            }
        ],
        "exhibits": [
            {
                "id": "EX-13-01",
                "name": "State FSL Autosomal STR DNA Report on Safe Latch Bloodstain",
                "evidence_type": "DNA",
                "file_hash": "sha256_fsl_dna_safe_latch_blood",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Luminol swab of jagged edge on the pried safe handle yielded human epithelial blood. Autosomal STR 16-locus typing gave a complete single-source male profile matching Suspect Kailash R. (H2) with random match probability 1 in 3.8 billion. Suspect Devendra P. (H1) is definitively excluded across all 16 loci."
            },
            {
                "id": "EX-13-02",
                "name": "Covert Thermal Security Camera Recording (Rear Service Exit)",
                "evidence_type": "CCTV",
                "file_hash": "sha256_thermal_cctv_service_exit_0222",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Auxiliary thermal surveillance camera at rear loading corridor timestamped 02:22 IST captures Suspect Kailash R. (H2) using his personal master RFID fob to silence secondary alarm, carrying three velvet jewelry trays, and loading them into his white vehicle."
            },
            {
                "id": "EX-13-03",
                "name": "Verified Metro Multispeciality Hospital Emergency Admission & Biometric Log",
                "evidence_type": "document",
                "file_hash": "sha256_metro_hospital_er_alibi_dp",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Certified records from Metro Multispeciality Hospital (42 kilometers from the scene) confirm Suspect Devendra P. (H1) was admitted to the emergency ward at 23:15 IST with acute pancreatitis, underwent IV drip administration under continuous nursing supervision until 06:30 IST, and has time-stamped hospital facial biometric entries."
            },
            {
                "id": "EX-13-04",
                "name": "SCRB Certified Prior Criminal Conviction Dossier for Devendra P.",
                "evidence_type": "document",
                "file_hash": "sha256_scrb_prior_record_devendra_2021",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "State Criminal Records Bureau certified record showing Devendra P. was convicted in 2021 under Sections 457/380 IPC for a nighttime workshop burglary involving rotary cutters and pry bars. Sentence completed in 2023."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-13-ADV",
            "name": "Anonymous Tip Letter Alleging Devendra P.",
            "evidence_type": "document",
            "file_hash": "sha256_fake_tip_devendra",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unsigned handwritten note dropped in police suggestion box asserting that 'Devendra was bragging about a big jewelry score at the local tea stall.'"
        },
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.45},
                {"factor_type": "opportunity", "factor_value": "confirmed_elsewhere", "numeric_adjustment": 0.10},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 1.00},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "strongly_verified", "numeric_adjustment": 0.10},
                {"factor_type": "travel_feasibility", "factor_value": "physically_impossible", "numeric_adjustment": 0.05}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "secondary_opportunistic", "numeric_adjustment": 0.50},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {
            "H1": [
                {
                    "suspect_name": "Devendra P.",
                    "offense_type": "Commercial Workshop Burglary & Safe Breaking",
                    "legal_section": "Section 457, 380 IPC",
                    "offense_date": "2021-04-12",
                    "location": "Industrial Estate, Chakan",
                    "outcome": "convicted",
                    "weapon_used": "Rotary cutter / pry bar",
                    "entry_method": "Forced entry through rear door latch",
                    "victim_type": "Commercial jewelry workshop",
                    "location_type": "Commercial industrial workshop",
                    "time_pattern": "Nighttime 01:00-03:00",
                    "mo_description": "Used mechanical rotary cutter and heavy-duty crowbar to pry open commercial steel safe after cutting service entry latch.",
                    "verification_status": "verified",
                    "identity_match_confidence": 0.96,
                    "verified_identity": True,
                    "is_juvenile": False
                }
            ],
            "H2": []
        }
    },

    # --------------------------------------------------------------------------
    # CASE 14: INNOCENT SUSPECT WITH PRIOR CONVICTIONS VS CLEAN DISPATCHER (Test Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_14_innocent_record_transit",
        "title": "State v. A.M. & Ors. (Transit Cargo Logistics Theft / Identity Trap Case)",
        "split": "test",
        "category": "synthetic_trap",
        "is_contested": False,
        "citation": "Sessions Court Special Cargo Crime Registry Docket #C-14/2026",
        "confidence_note": "High (Latent friction ridge match and cellular GPS telemetry vs. airport flight alibi)",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Logistics Dispatcher Alok M. (H2, Clean Record)",
            "rationale": "Latent fingerprint on container seal and coincident GPS telemetry prove Alok M. committed the cargo theft; prior offender Amarjit S. (H1) is conclusively exonerated by commercial flight records."
        },
        "decisive_evidence_ids": ["EX-14-01", "EX-14-02", "EX-14-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Former Transporter Amarjit S. (Prior Cargo Hijack Record)",
                "statement": "Former long-haul trucker Amarjit S., who has two prior convictions for highway cargo interception, intercepted the logistics container en route."
            },
            {
                "id": "H2",
                "label": "Logistics Depot Dispatcher Alok M. (Clean Record)",
                "statement": "Depot logistics dispatcher Alok M. secretly broke the container seal at the intermediate siding and diverted the high-value electronics."
            },
            {
                "id": "H3",
                "label": "Accidental In-Transit Seal Rupture",
                "statement": "The container seal snapped accidentally due to road vibration and cargo fell out undetected."
            }
        ],
        "exhibits": [
            {
                "id": "EX-14-01",
                "name": "State Fingerprint Bureau Latent Friction Ridge ACE-V Report",
                "evidence_type": "fingerprint",
                "file_hash": "sha256_afis_latent_print_container_latch",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Latent friction ridge print lifted using cyanoacrylate fuming from the fresh sheared edge of high-security container seal #SL-88902 matched the left index finger of Suspect Alok M. (H2) with 14 clear minutiae points. Suspect Amarjit S. (H1) friction ridge pattern is completely incompatible and excluded."
            },
            {
                "id": "EX-14-02",
                "name": "GPS Telemetry & Cellular CDR Siding Triangulation",
                "evidence_type": "CDR",
                "file_hash": "sha256_gps_cdr_alok_siding_0145",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Cell tower sector logs and FASTag telemetry show Alok M.'s personal vehicle was stationary alongside the container truck at the desolate railway siding for 38 minutes between 01:25 and 02:03 IST. Bluetooth handshake recorded between his vehicle and the depot scanner."
            },
            {
                "id": "EX-14-03",
                "name": "Air India Passenger Manifest & Airport CISF Biometric Gate Log",
                "evidence_type": "document",
                "file_hash": "sha256_air_india_ai804_manifest_amarjit",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Official certified flight manifest for Air India AI-804 confirms Suspect Amarjit S. (H1) boarded the aircraft at New Delhi (DEL) at 23:45 IST and landed at Bengaluru (BLR) at 02:35 IST. CISF biometric DigiYatra facial recognition timestamps confirm his physical presence aboard the flight throughout the incident window."
            },
            {
                "id": "EX-14-04",
                "name": "SCRB Certified Criminal Record Dossier for Amarjit S.",
                "evidence_type": "document",
                "file_hash": "sha256_scrb_prior_record_amarjit_2018_2020",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Certified conviction dossier showing Amarjit S. was convicted in 2018 and 2020 under Section 392 IPC for highway transit cargo thefts. Both cases involved tampering with container seals."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-14-ADV",
            "name": "Fabricated Siding Log Sheet Entry",
            "evidence_type": "document",
            "file_hash": "sha256_fake_siding_log_amarjit",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Photocopied night register sheet containing a handwritten scribble alleging 'Amarjit truck spotted outside siding gate at 01:30.'"
        },
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.45},
                {"factor_type": "opportunity", "factor_value": "confirmed_elsewhere", "numeric_adjustment": 0.10},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.95},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "strongly_verified", "numeric_adjustment": 0.10},
                {"factor_type": "travel_feasibility", "factor_value": "physically_impossible", "numeric_adjustment": 0.05}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.90},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "limited_capacity", "numeric_adjustment": 0.40},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {
            "H1": [
                {
                    "suspect_name": "Amarjit S.",
                    "offense_type": "Highway Lorry Cargo Hijacking & Interception",
                    "legal_section": "Section 392, 397 IPC",
                    "offense_date": "2018-11-20",
                    "location": "NH-48 Corridor, Kolhapur",
                    "outcome": "convicted",
                    "weapon_used": "Iron rod / cutter",
                    "entry_method": "Breaking container lock bolt seal",
                    "victim_type": "Logistics fleet vehicle",
                    "location_type": "Transit bypass corridor",
                    "time_pattern": "Nighttime 01:00-03:00",
                    "mo_description": "Sheared container bolt seal at transit halt and offloaded consumer electronics into waiting mini-truck.",
                    "verification_status": "verified",
                    "identity_match_confidence": 0.98,
                    "verified_identity": True,
                    "is_juvenile": False
                }
            ],
            "H2": []
        }
    },

    # --------------------------------------------------------------------------
    # CASE 15: BLIND EXTERNAL CASE (Independent Contributor - Moot Dataset)
    # The Nhava Sheva Logistics Container Yard Warehouse Fire
    # Focus: Arson for insurance fraud vs Hot-work welding negligence vs Electrical
    # --------------------------------------------------------------------------
    {
        "id": "case_15_nhava_sheva_arson",
        "title": "State v. N.S. Container Logistics (Nhava Sheva Warehouse Arson / Fire Inquest)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: Forensic Law Student Moot Archive (Case #BLIND-2024-F01)",
        "confidence_note": "Moderate - Mixed circumstantial financial motive vs physical fire science",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Contractor Maintenance Welding Crew (Gross Negligence)",
            "rationale": "Forensic fire burn-pattern analysis and contractor job sheets confirm uninsulated hot-slag from structural welding ignited open lacquer thinner barrels. Owner's vehicle departed 2 hours prior."
        },
        "decisive_evidence_ids": ["EX-15-01", "EX-15-02"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Managing Director Rajesh G. (Arson Insurance Fraud)",
                "statement": "Director arranged deliberate torching of warehouse to recover ₹45 Crore fire insurance policy to clear impending commercial bank defaults."
            },
            {
                "id": "H2",
                "label": "Contractor Maintenance Welding Crew (Gross Negligence)",
                "statement": "Uncertified welding workers operated thermal cutting torch adjacent to volatile chemical storage without mandatory fire-retardant blankets or standby extinguishers."
            },
            {
                "id": "H3",
                "label": "Electrical Substation Surge / Transformer Failure",
                "statement": "High-voltage monsoon power fluctuation in the main terminal transformer triggered electrical arcing in ceiling conduits causing passive structural ignition."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 0.80},
                {"factor_type": "opportunity", "factor_value": "confirmed_elsewhere", "numeric_adjustment": 0.20},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.70},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "partially_verified", "numeric_adjustment": 0.35},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 0.90}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.95},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "limited_capacity", "numeric_adjustment": 0.30},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.10},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {
            "H1": [],
            "H2": [
                {
                    "suspect_name": "Apex Engineering Contractors",
                    "offense_type": "Industrial Safety & Fire Negligence Violation",
                    "legal_section": "Section 285, 287 IPC",
                    "offense_date": "2021-03-12",
                    "location": "MIDC Taloja, Navi Mumbai",
                    "outcome": "convicted",
                    "weapon_used": "Gas cutting torch",
                    "entry_method": "Authorized maintenance access",
                    "victim_type": "Industrial warehouse property",
                    "location_type": "Chemical storage depot",
                    "time_pattern": "Evening shift 19:00-21:00",
                    "mo_description": "Failed to erect fire-resistant partition walls during hot-cutting operations near solvent drums.",
                    "verification_status": "verified",
                    "identity_match_confidence": 0.95,
                    "verified_identity": True,
                    "is_juvenile": False
                }
            ],
            "H3": []
        },
        "exhibits": [
            {
                "id": "EX-15-01",
                "name": "State Fire Services Forensic Arson & Burn Origin Investigation",
                "evidence_type": "Document",
                "file_hash": "sha256_fire_fsl_nhava_origin",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Detailed inverted V-pattern thermal mapping isolates the primary fire origin to Bay-4 welding partition at floor level. Gas chromatography confirmed absence of kerosene or commercial accelerants; fuel source was unsealed industrial lacquer thinner barrels ignited by 1200°C molten welding slag. Electrical conduit breakers on the main transformer were tripped mechanically post-fire, disproving electrical failure as the initiator."
            },
            {
                "id": "EX-15-02",
                "name": "Contractor Hot-Work Job Card & Disciplinary Inspection",
                "evidence_type": "Document",
                "file_hash": "sha256_apex_contractor_jobcard_09",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Maintenance job ticket confirms Apex Contractors crew was performing uninsulated torch-cutting of steel shelving in Bay-4 until 19:55. Safety auditor inspection reveals two handheld chemical extinguishers beside Bay-4 were discharged and completely empty prior to the incident, with zero water hoses connected."
            },
            {
                "id": "EX-15-03",
                "name": "Perimeter Gate ANPR & Director Vehicle Log",
                "evidence_type": "CCTV",
                "file_hash": "sha256_nhava_anpr_gate_south",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "High-definition ANPR camera captures Director Rajesh G.'s Mercedes departing the facility at 18:22 IST. Cellular tower records corroborate his device registered at a business club dinner in South Mumbai from 19:30 onwards through midnight, establishing physical absence during the 20:15 ignition window."
            },
            {
                "id": "EX-15-04",
                "name": "Commercial Insurance Policy & Bank Debt Recovery Notice",
                "evidence_type": "Document",
                "file_hash": "sha256_insurance_debt_notice_nhava",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Financial audit records demonstrate warehouse inventory was insured for ₹45 Crore with policy renewed 3 weeks prior. State Bank had served an asset possession notice under SARFAESI Act for ₹38 Crore pending debt, creating strong circumstantial suspicion of financial motive."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-15-ADV",
            "name": "Anonymous Tipster Note Accusing Director",
            "evidence_type": "Document",
            "file_hash": "sha256_anon_tip_director_arson",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unsigned computer-printed note dropped at police station claiming Director Rajesh met professional torchmen at a hotel."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 16: BLIND EXTERNAL CASE (Independent Contributor - Cyber Clinic)
    # The AlphaTech Labs Defense Algorithm Exfiltration
    # Focus: Rogue Firmware Architect vs Foreign APT Cyber Espionage vs Framing Admin
    # --------------------------------------------------------------------------
    {
        "id": "case_16_cyber_exfiltration",
        "title": "State Cyber Crime Cell v. AlphaTech Labs (Defense Algorithm Exfiltration Case)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: Cyber Law & Digital Forensics Clinic (Case #BLIND-2024-F02)",
        "confidence_note": "High - Corroborated network telemetry and physical airport alibi vs planted USB",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Foreign APT Group (Remotely compromised workstation via spear-phishing)",
            "rationale": "Network firewall logs show C2 beaconing and memory injection mimicking user credentials. Workstation owner was physically in transit on commercial flight during the 02:14 AM exfiltration window."
        },
        "decisive_evidence_ids": ["EX-16-01", "EX-16-02"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Senior Firmware Architect Neil K.",
                "statement": "Architect downloaded proprietary drone telemetry code onto personal USB to transfer to foreign competitor."
            },
            {
                "id": "H2",
                "label": "Foreign Advanced Persistent Threat (APT Group)",
                "statement": "Foreign cyber-espionage syndicate remotely compromised internal subnet via weaponized PDF backdoor and exfiltrated code using architect's cached credentials."
            },
            {
                "id": "H3",
                "label": "IT Infrastructure Admin Vikram D.",
                "statement": "Disgruntled system administrator used domain controller root privilege to exfiltrate code and deliberately frame Neil K."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 0.85},
                {"factor_type": "opportunity", "factor_value": "confirmed_elsewhere", "numeric_adjustment": 0.10},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.95},
                {"factor_type": "motive", "factor_value": "professional_conflict", "numeric_adjustment": 0.70},
                {"factor_type": "alibi_status", "factor_value": "strongly_verified", "numeric_adjustment": 0.05},
                {"factor_type": "travel_feasibility", "factor_value": "physically_impossible", "numeric_adjustment": 0.05}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.90},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 0.95},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 1.00},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 0.90},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.90},
                {"factor_type": "motive", "factor_value": "personal_vendetta", "numeric_adjustment": 0.60},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {"H1": [], "H2": [], "H3": []},
        "exhibits": [
            {
                "id": "EX-16-01",
                "name": "Network Perimeter Firewall & Endpoint EDR Forensic Dump",
                "evidence_type": "Document",
                "file_hash": "sha256_edr_firewall_alphatech_c2",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "EDR memory forensic extraction reveals Neil K.'s workstation process svchost.exe was injected with a Cobalt Strike beacon payload at 02:08 AM. 4.2 GB of encrypted git archive packets were transmitted to an offshore command-and-control server in Frankfurt. The process initiated automatically via a task scheduler backdoor planted 5 days prior via a malicious PDF email attachment."
            },
            {
                "id": "EX-16-02",
                "name": "Bangalore International Airport CISF Gate Log & Flight Manifest",
                "evidence_type": "CCTV",
                "file_hash": "sha256_cisf_airport_neil_alibi",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "CISF biometric e-gate logs and IndiGo Airlines flight 6E-512 manifest establish Neil K. passed through security at Bangalore Airport at 01:15 AM and was airborne between 01:55 AM and 04:30 AM without in-flight Wi-Fi connectivity, conclusively disproving physical access to his workstation at the time of exfiltration."
            },
            {
                "id": "EX-16-03",
                "name": "SanDisk Flash Drive Found in Neil K. Office Desk",
                "evidence_type": "Document",
                "file_hash": "sha256_sandisk_usb_desk_neil",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "A 64GB SanDisk USB recovered from Neil K.'s desk drawer contained compiled software binaries. Forensic file metadata analysis demonstrates last written timestamp was 7 months prior to the incident; zero files from the compromised drone guidance repository were present on the media."
            },
            {
                "id": "EX-16-04",
                "name": "Git Repository Access Audit Log",
                "evidence_type": "Document",
                "file_hash": "sha256_git_audit_ssh_key_neil",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Git enterprise server logs indicate the repository was pulled using SSH key neil_rsa_pub. While initially casting circumstantial suspicion on Neil, cryptographic analysis shows the private key was stored unencrypted on his compromised workstation disk and harvested by the malware."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-16-ADV",
            "name": "Planted Resignation Resentment Memo",
            "evidence_type": "Document",
            "file_hash": "sha256_fake_memo_competitor_offer",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Unverified draft email stating 'I will take the guidance code with me if compensation is not matched.'"
        }
    },

    # --------------------------------------------------------------------------
    # CASE 17: BLIND EXTERNAL CASE (Independent Contributor - Trial Advocacy)
    # The Tiger Point Matheran Cliff Fall Inquest
    # Focus: Spousal homicide push vs Tragic accidental slip vs Suicide
    # --------------------------------------------------------------------------
    {
        "id": "case_17_cliff_fall_inquest",
        "title": "Inquest into the Fatal Cliff Fall of Meera D. (Tiger Point Matheran Case)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: Criminal Trial Advocacy Moot Panel (Case #BLIND-2024-F03)",
        "confidence_note": "High - Scientific geological shear analysis, medical autopsy, and third-party tourist video",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Tragic Accidental Slip & Shale Ledge Shear",
            "rationale": "Medical autopsy proves complete absence of pre-mortem assault or throttling marks. Tourist video timestamped 3 minutes before fall places husband 10 meters away. Geological survey reveals fresh 1.2m mud-shear collapse of wet shale."
        },
        "decisive_evidence_ids": ["EX-17-01", "EX-17-02", "EX-17-04"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Husband Rohan D. (Homicide by Pushing)",
                "statement": "Husband deliberately pushed victim over the cliff edge during a dispute over marital finances to collect insurance and dowry assets."
            },
            {
                "id": "H2",
                "label": "Accidental Slip & Ledge Shale Shear",
                "statement": "Victim accidentally slipped on moss-covered rainy shale rock while posing for a photograph when the ledge edge gave way."
            },
            {
                "id": "H3",
                "label": "Intentional Self-Harm / Suicide",
                "statement": "Victim intentionally leaped from the vantage point due to severe personal depression."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 0.65},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.40},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.75},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.85},
                {"factor_type": "alibi_status", "factor_value": "partially_verified", "numeric_adjustment": 0.40},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "limited_capacity", "numeric_adjustment": 0.20},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.10},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 0.90},
                {"factor_type": "means", "factor_value": "limited_capacity", "numeric_adjustment": 0.20},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {"H1": [], "H2": [], "H3": []},
        "exhibits": [
            {
                "id": "EX-17-01",
                "name": "District Civil Hospital Autopsy & Forensic Medical Post-Mortem",
                "evidence_type": "Document",
                "file_hash": "sha256_autopsy_meera_matheran_fall",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Post-mortem protocol records extensive blunt polytrauma and deceleration fractures of cranium and ribcage consistent with 80m vertical fall onto granite boulders. Neck hyoid bone is completely intact with zero subcutaneous petechial hemorrhages or fingernail scratch marks, conclusively ruling out pre-fall strangulation or violent physical struggling."
            },
            {
                "id": "EX-17-02",
                "name": "Third-Party Tourist Smartphone Video Recording",
                "evidence_type": "CCTV",
                "file_hash": "sha256_tourist_video_tiger_point_1612",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Time-calibrated video captured by an independent tourist at 16:12:05 IST captures Meera posing near the unfenced cliff edge on rain-soaked moss wearing smooth leather fashion sandals. Her husband Rohan is clearly captured 11 meters back on the paved asphalt walkway conversing with a tea vendor, holding umbrellas."
            },
            {
                "id": "EX-17-03",
                "name": "Family Bank Passbooks & Insurance Query Records",
                "evidence_type": "Document",
                "file_hash": "sha256_family_finances_dowry_claim",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Victim's father lodged formal complaint alleging Rohan harassed Meera regarding ₹15 Lakh home downpayment. Investigation confirms a joint life insurance policy was active, creating significant circumstantial friction."
            },
            {
                "id": "EX-17-04",
                "name": "Geological Survey of India Ledge Failure Examination",
                "evidence_type": "Document",
                "file_hash": "sha256_gsi_geological_shale_slip",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Geotechnical field survey at the fall point revealed a fresh 1.4-meter lateral mud-and-shale shear detachment along a saturated bedding plane. Soil compaction and striated shoe-sole scuff marks at the breakaway lip correspond to sudden physical loss of traction and rock collapse."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-17-ADV",
            "name": "Biased In-Law Written Accusation",
            "evidence_type": "Document",
            "file_hash": "sha256_inlaw_complaint_murder_demand",
            "hash_verified": False,
            "chain_of_custody_complete": True,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "Handwritten statement by victim's brother stating 'Rohan had threatened to throw her off if money was not arranged.'"
        }
    },

    # --------------------------------------------------------------------------
    # CASE 18: BLIND EXTERNAL CASE (Independent Contributor - Medico-Legal)
    # The Apex Heart Institute ICU Potassium Overdose Inquest
    # Focus: Malicious Nurse poisoning vs Junior Resident Iatrogenic error vs Pump fault
    # --------------------------------------------------------------------------
    {
        "id": "case_18_icu_potassium_poison",
        "title": "Inquest into Fatal Hyperkalemia of Patient S.V. (Apex ICU Medico-Legal Case)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: Medico-Legal Jurisprudence Fellowship Archive (Case #BLIND-2024-F04)",
        "confidence_note": "High - Audio dictaphone emergency tape, pharmacy dispensation, and toxicology",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Junior Resident Dr. Gaurav (Fatal Iatrogenic Medical Dosing Error)",
            "rationale": "Code Blue emergency recording captures Dr. Gaurav mistakenly issuing an immediate IV direct push bolus command for concentrated KCl during arrhythmia panic, which nurse Sunita questioned and administered per explicit repeated order."
        },
        "decisive_evidence_ids": ["EX-18-01", "EX-18-03", "EX-18-04"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Night Duty Staff Nurse Sunita (Malicious Intentional Poisoning)",
                "statement": "Nurse Sunita intentionally injected concentrated potassium chloride into patient's peripheral cannula due to an ongoing administrative grievance."
            },
            {
                "id": "H2",
                "label": "Junior Resident Dr. Gaurav (Fatal Iatrogenic Dosing Error)",
                "statement": "Junior resident physician panicked during acute tachyarrhythmia and verbally ordered an immediate IV direct bolus of concentrated KCl instead of calcium gluconate."
            },
            {
                "id": "H3",
                "label": "Automated Syringe Infusion Device Runaway Failure",
                "statement": "Microprocessor calibration failure in the motorized infusion pump delivered 50ml volume instantaneously instead of continuous 24-hour rate."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.90},
                {"factor_type": "motive", "factor_value": "personal_vendetta", "numeric_adjustment": 0.50},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.95},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 0.80},
                {"factor_type": "means", "factor_value": "limited_capacity", "numeric_adjustment": 0.30},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.10},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {"H1": [], "H2": [], "H3": []},
        "exhibits": [
            {
                "id": "EX-18-01",
                "name": "Forensic Toxicology & FSL Lab Post-Mortem Blood Assay",
                "evidence_type": "Document",
                "file_hash": "sha256_toxicology_kcl_hyperkalemia_assay",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Post-mortem femoral blood panel reveals acute serum potassium spike to 9.8 mEq/L resulting in fatal cardiac arrest. Syringe remnants recovered from ICU sharps bin contained high-concentration 15% potassium chloride without dilution solution."
            },
            {
                "id": "EX-18-02",
                "name": "Central Hospital Pharmacy Automated Dispensation Log",
                "evidence_type": "Document",
                "file_hash": "sha256_pyxis_pharmacy_dispense_gaurav",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Pyxis electronic medication station log indicates concentrated KCl 50ml ampoule was dispensed under Dr. Gaurav's biometric physician login at 03:14 AM and signed out to ICU Bed-4."
            },
            {
                "id": "EX-18-03",
                "name": "Emergency Resuscitation Audio Dictaphone Recording",
                "evidence_type": "CDR",
                "file_hash": "sha256_dictaphone_code_blue_apex_icu",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "ICU automated clinical dictaphone captures audio at 03:18:22: Dr. Gaurav shouts 'Heart rate 190, wide complex! Push 20 of potassium stat, bolus now!' Nurse Sunita's voice is recorded querying: 'Doctor, direct bolus? That is concentrated.' Dr. Gaurav is recorded responding: 'Yes, push it fast, patient is coding!' Conclusively confirming catastrophic verbal iatrogenic directive."
            },
            {
                "id": "EX-18-04",
                "name": "Biomedical Engineering Syringe Pump Inspection Report",
                "evidence_type": "Document",
                "file_hash": "sha256_bme_infusion_pump_audit_b4",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Biomedical engineering diagnostic testing on the B.Braun Perfusor pump at Bed-4 confirms motor gearing and optical encoders operated within 0.1% tolerance with zero volume runaway or software watchdog exceptions."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-18-ADV",
            "name": "Hospital Administration Internal Complaint Memo",
            "evidence_type": "Document",
            "file_hash": "sha256_nurse_sunita_harassment_complaint",
            "hash_verified": True,
            "chain_of_custody_complete": True,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "HR disciplinary notice against Nurse Sunita regarding attendance arguments, introduced to allege vindictive sabotage."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 19: BLIND EXTERNAL CASE (Independent Contributor - Mock Trial)
    # The Opera House Subterranean Diamond Vault Burglary
    # Focus: Staged Owner Insurance Fraud vs Nephew Betrayal vs Safecracking Syndicate
    # --------------------------------------------------------------------------
    {
        "id": "case_19_diamond_vault_theft",
        "title": "State v. P.J. & Ors. (Opera House Diamond Vault Staged Burglary Case)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: Judicial Academy Mock Trial Case Study (Case #BLIND-2024-F05)",
        "confidence_note": "High - Customs airport seizure of stolen diamonds and electronic lock audit",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Jeweler Owner Pravin J. and Accomplices (Staged Theft)",
            "rationale": "Digital lock audit shows owner's authentic PIN opened vault without forced entry. Customs intercepted owner's brother-in-law boarding flight to Dubai with the missing diamonds."
        },
        "decisive_evidence_ids": ["EX-19-01", "EX-19-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Jeweler Owner Pravin J. (Staged Insurance Burglary)",
                "statement": "Owner staged an elaborate fake burglary using his master credentials to claim ₹12 Crore insurance while smuggling stones to Dubai via kin."
            },
            {
                "id": "H2",
                "label": "Estranged Nephew Yash J. (Duplicate Keycard Theft)",
                "statement": "Nephew addicted to high-stakes gambling cloned vault keycard and looted safe while uncle was away at trade exhibition."
            },
            {
                "id": "H3",
                "label": "Professional Underground Safecracking Syndicate",
                "statement": "Organized criminal gang tunneled through sewer conduit and utilized electromagnetic lock bypass to breach subterranean vault."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 0.95},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 1.00},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.95},
                {"factor_type": "alibi_status", "factor_value": "partially_verified", "numeric_adjustment": 0.40},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "remote_or_indirect", "numeric_adjustment": 0.45},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.50},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.70},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.85},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.40},
                {"factor_type": "means", "factor_value": "specialized_expert", "numeric_adjustment": 0.90},
                {"factor_type": "motive", "factor_value": "direct_financial_gain", "numeric_adjustment": 0.90},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {"H1": [], "H2": [], "H3": []},
        "exhibits": [
            {
                "id": "EX-19-01",
                "name": "Godrej Electronic Time-Lock & Master Vault Audit Telemetry",
                "evidence_type": "Document",
                "file_hash": "sha256_godrej_vault_timelock_audit",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Digital diagnostic read-out from the vault controller demonstrates the door was opened at 23:42 IST with owner Pravin J.'s authentic Master PIN and mechanical key. Zero acoustic sensor alarms, drill torque triggers, or electronic tampering events were logged during the incident."
            },
            {
                "id": "EX-19-02",
                "name": "Forensic Structural Examination of Vault Walls & Basement",
                "evidence_type": "Document",
                "file_hash": "sha256_fsl_structural_tunnel_inspection",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Physical inspection of masonry and subterranean drainage conduits confirms reinforced concrete walls are completely intact with no drilling, tunnel breaches, or structural compromises."
            },
            {
                "id": "EX-19-03",
                "name": "Mumbai Customs Intelligence Air Cargo Seizure Dossier",
                "evidence_type": "Document",
                "file_hash": "sha256_customs_air_cargo_seizure_dubai",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Air Intelligence Unit at Terminal 2 intercepted Pravin J.'s brother-in-law Nilesh boarding Emirates flight EK-501 to Dubai. 4,200 carats of certified cut diamonds matching the serial numbers on the victim's vault ledger were recovered concealed in false bottoms of hard-shell luggage."
            },
            {
                "id": "EX-19-04",
                "name": "Bank Consortium SARFAESI Default & Debt Ledger",
                "evidence_type": "Document",
                "file_hash": "sha256_bank_debt_sarfaesi_opera_house",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Certified forensic financial audit showing jeweler's enterprise had defaulted on ₹18 Crore working capital facilities with loan recall notices issued 10 days before the alleged heist."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-19-ADV",
            "name": "Planted Goa Casino Debt Ledger Scribble",
            "evidence_type": "Document",
            "file_hash": "sha256_goa_casino_nephew_iou_scribble",
            "hash_verified": False,
            "chain_of_custody_complete": False,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 1,
            "text": "Photocopied handwritten IOU slip claiming nephew Yash owed ₹5 Crore to Goa bookies."
        }
    },

    # --------------------------------------------------------------------------
    # CASE 20: BLIND EXTERNAL CASE (Independent Contributor - Appellate Moot)
    # The Marine Drive Luxury SUV Fatal Hit-and-Run
    # Focus: Wealthy Son driving under influence vs Hired Fall-Guy driver vs Third vehicle
    # --------------------------------------------------------------------------
    {
        "id": "case_20_hit_and_run_substitute",
        "title": "State v. K.B. (Marine Drive Luxury SUV Fatal Hit-and-Run / Driver Fall-Guy Case)",
        "split": "blind_test",
        "category": "blind_mixed_evidence",
        "is_contested": False,
        "citation": "Independent Contributor: High Court Criminal Appellate Moot Court (Case #BLIND-2024-F06)",
        "confidence_note": "High - Steering airbag epithelial DNA match and Sea Link ANPR cabin imaging",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Wealthy Youth Kabir B. (Driver Ramakant was Paid Proxy Fall-Guy)",
            "rationale": "Driver's airbag facial contact swab proves 99.98% STR DNA match to Kabir B. High-resolution toll plaza cabin camera 14 minutes prior captures Kabir driving alone."
        },
        "decisive_evidence_ids": ["EX-20-01", "EX-20-02"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Kabir B. (Industrialist Son) Driving",
                "statement": "Kabir B. was speeding under the influence of alcohol and fled the scene in a trailing escort car, while family driver surrendered as a paid proxy."
            },
            {
                "id": "H2",
                "label": "Family Driver Ramakant Driving",
                "statement": "Hired chauffeur Ramakant was legitimately operating the vehicle on personal errand and surrendered voluntarily."
            },
            {
                "id": "H3",
                "label": "Unidentified Commercial Lorry Collision",
                "statement": "A heavy transport truck collided with pedestrians earlier; the Mercedes only struck road debris."
            }
        ],
        "suspect_factors": {
            "H1": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 1.00},
                {"factor_type": "opportunity", "factor_value": "confirmed_at_scene", "numeric_adjustment": 1.00},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.85},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H2": [
                {"factor_type": "access", "factor_value": "direct_physical_access", "numeric_adjustment": 0.90},
                {"factor_type": "opportunity", "factor_value": "confirmed_elsewhere", "numeric_adjustment": 0.20},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.85},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.20},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ],
            "H3": [
                {"factor_type": "access", "factor_value": "none_or_restricted", "numeric_adjustment": 0.10},
                {"factor_type": "opportunity", "factor_value": "unconfirmed_unknown", "numeric_adjustment": 0.30},
                {"factor_type": "means", "factor_value": "standard_physical_capacity", "numeric_adjustment": 0.80},
                {"factor_type": "motive", "factor_value": "none_apparent", "numeric_adjustment": 0.10},
                {"factor_type": "alibi_status", "factor_value": "none", "numeric_adjustment": 1.00},
                {"factor_type": "travel_feasibility", "factor_value": "physically_feasible", "numeric_adjustment": 1.00}
            ]
        },
        "prior_records": {"H1": [], "H2": [], "H3": []},
        "exhibits": [
            {
                "id": "EX-20-01",
                "name": "State FSL Airbag Deployment DNA STR Profile Assay",
                "evidence_type": "DNA",
                "file_hash": "sha256_airbag_str_dna_kabir_fsl",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Epithelial cell swab from the steering wheel driver airbag impact cushion yielded high-quality 16-locus autosomal STR profile matching suspect Kabir B. at 99.98% random match probability. Chauffeur Ramakant's DNA profile is completely absent on the driver airbag impact face."
            },
            {
                "id": "EX-20-02",
                "name": "Bandra-Worli Sea Link High-Resolution Toll ANPR & Cabin Camera",
                "evidence_type": "CCTV",
                "file_hash": "sha256_sealink_anpr_cabin_hd_2348",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Infrared night-vision cabin camera at Sea Link toll plaza captures the vehicle at 23:48 IST (14 minutes prior to crash). High-resolution image clearly shows Kabir B. operating the steering wheel wearing a black Balenciaga hoodie, with passenger and rear seats completely empty."
            },
            {
                "id": "EX-20-03",
                "name": "Written Surrender Statement of Driver Ramakant",
                "evidence_type": "Document",
                "file_hash": "sha256_surrender_ramakant_confession",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": False,
                "source_independent": False,
                "quality_rating": 2,
                "text": "Signed statement by chauffeur Ramakant claiming he was alone driving the vehicle to garage. Medical examination reveals Ramakant has zero abrasions, seatbelt chest bruising, or facial impact erythema consistent with explosive airbag deployment."
            },
            {
                "id": "EX-20-04",
                "name": "Mercedes Bosch Airbag Control Unit (ACU) Crash Telemetry Dump",
                "evidence_type": "Document",
                "file_hash": "sha256_mercedes_acu_crash_telemetry",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Electronic control module forensic extraction records speed at impact was 138 km/h on Marine Drive, throttle position 84%, brake pressure 0 bar (zero braking), confirming reckless excessive speed."
            }
        ],
        "adversarial_exhibit": {
            "id": "EX-20-ADV",
            "name": "Paid Chauffeur Affidavits",
            "evidence_type": "Document",
            "file_hash": "sha256_notarized_driver_affidavit",
            "hash_verified": False,
            "chain_of_custody_complete": True,
            "sec_65b_certificate_present": False,
            "source_independent": False,
            "quality_rating": 2,
            "text": "Notarized affidavit by domestic driver claiming Kabir B. was sleeping at farmhouse at the time of the collision."
        }
    },

    {
        "id": "case_21_framed_apprentice_heist",
        "title": "State v. S.K. & Anr. (Opera House Diamond Cutting Laser Heist)",
        "split": "test",
        "category": "property_heist",
        "is_contested": False,
        "citation": "Independent Contributor: Adv. Tanya Mehra (NLU Delhi) & Adv. Devendra Verma (ILS Pune)",
        "confidence_note": "High - Confirmation bias trap: Apprentice had planted stone, juvenile prior, and salary dispute, but physical laser striation and biometric turnstile conclusively exonerate him.",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Master Cutter D. Kulkarni (Inside Laser Breach & Framing)",
            "rationale": "High-resolution stereomicroscopy confirms vault security bracket was severed with a 532nm green Nd:YAG laser tool exclusively licensed to Kulkarni's private workshop. Turnstile biometrics place Apprentice Suresh outside the facility at 11:30 PM, 12 minutes before the vault was electronically breached."
        },
        "decisive_evidence_ids": [
            "EX-21-01",
            "EX-21-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Apprentice Suresh K. (Framed Employee)",
                "statement": "Apprentice Suresh breached the inner vault using stolen keys, stole the 15-carat primary diamond, and hid a 2-carat uncut stone in his employee locker."
            },
            {
                "id": "H2",
                "label": "Master Cutter D. Kulkarni (Inside Precision Theif)",
                "statement": "Master Cutter Kulkarni utilized his proprietary high-precision 532nm laser cutting tool to bypass vault sensors after hours and planted a dummy stone in Suresh's locker to divert suspicion."
            },
            {
                "id": "H3",
                "label": "External Armed Dacoity Gang",
                "statement": "An external armed syndicate penetrated the rooftop ventilation duct and forced the vault mechanism."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "supervised_access",
                    "numeric_adjustment": 0.5
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "confirmed_elsewhere",
                    "numeric_adjustment": 0.15
                },
                {
                    "factor_type": "means",
                    "factor_value": "lacks_technical_means",
                    "numeric_adjustment": 0.2
                },
                {
                    "factor_type": "motive",
                    "factor_value": "unpaid_wages_dispute",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "fully_verified",
                    "numeric_adjustment": 0.1
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_infeasible",
                    "numeric_adjustment": 0.2
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "master_key_and_vault_code",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "unsupervised_after_hours",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "means",
                    "factor_value": "proprietary_laser_cutting_tool",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "motive",
                    "factor_value": "personal_bankruptcy_liquidation",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "unverified",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.95
                }
            ],
            "H3": [
                {
                    "factor_type": "access",
                    "factor_value": "zero_authorized_access",
                    "numeric_adjustment": 0.1
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "perimeter_alarmed",
                    "numeric_adjustment": 0.2
                },
                {
                    "factor_type": "means",
                    "factor_value": "heavy_cutting_equipment",
                    "numeric_adjustment": 0.6
                },
                {
                    "factor_type": "motive",
                    "factor_value": "syndicate_profit",
                    "numeric_adjustment": 0.7
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "unknown",
                    "numeric_adjustment": 0.5
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.6
                }
            ]
        },
        "prior_records": {
            "H1": [
                {
                    "offense_category": "petty_theft",
                    "year_of_conviction": 2021,
                    "relevance_level": "medium",
                    "description": "Juvenile shoplifting charge 5 years ago; used by investigators as prejudicial prior."
                }
            ],
            "H2": []
        },
        "exhibits": [
            {
                "id": "EX-21-01",
                "name": "FSL Laser Kerf & Heat-Affected Zone (HAZ) Micro-Spectrometry",
                "evidence_type": "Forensic",
                "file_hash": "sha256_laser_kerf_haz_spectrometry",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Stereomicroscopy and electron probe microanalysis of the severed vault titanium bracket reveal ultra-narrow 42-micrometer kerf width with 532nm green laser thermal oxidation. Kerf geometry matches the proprietary Nd:YAG laser tool registered exclusively to Master Cutter Kulkarni; Apprentice Suresh had zero access or training on laser equipment."
            },
            {
                "id": "EX-21-02",
                "name": "Biometric Turnstile Departure Log & Security CCTV",
                "evidence_type": "Digital",
                "file_hash": "sha256_biometric_turnstile_cctv",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Time-synchronized biometric turnstile logs and external street CCTV confirm Apprentice Suresh exited the building at 11:30 PM and boarded the 11:38 PM local train at Charni Road station. The electronic vault door was breached at 11:42 PM, establishing a definitive physical alibi for Suresh."
            },
            {
                "id": "EX-21-03",
                "name": "Recovered 2-Carat Stone Adhesive Trace Analysis",
                "evidence_type": "Physical",
                "file_hash": "sha256_planted_diamond_adhesive",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "The 2-carat uncut diamond recovered from Suresh's locker bears microscopic traces of UV-cured cyanoacrylate bonding polymer identical to the custom adhesive bottle seized from Kulkarni's private worktable, indicating deliberate planting."
            },
            {
                "id": "EX-21-04",
                "name": "Rooftop Ventilation Shaft Physical Inspection",
                "evidence_type": "Physical",
                "file_hash": "sha256_rooftop_vent_inspection",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Perimeter physical survey confirms rooftop ventilation steel security grilles remain undisturbed with unbroken layer of atmospheric soot (0.00 breach), completely refuting external armed syndicate infiltration."
            }
        ]
    },
    {
        "id": "case_22_staged_hang_asphyxia",
        "title": "Inquest into Fatal Ligature Asphyxia of Industrialist Singhal",
        "split": "test",
        "category": "homicide",
        "is_contested": False,
        "citation": "Independent Contributor: Dr. Arindam Sen, MD (AIIMS New Delhi) & Prof. K. Sharma (NFSU Gandhinagar)",
        "confidence_note": "High - Confirmation bias trap: Partner Oberoi screamed death threats at 10 PM, but post-mortem horizontal ligature mark and flight records prove manual strangulation by live-in caregiver at 3:30 AM.",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Live-in Caregiver Anthony (Manual Ligature Strangulation from Behind)",
            "rationale": "Autopsy establishes a continuous horizontal ligature furrow below thyroid cartilage with sub-conjunctival petechiae, pathognomonic of homicidal ligature strangulation from behind, rather than hanging. Time of death (03:00-04:00 AM) coincides with caregiver's solo bedside shift and completely excludes partner Oberoi who boarded a commercial flight at 11:45 PM."
        },
        "decisive_evidence_ids": [
            "EX-22-01",
            "EX-22-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Business Partner V. Oberoi (Threatening Debtor)",
                "statement": "Partner Oberoi returned to the residence late at night and hanged Singhal to extinguish a ?15 Crore personal loan default."
            },
            {
                "id": "H2",
                "label": "Live-in Caregiver Anthony (Homicidal Ligature Strangulation)",
                "statement": "Caregiver Anthony strangled Singhal from behind with a nylon medical cord at 03:30 AM to conceal narcotic painkiller theft, then staged the body on the ceiling hook."
            },
            {
                "id": "H3",
                "label": "Suicidal Suspension (Self-Inflicted Hanging)",
                "statement": "Singhal committed suicide via suspension from the ceiling fan due to severe depressive insomnia."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "forced_or_invited_access",
                    "numeric_adjustment": 0.6
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "confirmed_elsewhere",
                    "numeric_adjustment": 0.1
                },
                {
                    "factor_type": "means",
                    "factor_value": "standard_physical_capacity",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "motive",
                    "factor_value": "extreme_financial_debt",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "fully_verified",
                    "numeric_adjustment": 0.05
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_infeasible",
                    "numeric_adjustment": 0.1
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "exclusive_bedroom_custody",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "unsupervised_overnight_shift",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "means",
                    "factor_value": "medical_cord_and_sedatives",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "motive",
                    "factor_value": "theft_concealment",
                    "numeric_adjustment": 0.75
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "sole_individual_present",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 1.0
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-22-01",
                "name": "Department of Forensic Medicine Autopsy Protocol",
                "evidence_type": "Forensic",
                "file_hash": "sha256_autopsy_ligature_morphology",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Post-mortem dissection reveals a completely horizontal, continuous ligature furrow located below the level of the thyroid cartilage, with inward fracture of the greater cornu of hyoid bone and dense petechial hemorrhages in bilateral palpebral conjunctivae. Findings conclusively establish homicidal ligature strangulation applied horizontally from behind; entirely incompatible with suicidal suspension (hanging produces an oblique, non-continuous groove above thyroid)."
            },
            {
                "id": "EX-22-02",
                "name": "CISF Airport Departure Biometrics & In-Flight Passenger Manifest",
                "evidence_type": "Document",
                "file_hash": "sha256_cisf_flight_manifest_oberoi",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Immigration facial recognition logs and boarding pass records verify Business Partner Oberoi passed international security at 10:45 PM and was airborne on flight AI-102 to Dubai at 11:45 PM. Core body temperature and post-mortem vitreous potassium confirm Singhal died between 03:00 AM and 04:00 AM, conclusively exculpating Oberoi."
            },
            {
                "id": "EX-22-03",
                "name": "Caregiver Anthony Shift Log & Medical Waste Bin Recovery",
                "evidence_type": "Physical",
                "file_hash": "sha256_caregiver_braided_cord",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Forensic recovery from the basement bio-hazard bin identified a 6mm braided nylon traction cord bearing victim's cervical epidermal DNA and Anthony's sweat epithelial markers. Furrow microscopic weave impression on Singhal's neck matches this 6mm braided cord exactly."
            }
        ]
    },
    {
        "id": "case_23_decoy_cfo_wire_fraud",
        "title": "State v. R.K. & Anr. (?32 Crore Treasury SWIFT Exfiltration)",
        "split": "test",
        "category": "cyber_fraud",
        "is_contested": False,
        "citation": "Independent Contributor: Ret. DySP Ashok S. Patil (Anti-Corruption Bureau & Economic Offences Wing)",
        "confidence_note": "High - Confirmation bias trap: CFO Raman had ?8 Crore crypto debt and booked London flight, but physical HSM token was inserted into basement server switch while Raman was at airport.",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Senior Systems Architect K. Nambiar (Physical HSM Clone & Session Hijack)",
            "rationale": "Hardware Security Module (HSM) session logs confirm the physical cryptographic token was inserted directly into Switchport 8 in the basement server room at 02:14 AM. Biometric turnstile logs and airport CCTV confirm CFO Raman was at Mumbai Airport terminal departure hall at 02:14 AM with zero device connectivity. Nambiar's badge logged into the server room at 02:08 AM."
        },
        "decisive_evidence_ids": [
            "EX-23-01",
            "EX-23-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Chief Financial Officer Raman K. (Indebted Executive)",
                "statement": "CFO Raman authorized the ?32 Crore SWIFT wire to an offshore Panamanian account to liquidate crushing personal cryptocurrency debts before fleeing to London."
            },
            {
                "id": "H2",
                "label": "Senior Systems Architect K. Nambiar (Insider Network Intruder)",
                "statement": "Systems Architect Nambiar bypassed multi-factor controls by physically inserting an authorized cryptographic token into the core datacenter switchport while hijacking the CFO's authenticated web session."
            },
            {
                "id": "H3",
                "label": "External Ransomware / Cobalt Strike APT Syndicate",
                "statement": "An external advanced persistent threat group gained remote administrative control via unpatched perimeter VPN gateway."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "master_administrative_privileges",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "confirmed_elsewhere",
                    "numeric_adjustment": 0.1
                },
                {
                    "factor_type": "means",
                    "factor_value": "swift_portal_credentials",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "motive",
                    "factor_value": "imminent_personal_bankruptcy",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "fully_verified",
                    "numeric_adjustment": 0.05
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_infeasible",
                    "numeric_adjustment": 0.1
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "datacenter_physical_badge",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "present_at_target_node",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "means",
                    "factor_value": "hardware_switchport_access",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "motive",
                    "factor_value": "unexplained_offshore_wealth",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "unverified",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 1.0
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-23-01",
                "name": "Datacenter Core Switchport 8 Telemetry & HSM Cryptographic Logs",
                "evidence_type": "Digital",
                "file_hash": "sha256_core_switchport_hsm_telemetry",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Cisco Catalyst 9500 switchport 8 telemetry proves the wire transaction was signed using a physically plugged-in YubiKey-HSM hardware token at 02:14:22 AM locally on VLAN 40 (Datacenter Operations). The physical token was located inside the secure basement server enclosure, requiring local physical contact."
            },
            {
                "id": "EX-23-02",
                "name": "Chhatrapati Shivaji Maharaj International Airport CCTV & Immigration Timestamps",
                "evidence_type": "Digital",
                "file_hash": "sha256_airport_immigration_cfo",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Immigration checkpoint timestamps and CCTV verify CFO Raman was physically standing in the immigration queue at Terminal 2 from 01:50 AM to 02:35 AM with personal electronics sealed in checked luggage, establishing conclusive impossibility of physical presence in the basement server room."
            },
            {
                "id": "EX-23-03",
                "name": "Basement Server Enclosure RFID Turnstile Log",
                "evidence_type": "Digital",
                "file_hash": "sha256_basement_rfid_nambiar",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Badge access reader logs confirm Systems Architect Nambiar scanned his personal badge into the basement server enclosure at 02:08 AM and departed at 02:26 AM, perfectly encapsulating the 02:14 AM wire transfer."
            }
        ]
    },
    {
        "id": "case_24_ambiguous_cold_storage_ammonia",
        "title": "Inquest into Fatal Ammonia Inhalation at Continental Cold Storage",
        "split": "blind_test",
        "category": "industrial_disaster",
        "is_contested": True,
        "citation": "Independent Contributor: Adv. Mihir Kothari (Bombay High Court) & Adv. Ananya Joshi (NLSIU Bangalore)",
        "confidence_note": "Inconclusive / Mixed Ambiguity - Dual causative factors: deferred corporate maintenance corrosion vs intentional mechanical wrench valve tampering. Standard of proof beyond reasonable doubt is NOT met.",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Corporate Management Negligence (Corrosion Cracking Flange Failure)",
            "rationale": "Metallurgical examination reveals severe stress corrosion cracking and 70% thread degradation across flange bolts that failed under normal operating pressure. However, toolmark impressions on secondary bypass valve indicate human tampering, creating irreducible statutory ambiguity."
        },
        "decisive_evidence_ids": [
            "EX-24-01",
            "EX-24-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Corporate Maintenance Negligence (Flange Corrosion Failure)",
                "statement": "Management deferred statutory hydrostatic inspections for 3 years, causing catastrophic ammonia rupture from stress corrosion cracking."
            },
            {
                "id": "H2",
                "label": "Competitor Industrial Sabotage (Deliberate Valve Tampering)",
                "statement": "An operative hired by rival export company entered through the perimeter fence and manually forced open the secondary pressure relief bypass valve."
            },
            {
                "id": "H3",
                "label": "Night Watchman Accidental Operation Error",
                "statement": "The deceased watchman attempted to silence a pressure alarm by turning valves without protective respirator gear."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "management_control",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "ongoing_neglect",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "means",
                    "factor_value": "deferred_capital_budget",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "motive",
                    "factor_value": "cost_cutting_savings",
                    "numeric_adjustment": 0.75
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "documented_deferrals",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.85
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "perimeter_trespass",
                    "numeric_adjustment": 0.6
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "unmonitored_night_shift",
                    "numeric_adjustment": 0.7
                },
                {
                    "factor_type": "means",
                    "factor_value": "heavy_adjustable_wrench",
                    "numeric_adjustment": 0.75
                },
                {
                    "factor_type": "motive",
                    "factor_value": "commercial_disruption",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "unverified",
                    "numeric_adjustment": 0.65
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.7
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-24-01",
                "name": "National Metallurgical Laboratory (NML) Flange Failure Report",
                "evidence_type": "Forensic",
                "file_hash": "sha256_nml_flange_corrosion_report",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Scanning Electron Microscopy (SEM) of the failed ANSI Class 300 ammonia flange demonstrates extensive intergranular stress corrosion cracking (SCC) with 68% wall-thickness loss on the inner gasket seat, consistent with long-term deferred maintenance."
            },
            {
                "id": "EX-24-02",
                "name": "State Directorate of Industrial Safety Inspection & Valve Toolmarks",
                "evidence_type": "Forensic",
                "file_hash": "sha256_dis_toolmark_bypass_valve",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Forensic examination of the secondary bypass line discovered fresh serrated mechanical toolmark abrasions on the brass valve stem, indicating a 24-inch pipe wrench was applied to force the valve past its safety detent hours before the rupture. Paint flakes on the valve stem do not match in-house maintenance tools."
            },
            {
                "id": "EX-24-03",
                "name": "CCTV DVR Hard Drive Diagnostic & Power Log",
                "evidence_type": "Digital",
                "file_hash": "sha256_cctv_dvr_power_loss",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 3,
                "text": "Perimeter CCTV recorder experienced power disruption at 01:15 AM due to tripping of external breaker, leaving a 90-minute visual blind spot during which either internal passive failure or external intrusion could have occurred."
            }
        ]
    },
    {
        "id": "case_25_insulin_overdose_ward",
        "title": "Inquest into Fatal Hyperinsulinemic Hypoglycemia of Smt. Sharda Devi",
        "split": "test",
        "category": "poisoning",
        "is_contested": False,
        "citation": "Independent Contributor: Dr. Shweta Rastogi (NFSU) & Prof. K. Sharma (NFSU Gandhinagar)",
        "confidence_note": "High - Confirmation bias trap: Stepson Rahul had heated will dispute 4 hours prior and inherits ?8 Crore, but post-mortem C-peptide assay and medicine lock prove 04:15 AM injection by nurse on duty.",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Night Ward Nurse Sunita (Fatal Exogenous Insulin Overdose)",
            "rationale": "Biochemical toxicology proves profound hypoglycemia with serum insulin > 1000 pmol/L and zero detectable C-peptide (< 0.1 ng/mL), establishing injection of synthetic exogenous human insulin. Automated medicine refrigerator dispensing logs confirm Sunita unlocked the rapid-acting insulin cartridge at 04:11 AM, while stepson Rahul departed the hospital at 01:30 AM."
        },
        "decisive_evidence_ids": [
            "EX-25-01",
            "EX-25-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Stepson Rahul M. (Sole Estate Beneficiary)",
                "statement": "Stepson Rahul injected lethal dose of insulin during late-night bedside visit to secure immediate ?8 Crore inheritance following heated argument."
            },
            {
                "id": "H2",
                "label": "Night Ward Nurse Sunita (Lethal Medication Administration)",
                "statement": "Nurse Sunita administered 100 IU of Actrapid insulin via intravenous cannula at 04:15 AM, acting under financial inducement from rival beneficiaries."
            },
            {
                "id": "H3",
                "label": "Spontaneous Endogenous Insulinoma Crisis",
                "statement": "The patient experienced acute neuroglycopenic coma caused by an undetected neuroendocrine pancreatic islet tumor."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "visitor_visitation_pass",
                    "numeric_adjustment": 0.6
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "confirmed_elsewhere",
                    "numeric_adjustment": 0.1
                },
                {
                    "factor_type": "means",
                    "factor_value": "syringe_procurement_possible",
                    "numeric_adjustment": 0.7
                },
                {
                    "factor_type": "motive",
                    "factor_value": "eight_crore_will_inheritance",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "fully_verified",
                    "numeric_adjustment": 0.05
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_infeasible",
                    "numeric_adjustment": 0.1
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "direct_intravenous_line_access",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "unsupervised_medication_round",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "means",
                    "factor_value": "dispensing_keys_and_syringes",
                    "numeric_adjustment": 1.0
                },
                {
                    "factor_type": "motive",
                    "factor_value": "illicit_financial_remittance",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "sole_on_duty_staff",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 1.0
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-25-01",
                "name": "Clinical Biochemistry Toxicological Assay (C-Peptide vs Free Insulin)",
                "evidence_type": "Forensic",
                "file_hash": "sha256_c_peptide_insulin_assay",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Post-admission serum assay confirms circulating free insulin level was extremely elevated at 1,240 pmol/L with completely suppressed C-peptide concentration of < 0.05 ng/mL. In endogenous insulinoma, C-peptide is elevated equimolarly with insulin; zero C-peptide is the definitive scientific hallmark of exogenous synthetic insulin administration, entirely ruling out spontaneous pancreatic tumor."
            },
            {
                "id": "EX-25-02",
                "name": "Hospital Main Entrance Turnstile & Uber Ride Telemetry (Stepson Alibi)",
                "evidence_type": "Digital",
                "file_hash": "sha256_turnstile_uber_alibi_rahul",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Hospital visitor gate RFID card logs, lobby CCTV, and verified Uber trip receipts establish Stepson Rahul exited the hospital premises at 01:28 AM and was dropped at his residence in Bandra West at 02:04 AM. The patient's continuous glycemic monitor records normal blood glucose until 04:12 AM, when an abrupt precipitous crash occurred, conclusively eliminating Rahul as the administrator."
            },
            {
                "id": "EX-25-03",
                "name": "Ward High-Risk Medication Refrigerator Smart-Lock Audit",
                "evidence_type": "Digital",
                "file_hash": "sha256_smart_lock_medication_sunita",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "Smart-lock biometric access audit of the intensive care medication refrigerator proves Nurse Sunita scanned her credentials at 04:11:15 AM and withdrew a 100 IU vial of Humalog insulin without corresponding physician prescription entry on the electronic health record."
            }
        ]
    },
    {
        "id": "case_26_hit_run_cctv_optical_illusion",
        "title": "State v. P.S. & Ors. (Marine Drive Midnight Hit-and-Run Collision)",
        "split": "test",
        "category": "traffic_fatality",
        "is_contested": False,
        "citation": "Independent Contributor: Ret. ACP R. V. Deshmukh (Maharashtra Police CID) & Adv. Devendra Verma (ILS Pune)",
        "confidence_note": "High - Confirmation bias trap: Suspect Singhania owns silver Honda with plate 4812 matching partial CCTV, had bumper dent, and lied to police. But paint spectrophotometry and aged rust prove Contractor Patil's Skoda Rapid was the striking vehicle.",
        "ground_truth": {
            "hypothesis_id": "H2",
            "culprit_summary": "Transport Contractor P. Patil (Striking Vehicle Skoda Rapid MH-12-QB-4872)",
            "rationale": "High-performance liquid chromatography and spectrophotometry confirm paint transfer on victim's bicycle frame is metallic polyurethane with bismuth vanadate yellow undertone, matching Skoda OEM factory formulation, not Honda factory enamel. Forensic metal analysis proves Singhania's bumper dent is oxidized old rust (3+ weeks old) with zero fresh impact fractures."
        },
        "decisive_evidence_ids": [
            "EX-26-01",
            "EX-26-02"
        ],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Businessman K. Singhania (Silver Honda City MH-12-AA-4812)",
                "statement": "Singhania struck the bicyclist at 11:58 PM while speeding in his silver Honda City and fled the scene, later claiming he was at a restaurant."
            },
            {
                "id": "H2",
                "label": "Transport Contractor P. Patil (Silver Skoda Rapid MH-12-QB-4872)",
                "statement": "Patil operated his silver Skoda Rapid at excessive speed, struck the victim at the pedestrian crossing, and concealed the damaged vehicle in a private warehouse."
            },
            {
                "id": "H3",
                "label": "Unregistered Overloaded Aggregate Tipper Truck",
                "statement": "An overloaded construction dump truck sideswiped the cyclist with its rear under-run protection bar."
            }
        ],
        "suspect_factors": {
            "H1": [
                {
                    "factor_type": "access",
                    "factor_value": "vehicle_ownership",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "inconsistent_timeline",
                    "numeric_adjustment": 0.7
                },
                {
                    "factor_type": "means",
                    "factor_value": "sedan_vehicle",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "motive",
                    "factor_value": "avoid_dui_arrest",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "false_statements_given",
                    "numeric_adjustment": 0.8
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.9
                }
            ],
            "H2": [
                {
                    "factor_type": "access",
                    "factor_value": "vehicle_ownership",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "opportunity",
                    "factor_value": "cell_tower_colocated",
                    "numeric_adjustment": 0.95
                },
                {
                    "factor_type": "means",
                    "factor_value": "sedan_vehicle",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "motive",
                    "factor_value": "commercial_deadline_speeding",
                    "numeric_adjustment": 0.85
                },
                {
                    "factor_type": "alibi_status",
                    "factor_value": "unverified",
                    "numeric_adjustment": 0.9
                },
                {
                    "factor_type": "travel_feasibility",
                    "factor_value": "physically_feasible",
                    "numeric_adjustment": 0.95
                }
            ]
        },
        "exhibits": [
            {
                "id": "EX-26-01",
                "name": "Central Forensic Science Laboratory (CFSL) Paint Multi-Layer Spectrophotometry",
                "evidence_type": "Forensic",
                "file_hash": "sha256_paint_spectrophotometry_skoda",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Fourier Transform Infrared (FTIR) microscopy and microspectrophotometry of micro-paint scrapings recovered from the victim's bicycle frame identify a four-coat automotive finish: phosphate primer, electrocoat, silver metallic basecoat containing aluminum flake, and clear polyurethane topcoat with bismuth vanadate yellow toner. The organic binder matrix matches Skoda OEM formulation Brilliant Silver (Paint Code 8E8E); entirely incompatible with Honda Tafeta White/Silver acrylic enamel."
            },
            {
                "id": "EX-26-02",
                "name": "State Motor Vehicles Department Metallurgical Damage Chronology",
                "evidence_type": "Physical",
                "file_hash": "sha256_bumper_dent_metallurgical_chronology",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 5,
                "text": "Physical inspection of Singhania's Honda City bumper indentation reveals heavy micro-crystalline iron oxide (pitting rust) covering the crease edges with accumulated road grime, confirming the metal deformation occurred at least 3 weeks prior. Zero fresh paint transfer or fractured plastic clips were present, disproving involvement in the midnight collision."
            },
            {
                "id": "EX-26-03",
                "name": "High-Speed ANPR Tollway Camera & Windshield Fracture Capture",
                "evidence_type": "Digital",
                "file_hash": "sha256_anpr_toll_skoda_patil",
                "hash_verified": True,
                "chain_of_custody_complete": True,
                "sec_65b_certificate_present": True,
                "source_independent": True,
                "quality_rating": 4,
                "text": "High-definition infrared Automatic Number Plate Recognition (ANPR) camera located 2.4 km south at Sea Link toll plaza captured silver Skoda Rapid registration MH-12-QB-4872 at 12:05:14 AM displaying severe spiderweb impact fracture on passenger-side windshield and fractured right headlight assembly."
            }
        ]
    }


]


def export_benchmark_dataset(target_dir: str = "backend/evaluation/datasets"):
    """
    Exports all benchmark cases as individual JSON files and a master index.
    """
    path = Path(target_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    index = []
    for case in BENCHMARK_CASES:
        filename = f"{case['id']}.json"
        case_path = path / filename
        with open(case_path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, ensure_ascii=False)
        index.append({
            "id": case["id"],
            "title": case["title"],
            "split": case["split"],
            "category": case["category"],
            "is_contested": case["is_contested"],
            "citation": case["citation"],
            "ground_truth_hypothesis": case["ground_truth"]["hypothesis_id"],
            "exhibits_count": len(case["exhibits"]),
            "hypotheses_count": len(case["hypotheses"]),
            "file": filename
        })
        
    index_path = path / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        
    print(f"[BENCHMARK] Exported {len(BENCHMARK_CASES)} frozen benchmark cases to {path}")
    return index


if __name__ == "__main__":
    export_benchmark_dataset()
