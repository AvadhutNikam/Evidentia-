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
    # CASE 1: REAL LANDMARK (Tuning Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_01_pujari",
        "title": "State of Maharashtra v. Yogesh Raut & Ors. (Pune Techie Case)",
        "split": "tuning",
        "category": "real_landmark",
        "is_contested": False,
        "citation": "Special Sessions Court, Pune (Judgment dated 27 March 2017) / Confirmed Bombay High Court 2024",
        "confidence_note": "High (Beyond Reasonable Doubt, confirmed on appeal with forensic corroboration)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Yogesh Raut and co-accused (cab driver and accomplices)",
            "rationale": "Forensic blood match in Qualis cab MH-12-CR-8692, ATM CCTV cash withdrawal, Sec 164 CrPC judicial confession by approver."
        },
        "decisive_evidence_ids": ["EX-01-01", "EX-01-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Yogesh Raut & Co-accused",
                "statement": "Cab driver Yogesh Raut and accomplices abducted the victim in Qualis cab MH-12-CR-8692, used her ATM cards, and committed the assault."
            },
            {
                "id": "H2",
                "label": "Unknown Highway Syndicate",
                "statement": "An opportunistic inter-state highway gang hijacked the victim at Kharadi bypass; cab driver Yogesh was unrelated."
            },
            {
                "id": "H3",
                "label": "Workplace Colleague",
                "statement": "A disgruntled corporate colleague arranged the abduction using a hired private vehicle."
            }
        ],
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
    # CASE 2: REAL LANDMARK (Tuning Set)
    # --------------------------------------------------------------------------
    {
        "id": "case_02_indiranagar",
        "title": "State of Karnataka v. Manjunath & Ors. (Indiranagar Robbery-Homicide)",
        "split": "tuning",
        "category": "real_landmark",
        "is_contested": False,
        "citation": "Principal Sessions Court, Bengaluru (SC-412/2019)",
        "confidence_note": "High (Direct latent fingerprint match and gold jewellery recovery under Sec 27 Evidence Act)",
        "ground_truth": {
            "hypothesis_id": "H1",
            "culprit_summary": "Former domestic assistant Manjunath and accomplice",
            "rationale": "Latent fingerprint on broken window latch matched Manjunath; stolen 120g temple gold recovered from pawn broker based on disclosure."
        },
        "decisive_evidence_ids": ["EX-02-01", "EX-02-03"],
        "hypotheses": [
            {
                "id": "H1",
                "label": "Former Domestic Staff Manjunath",
                "statement": "Former domestic worker Manjunath knew the safe combination, broke through the rear window, and assaulted the resident."
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
    # CASE 3: REAL CONTESTED LANDMARK (Test Set - Handled Honestly)
    # --------------------------------------------------------------------------
    {
        "id": "case_03_talwar",
        "title": "CBI v. Rajesh & Nupur Talwar (Aarushi Talwar Double Homicide)",
        "split": "test",
        "category": "contested",
        "is_contested": True,
        "citation": "Allahabad High Court (Criminal Appeal No. 7463/2013, Judgment 12 October 2017)",
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
                "label": "Parents (Rajesh & Nupur Talwar)",
                "statement": "The parents committed the killings inside the sealed flat under sudden grave provocation, then dressed up the crime scene."
            },
            {
                "id": "H2",
                "label": "Domestic Servants / Outside Intruders",
                "statement": "Domestic helpers (Krishna, Rajkumar, Vijay Mandal) entered Hemraj's room, attempted assault, and committed the murders before fleeing."
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
