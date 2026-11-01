"""
backend/config.py
================================================================================
EVIDENTIA AI - CENTRALIZED SYSTEM AND SCORING CONFIGURATION
================================================================================
Central source of truth for:
1. AI Model Selection and Fallback Models
2. Security, JWT, and CORS Settings
3. Database and Storage Quotas
4. Scientific ACH Scoring Defaults, Likelihood Ratios, and Exculpatory Factors
"""

import os
from typing import Dict, List, Any

# ==============================================================================
# 1. AI MODEL CONFIGURATION
# ==============================================================================
DEFAULT_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
FALLBACK_MODEL_NAMES = [
    os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest"
]

# ==============================================================================
# 2. SECURITY AND ENVIRONMENT
# ==============================================================================
ENV = os.getenv("ENV", "development").lower()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be set in production environment!")
    JWT_SECRET_KEY = "evidentia-ai-dev-insecure-secret-key-change-in-production-min-32-chars"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evidentia.db")

ALLOWED_ORIGINS = [
    orig.strip()
    for orig in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    ).split(",")
    if orig.strip()
]

# ==============================================================================
# 3. FORENSIC STORAGE AND UPLOAD QUOTAS
# ==============================================================================
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024      # 100 MB per single exhibit
MAX_CASE_STORAGE_BYTES = 500 * 1024 * 1024   # 500 MB per case docket
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# ==============================================================================
# 4. SCORING COMPUTATION CONSTANTS
# ==============================================================================
DEFAULT_DEPENDENCY_DAMPING_FACTORS = [1.0, 0.50, 0.25, 0.125]
DEFAULT_SCORING_TOLERANCE = 1e-4

CHANGE2_FACTOR_NUMERICS = {
    'direct_physical_access': 1.00,
    'key_premises_access': 0.85,
    'vehicle_weapon_access': 0.80,
    'remote_or_indirect': 0.45,
    'none_or_restricted': 0.10,
    'confirmed_at_scene': 1.00,
    'confirmed_vicinity': 0.80,
    'unconfirmed_unknown': 0.50,
    'confirmed_elsewhere': 0.10,
    'specialized_expert': 1.00,
    'standard_physical_capacity': 0.75,
    'limited_capacity': 0.40,
    'physically_incapable': 0.05,
    'direct_financial_gain': 0.95,
    'personal_enmity_grudge': 0.90,
    'sexual_predation': 0.90,
    'professional_conflict': 0.70,
    'secondary_opportunistic': 0.50,
    'none_apparent': 0.20,
    'strongly_verified': 0.10,
    'partially_verified': 0.50,
    'claimed': 1.00,
    'none': 1.00,
    'contradicted': 1.30,
    'physically_feasible': 1.00,
    'borderline': 0.75,
    'physically_impossible': 0.05
}

AVOID_DOUBLE_COUNTING_RULE = (
    'RULE ON AVOIDING DOUBLE COUNTING: Post-incident flight, destruction of physical evidence, '
    'and false exculpatory statements during interrogation are subsequent case exhibits, '
    'not baseline background plausibility. They must be scored strictly in the ACH Evidence Score (Layer 1). '
    'The Background Plausibility Module assesses only pre-existing candidate profile factors: '
    'Access, Opportunity, Means, Motive/Relationship, Verified Alibi, and Spatiotemporal Travel Feasibility.'
)

CRIMINAL_HISTORY_SAFEGUARD_NOTICE = (
    'LEGAL NOTICE: Criminal history is an investigative lead, not evidence of guilt. '
    'Under statutory and evidentiary rules (e.g. Section 54 Indian Evidence Act / Section 52 Bharatiya Sakshya Adhiniyam), '
    'past character and prior convictions are inadmissible as substantive proof of the charged offense. '
    'Modus operandi similarity is utilized solely to prioritize investigative lines of inquiry.'
)

METHOD_DIMENSION_WEIGHTS = {
    'weapon': 0.20,
    'entry_method': 0.25,
    'victim_type': 0.20,
    'location_type': 0.15,
    'time_pattern': 0.20
}

# ==============================================================================
# 5. SCIENTIFIC EVIDENCE SCORING AND LIKELIHOOD RATIO TABLES
# ==============================================================================

DEFAULT_BASE_RELIABILITY = {
    "DNA": 0.95,
    "fingerprint": 0.90,
    "CCTV": 0.85,
    "CDR": 0.80,
    "document": 0.70,
    "witness": 0.55,
    "confession": 0.40,
}

CLASSIFICATION_CONFIG = {
    "strong_support": {
        "numeric": 3.0,
        "penalty": 0.0,
        "bonus": 1.0,
        "label": "Strong Support"
    },
    "moderate_support": {
        "numeric": 2.0,
        "penalty": 0.0,
        "bonus": 0.65,
        "label": "Moderate Support"
    },
    "weak_support": {
        "numeric": 1.0,
        "penalty": 0.0,
        "bonus": 0.30,
        "label": "Weak Support"
    },
    "neutral": {
        "numeric": 0.0,
        "penalty": 0.0,
        "bonus": 0.0,
        "label": "Neutral / Inconclusive"
    },
    "weak_contradiction": {
        "numeric": -1.0,
        "penalty": 0.60,
        "bonus": 0.0,
        "label": "Weak Contradiction"
    },
    "moderate_contradiction": {
        "numeric": -2.0,
        "penalty": 1.50,
        "bonus": 0.0,
        "label": "Moderate Contradiction"
    },
    "strong_contradiction": {
        "numeric": -3.0,
        "penalty": 2.50,
        "bonus": 0.0,
        "label": "Strong Contradiction"
    }
}

# ==============================================================================
# CHANGE 4: SCIENTIFIC LIKELIHOOD RATIO REFERENCE TABLE & FORENSIC ERROR RATES
# ==============================================================================
# Configuration table of empirical likelihood-ratio ranges by evidence type and finding.
# Sources cited from peer-reviewed forensic science literature, NIST, PCAST, and international standards.
# Ranges are provided because exact point values are rarely known in empirical forensics.

LIKELIHOOD_RATIO_REFERENCE_TABLE: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # 1. DNA & BIOLOGICAL TRACE EVIDENCE
    # --------------------------------------------------------------------------
    "dna_single_source_full_match": {
        "evidence_type": "DNA",
        "finding_name": "Single-Source Full STR Profile Match (15+ Loci)",
        "finding_description": "Clean, unmixed biological sample matching suspect across all standard CODIS/Interpol autosomal STR loci.",
        "min_lr": 100000.0,
        "max_lr": 1000000000.0,
        "typical_lr": 1000000.0,
        "support_direction": "supports",
        "source_citation": "Butler, J. M. (2015). Advanced Topics in Forensic DNA Typing: Interpretation. Academic Press / NIST DNA Match Statistics.",
        "forensic_error_rate": "Laboratory sample handling & chain error rate estimated at 1 in 100,000 to 1 in 1,000,000; random match probability < 1 in 10^15.",
        "notes": "Judicial gold standard for individualization. Exceeds standard reasonable doubt threshold when integrity chain is verified."
    },
    "dna_partial_or_mixture_match": {
        "evidence_type": "DNA",
        "finding_name": "Partial Profile or Major Mixture Component Match (9-14 Loci)",
        "finding_description": "Degraded sample or major contributor in 2-person mixture matching suspect profile.",
        "min_lr": 50.0,
        "max_lr": 5000.0,
        "typical_lr": 500.0,
        "support_direction": "supports",
        "source_citation": "Gill, P., et al. (2006). DNA Commission of the International Society of Forensic Genetics: Recommendations on the interpretation of mixtures. Forensic Science International.",
        "forensic_error_rate": "Allelic drop-out and stutter artifact ambiguity: 2%–5%.",
        "notes": "Strong associative weight but requires probabilistic genotyping software confirmation."
    },
    "dna_low_template_match": {
        "evidence_type": "DNA",
        "finding_name": "Low-Template / Touch DNA Trace (<100 pg)",
        "finding_description": "Trace touch DNA with potential stochastic effects (allelic drop-in / drop-out).",
        "min_lr": 5.0,
        "max_lr": 50.0,
        "typical_lr": 15.0,
        "support_direction": "supports",
        "source_citation": "Balding, D. J., & Buckleton, J. (2009). Interpreting low template DNA profiles. Forensic Science International: Genetics, 4(1), 1-10.",
        "forensic_error_rate": "High secondary transfer risk and drop-in error rate: 10%–15%.",
        "notes": "Prone to innocent transfer via secondary contact; requires circumstantial corroboration."
    },
    "dna_inconclusive_mixed": {
        "evidence_type": "DNA",
        "finding_name": "Complex Unresolvable Mixture (3+ Contributors) / Inconclusive",
        "finding_description": "Insufficient quantity or complex multi-person mixture where alleles cannot be reliably attributed.",
        "min_lr": 1.0,
        "max_lr": 1.0,
        "typical_lr": 1.0,
        "support_direction": "neutral",
        "source_citation": "ENFSI DNA Working Group (2017). Guidelines for the Interpretation of Complex DNA Mixtures.",
        "forensic_error_rate": "Not probative; statistical weight null.",
        "notes": "LR = 1.0 has zero effect on hypothesis probabilities (neutral / non-diagnostic)."
    },
    "dna_definitive_exclusion": {
        "evidence_type": "DNA",
        "finding_name": "Definitive DNA Exclusion / Complete Non-Match",
        "finding_description": "Suspect's alleles are demonstrably absent at 3 or more un-degraded loci from single-source crime scene trace.",
        "min_lr": 0.000001,
        "max_lr": 0.0001,
        "typical_lr": 0.00001,
        "support_direction": "exculpates",
        "source_citation": "National Research Council. (1996). The Evaluation of Forensic DNA Evidence. National Academies Press.",
        "forensic_error_rate": "Biological mutation rate < 0.1%; exclusion is decisive for single-source perpetrator stains.",
        "notes": "Conclusively refutes single-perpetrator direct action hypothesis unless co-conspirator / accessory scenario applies."
    },

    # --------------------------------------------------------------------------
    # 2. FINGERPRINT & FRICTION RIDGE EVIDENCE
    # --------------------------------------------------------------------------
    "fingerprint_full_minutiae_match": {
        "evidence_type": "fingerprint",
        "finding_name": "Latent Print High-Clarity Identification (12+ Minutiae)",
        "finding_description": "High-clarity friction ridge impression with 12+ clear Galton minutiae matching suspect exemplar.",
        "min_lr": 1000.0,
        "max_lr": 100000.0,
        "typical_lr": 10000.0,
        "support_direction": "supports",
        "source_citation": "Ulery, B. T., et al. (2011). Accuracy and reliability of forensic latent fingerprint decisions (Black Box Study). PNAS, 108(19), 7733-7738; Neumann et al. (2012) JRSS.",
        "forensic_error_rate": "False positive match rate estimated at 0.1%–0.2% in blind verification tests.",
        "notes": "Extremely high discriminative value under ACE-V verification standard."
    },
    "fingerprint_partial_match": {
        "evidence_type": "fingerprint",
        "finding_name": "Partial Latent Print Match (7–11 Minutiae)",
        "finding_description": "Partial impression with moderate ridge flow and limited minutiae.",
        "min_lr": 20.0,
        "max_lr": 500.0,
        "typical_lr": 100.0,
        "support_direction": "supports",
        "source_citation": "Ulery, B. T., et al. (2012). Repeatability and reproducibility of decisions by latent print examiners. PLoS ONE, 7(3), e32800.",
        "forensic_error_rate": "Inconclusive rate ~30%; false positive rate ~0.5%.",
        "notes": "Valuable corroborative evidence but insufficient for sole basis of conviction."
    },
    "fingerprint_inconclusive": {
        "evidence_type": "fingerprint",
        "finding_name": "Smudged / Insufficient Ridge Detail (<6 Minutiae)",
        "finding_description": "Severely distorted or smudged latent print lacking reliable ridge flow.",
        "min_lr": 1.0,
        "max_lr": 1.0,
        "typical_lr": 1.0,
        "support_direction": "neutral",
        "source_citation": "PCAST Report (2016). Forensic Science in Criminal Courts: Ensuring Scientific Validity of Feature-Comparison Methods.",
        "forensic_error_rate": "Unusable for identification or exclusion.",
        "notes": "LR = 1.0; no diagnostic value."
    },
    "fingerprint_definitive_exclusion": {
        "evidence_type": "fingerprint",
        "finding_name": "Clear Friction Ridge Pattern Exclusion",
        "finding_description": "Clean latent print displaying whorl/loop core structure demonstrably incompatible with suspect exemplar.",
        "min_lr": 0.001,
        "max_lr": 0.05,
        "typical_lr": 0.01,
        "support_direction": "exculpates",
        "source_citation": "Ulery et al. (2011); PCAST Report (2016).",
        "forensic_error_rate": "False exclusion error rate ~7.5% across examiners due to distortion misjudgments.",
        "notes": "Strongly excludes suspect as source of that particular impression."
    },

    # --------------------------------------------------------------------------
    # 3. CCTV & VIDEO SURVEILLANCE
    # --------------------------------------------------------------------------
    "cctv_hd_facial_match": {
        "evidence_type": "CCTV",
        "finding_name": "High-Definition Unoccluded Facial Biometric Match",
        "finding_description": "High-resolution video frame with clear frontal facial landmarks, distinctive scars/proportions matching suspect.",
        "min_lr": 100.0,
        "max_lr": 1000.0,
        "typical_lr": 300.0,
        "support_direction": "supports",
        "source_citation": "Phillips, P. J., et al. (2018). Face Recognition Vendor Test (FRVT). NIST Interagency Report 8238; Facial Identification Scientific Working Group (FISWG).",
        "forensic_error_rate": "Algorithmic false match rate < 0.1%; human reviewer error under good illumination ~1%.",
        "notes": "Extremely persuasive in judicial proceedings when uncompressed original is preserved."
    },
    "cctv_clothing_gait_vehicle_match": {
        "evidence_type": "CCTV",
        "finding_name": "Clothing, Gait, or Vehicle License Plate Corroboration",
        "finding_description": "Medium-distance footage matching suspect's distinct jacket, footwear, walking gait, or vehicle make/model/registration.",
        "min_lr": 5.0,
        "max_lr": 50.0,
        "typical_lr": 15.0,
        "support_direction": "supports",
        "source_citation": "Scientific Working Group on Digital Evidence (SWGDE) & FISWG Guidelines on Forensic Facial Identification.",
        "forensic_error_rate": "Generic apparel / vehicle ambiguity error rate 5%–10%.",
        "notes": "Substantial circumstantial corroboration placing suspect/vehicle in proximity."
    },
    "cctv_inconclusive_low_res": {
        "evidence_type": "CCTV",
        "finding_name": "Grainy / Silhouette Only / Obscured Camera Angle",
        "finding_description": "Low-light or distant silhouette where biometric and apparel details cannot be resolved.",
        "min_lr": 1.0,
        "max_lr": 1.0,
        "typical_lr": 1.0,
        "support_direction": "neutral",
        "source_citation": "SWGDE Best Practices for Forensic Video Analysis (2018).",
        "forensic_error_rate": "High risk of cognitive bias and confirmation error.",
        "notes": "Non-probative; LR = 1.0."
    },
    "cctv_definitive_exclusion": {
        "evidence_type": "CCTV",
        "finding_name": "Definitive Visual Physical Trait Exclusion",
        "finding_description": "Footage clearly depicts perpetrator possessing fundamentally different physical traits (e.g., height difference >15cm, distinct tattoos, biological sex).",
        "min_lr": 0.005,
        "max_lr": 0.05,
        "typical_lr": 0.01,
        "support_direction": "exculpates",
        "source_citation": "SWGDE / ENFSI Forensic Imaging Technical Standards.",
        "forensic_error_rate": "Human misjudgment rate under disguise ~2%–5%.",
        "notes": "Powerful exculpatory evidence for the hypothesis that suspect was the physical actor."
    },

    # --------------------------------------------------------------------------
    # 4. TELECOMMUNICATIONS & CDR (CALL DETAIL RECORDS)
    # --------------------------------------------------------------------------
    "cdr_scene_tower_co_location": {
        "evidence_type": "CDR",
        "finding_name": "Scene Cell Tower Co-Location During Incident Window",
        "finding_description": "Suspect's mobile handset connected to crime scene cell tower antenna azimuth sector during incident timeframe with simultaneous active calls/SMS/data session.",
        "min_lr": 5.0,
        "max_lr": 30.0,
        "typical_lr": 12.0,
        "support_direction": "supports",
        "source_citation": "ETSI TS 102 657; Interpol Telecommunications Evidence Guide; Cellular Telecommunications Forensic Analysis (CTFA).",
        "forensic_error_rate": "Network antenna handover / RF overshoot error rate 5%–12%.",
        "notes": "Establishes opportunity and physical co-presence within antenna footprint (typically 500m-2km radius)."
    },
    "cdr_escape_route_handovers": {
        "evidence_type": "CDR",
        "finding_name": "Sequential Tower Handovers Along Escape Corridor",
        "finding_description": "Multiple sequential cell tower registrations tracking suspect device moving along the perpetrator's escape corridor matching incident timeline.",
        "min_lr": 15.0,
        "max_lr": 100.0,
        "typical_lr": 40.0,
        "support_direction": "supports",
        "source_citation": "Tart, M., et al. (2012). Historic Radio Frequency Propagation and Cell Site Analysis in Criminal Investigations.",
        "forensic_error_rate": "Handover anomaly rate < 3% across multi-tower sequence.",
        "notes": "High diagnostic value: demonstrates transit path synchronized with crime events."
    },
    "cdr_distant_tower_exclusion": {
        "evidence_type": "CDR",
        "finding_name": "Active Cell Tower Connection in Distant City / Area (50+ km)",
        "finding_description": "Handset initiated or received voice calls through a cell tower located over 50 km from scene during the crime timeframe.",
        "min_lr": 0.01,
        "max_lr": 0.10,
        "typical_lr": 0.03,
        "support_direction": "exculpates",
        "source_citation": "ETSI TS 102 657; Forensic Telecom Group Best Practices.",
        "forensic_error_rate": "Device lending / handset handover to acquaintance without owner ~5%–10%.",
        "notes": "Strong electronic alibi indicating physical impossibility of presence unless device was detached from suspect."
    },
    "cdr_switched_off_or_idle": {
        "evidence_type": "CDR",
        "finding_name": "Handset Switched Off or Inactive / No Transmission",
        "finding_description": "Handset was powered off or registered zero telecom transactions during the window.",
        "min_lr": 1.0,
        "max_lr": 2.5,
        "typical_lr": 1.2,
        "support_direction": "supports",
        "source_citation": "Interpol Telecommunications Evidence Guide.",
        "forensic_error_rate": "Routine battery depletion / coverage dead zone ambiguity.",
        "notes": "Weak circumstantial indicator of operational security; low weight."
    },

    # --------------------------------------------------------------------------
    # 5. DIGITAL FORENSICS & GPS TELEMATICS
    # --------------------------------------------------------------------------
    "digital_precise_gps_fix": {
        "evidence_type": "digital",
        "finding_name": "High-Precision GPS / Telematics Fix Inside Scene Boundary",
        "finding_description": "GPS sensor log, Google Timeline, or vehicle ECU telematics recording geographic coordinates within 15 meters of scene at exact incident time.",
        "min_lr": 50.0,
        "max_lr": 500.0,
        "typical_lr": 150.0,
        "support_direction": "supports",
        "source_citation": "ISO/IEC 27037: Guidelines for identification, collection, acquisition and preservation of digital evidence; SWGDE GPS Forensics.",
        "forensic_error_rate": "GPS hardware clock drift / multipath error < 0.1% when 4+ satellites locked.",
        "notes": "Decisive spatio-temporal placement."
    },
    "digital_incriminating_communications": {
        "evidence_type": "digital",
        "finding_name": "Encrypted Chat / Message Coordination of Offense",
        "finding_description": "Forensically recovered messages, search history (searches for target, weapons, poison), or payment transfers between conspirators.",
        "min_lr": 20.0,
        "max_lr": 200.0,
        "typical_lr": 60.0,
        "support_direction": "supports",
        "source_citation": "Casey, E. (2011). Digital Evidence and Computer Crime. Academic Press; ISO/IEC 27042.",
        "forensic_error_rate": "Context misattribution / shared device access 2%–5%.",
        "notes": "Direct evidence of mens rea, planning, and conspiracy."
    },
    "digital_remote_activity_exclusion": {
        "evidence_type": "digital",
        "finding_name": "Biometric Remote Session / Live Video Interaction Elsewhere",
        "finding_description": "Active biometric facial authentication, live interactive video conference, or continuous keystroke stream on remote computer miles away during incident.",
        "min_lr": 0.005,
        "max_lr": 0.05,
        "typical_lr": 0.01,
        "support_direction": "exculpates",
        "source_citation": "ISO/IEC 27037 Digital Evidence Standards.",
        "forensic_error_rate": "Remote desktop proxying / recorded video playback bypass < 1%.",
        "notes": "Substantiates digital alibi, severely disproving direct physical perpetrator role."
    },

    # --------------------------------------------------------------------------
    # 6. BALLISTICS & TOOLMARKS
    # --------------------------------------------------------------------------
    "ballistics_striation_match": {
        "evidence_type": "ballistics",
        "finding_name": "Microscopic Striation Match to Suspect's Seized Firearm",
        "finding_description": "Matching microscopic individual breech face, firing pin, or rifling striations between crime scene cartridge/bullet and test-fired sample from suspect weapon.",
        "min_lr": 500.0,
        "max_lr": 10000.0,
        "typical_lr": 2000.0,
        "support_direction": "supports",
        "source_citation": "Association of Firearm and Tool Mark Examiners (AFTE) Theory of Identification; PCAST Report (2016); Hamby et al. (2009).",
        "forensic_error_rate": "False positive identification rate 1.0%–1.5% under PCAST empirical evaluation.",
        "notes": "Conclusively links suspect's firearm to scene of shooting."
    },
    "ballistics_class_characteristics_only": {
        "evidence_type": "ballistics",
        "finding_name": "Matching Class Characteristics Only (Caliber & Rifling Direction)",
        "finding_description": "Cartridge matches caliber (e.g. 9mm Parabellum, 6 grooves right twist) but lacks reproducible individual striae.",
        "min_lr": 2.0,
        "max_lr": 10.0,
        "typical_lr": 4.0,
        "support_direction": "supports",
        "source_citation": "AFTE Criteria for Identification; Nichols, R. (2007) The Scientific Foundation of Firearms.",
        "forensic_error_rate": "Broad manufacturing pool; cannot individualize weapon.",
        "notes": "Consistent with weapon type, but common to thousands of firearms."
    },
    "ballistics_definitive_exclusion": {
        "evidence_type": "ballistics",
        "finding_name": "Ballistic Rifling Dimension Incompatibility / Exclusion",
        "finding_description": "Fired bullet has land and groove dimensions, pitch, or caliber demonstrably incompatible with suspect weapon.",
        "min_lr": 0.001,
        "max_lr": 0.02,
        "typical_lr": 0.005,
        "support_direction": "exculpates",
        "source_citation": "AFTE Standards; Biasotti & Murdock (1984).",
        "forensic_error_rate": "False exclusion error rate < 0.5%.",
        "notes": "Proves suspect weapon was not the discharge source."
    },

    # --------------------------------------------------------------------------
    # 7. CHEMICAL, GSR & TRACE FORENSICS
    # --------------------------------------------------------------------------
    "gsr_characteristic_3component": {
        "evidence_type": "GSR",
        "finding_name": "Characteristic 3-Component Gunshot Residue (Pb-Sb-Ba)",
        "finding_description": "SEM-EDS confirmed characteristic Primer Discharge Residue containing Lead-Antimony-Barium on suspect's hands/sleeves within 4 hours.",
        "min_lr": 15.0,
        "max_lr": 100.0,
        "typical_lr": 40.0,
        "support_direction": "supports",
        "source_citation": "ASTM E1588 Standard Guide for GSR Analysis by SEM/EDS; Dalby, O., et al. (2010). Analysis of GSR, J. Forensic Sci.",
        "forensic_error_rate": "Environmental contamination / secondary transfer from police patrol car ~2%–5%.",
        "notes": "Indicates suspect fired a weapon, was in immediate discharge plume (<2m), or handled freshly discharged firearm."
    },
    "gsr_clean_negative": {
        "evidence_type": "GSR",
        "finding_name": "Clean Negative GSR (Tested Within 2 Hours of Incident)",
        "finding_description": "Zero GSR particles detected on hands or outer cuffs swabbed shortly after incident without hand-washing opportunity.",
        "min_lr": 0.20,
        "max_lr": 0.80,
        "typical_lr": 0.50,
        "support_direction": "exculpates",
        "source_citation": "ASTM E1588 Standards; Romolo, F. S., & Margot, P. (2001). Identification of gunshot residue: a review.",
        "forensic_error_rate": "Particles can be lost through activity / wiping (half-life ~2-4 hours).",
        "notes": "Moderately weakens direct shooter hypothesis, but does not definitively rule out glove usage."
    },

    # --------------------------------------------------------------------------
    # 8. EYEWITNESS & TESTIMONY
    # --------------------------------------------------------------------------
    "eyewitness_confident_lineup_id": {
        "evidence_type": "witness",
        "finding_name": "Double-Blind Lineup Immediate High-Confidence Identification",
        "finding_description": "Witness observed perpetrator face clearly under good illumination, chose suspect from double-blind 6-person lineup with initial 90%+ confidence statement.",
        "min_lr": 5.0,
        "max_lr": 20.0,
        "typical_lr": 10.0,
        "support_direction": "supports",
        "source_citation": "Wixted, J. T., & Wells, G. L. (2017). The Information in Eyewitness Identification. Psychological Science in the Public Interest, 18(1), 10-65; NAS (2014) Identifying the Culprit.",
        "forensic_error_rate": "Initial pristine high-confidence false identification rate 8%–15%.",
        "notes": "Valuable corroboration when pristine administration protocols are followed."
    },
    "eyewitness_cross_racial_or_weapon_focus": {
        "evidence_type": "witness",
        "finding_name": "Suboptimal Lineup Identification (Weapon Focus / Cross-Racial / Delay)",
        "finding_description": "Identification made weeks later, under weapon focus stress, poor lighting, or across racial boundaries.",
        "min_lr": 1.5,
        "max_lr": 4.0,
        "typical_lr": 2.2,
        "support_direction": "supports",
        "source_citation": "National Academy of Sciences. (2014). Identifying the Culprit: Assessing Eyewitness Identification. National Academies Press.",
        "forensic_error_rate": "False identification rate under stress/weapon focus: 25%–35%.",
        "notes": "Low diagnostic power due to documented perceptual distortions."
    },
    "eyewitness_non_identification": {
        "evidence_type": "witness",
        "finding_name": "Witness Lineup Non-Identification / Stated Suspect is Not Perpetrator",
        "finding_description": "Witness who viewed perpetrator's face states unequivocally that suspect is NOT the perpetrator, or selects a known filler.",
        "min_lr": 0.10,
        "max_lr": 0.35,
        "typical_lr": 0.20,
        "support_direction": "exculpates",
        "source_citation": "Wells, G. L., & Olson, E. A. (2003). Eyewitness testimony. Annual Review of Psychology; Wixted & Wells (2017).",
        "forensic_error_rate": "Witness memory degradation / failed recognition false negative rate: 20%–30%.",
        "notes": "Substantially weakens perpetrator hypothesis."
    },

    # --------------------------------------------------------------------------
    # 9. ALIBI & DOCUMENTARY TIME-STAMPED VERIFICATION
    # --------------------------------------------------------------------------
    "alibi_certified_biometric_government": {
        "evidence_type": "alibi",
        "finding_name": "Independently Certified Biometric / Government Alibi",
        "finding_description": "Hospital trauma admission records with blood draw, airline international boarding gate biometric scan, or court recording during crime time.",
        "min_lr": 0.0001,
        "max_lr": 0.005,
        "typical_lr": 0.001,
        "support_direction": "exculpates",
        "source_citation": "Burke, T. (2007). Alibi Evidence and Corroboration. Law and Human Behavior; Indian Evidence Act Sec 11 (Plea of Alibi).",
        "forensic_error_rate": "Forged official credentials / twin impersonation error < 0.1%.",
        "notes": "Conclusive legal alibi; reduces culpability under primary actor hypothesis by 1000-fold."
    },
    "alibi_unverified_interested_party": {
        "evidence_type": "alibi",
        "finding_name": "Uncorroborated Interested Party Alibi (Spouse / Relative)",
        "finding_description": "Close family member or friend claims suspect was home, with no external digital or physical corroboration.",
        "min_lr": 0.70,
        "max_lr": 1.20,
        "typical_lr": 0.90,
        "support_direction": "neutral",
        "source_citation": "Olson, E. A., & Wells, G. L. (2004). What makes a great alibi? Law and Human Behavior, 28(2), 157-176.",
        "forensic_error_rate": "High familial bias / loyalty fabrication rate.",
        "notes": "Near-neutral evidential weight (LR approx 1.0) due to inherent credibility doubts."
    },
    "alibi_demonstrably_fabricated": {
        "evidence_type": "alibi",
        "finding_name": "Demonstrably Fabricated / Bribed False Alibi",
        "finding_description": "Claimed alibi witness confesses to being paid off, or hotel CCTV proves suspect was never at claimed alibi location.",
        "min_lr": 3.0,
        "max_lr": 15.0,
        "typical_lr": 6.0,
        "support_direction": "supports",
        "source_citation": "Wagstaff, G. F., et al. (2006). Fabricated alibis and inferences of guilt. Legal and Criminological Psychology.",
        "forensic_error_rate": "Innocent suspects sometimes fabricate alibis out of panic (~10%).",
        "notes": "Creates strong inference of guilty knowledge and pre-planned deception."
    },

    # --------------------------------------------------------------------------
    # 10. FINANCIAL, STOLEN PROPERTY & TRANSACTION RECORDS
    # --------------------------------------------------------------------------
    "financial_direct_proceeds_recovery": {
        "evidence_type": "financial",
        "finding_name": "Recovery of Stolen Proceeds / Victim Property in Suspect Custody",
        "finding_description": "Victim's debit card, stolen cash bundles with matching serial numbers, or unique family heirlooms seized directly from suspect's private custody.",
        "min_lr": 50.0,
        "max_lr": 500.0,
        "typical_lr": 120.0,
        "support_direction": "supports",
        "source_citation": "Association of Chief Police Officers (ACPO) Financial Investigation & Asset Recovery Standards; Sec 114 Indian Evidence Act.",
        "forensic_error_rate": "Innocent receiver / fence without participation in primary crime 2%–5%.",
        "notes": "Statutory presumption of guilt (recent possession of stolen property) under evidence law."
    },
    "general_irrelevant_neutral": {
        "evidence_type": "document",
        "finding_name": "Irrelevant / Non-Probative Background Exhibit",
        "finding_description": "Administrative memo, generic weather report, or background record having no probative bearing on suspect actions.",
        "min_lr": 1.0,
        "max_lr": 1.0,
        "typical_lr": 1.0,
        "support_direction": "neutral",
        "source_citation": "Heuer, R. J. (1999). Psychology of Intelligence Analysis; Federal Rule of Evidence 401.",
        "forensic_error_rate": "N/A (Zero diagnosticity).",
        "notes": "LR = 1.0; mathematically guaranteed to produce 0% change in hypothesis posteriors."
    },

    # --------------------------------------------------------------------------
    # 11. CHANGE 5: FIRST-CLASS EXCULPATORY EVIDENCE CATEGORIES
    # --------------------------------------------------------------------------
    "verified_alibi": {
        "evidence_type": "alibi",
        "finding_name": "Verified Independent Alibi (Official / Biometric / Electronic)",
        "finding_description": "Independently certified presence elsewhere during incident window corroborated by official records, hospital admissions, or biometric turnstile data.",
        "min_lr": 0.0001,
        "max_lr": 0.005,
        "typical_lr": 0.001,
        "support_direction": "exculpates",
        "source_citation": "Burke, T. (2007). Alibi Evidence and Corroboration. Law and Human Behavior; Sec 11 Indian Evidence Act (Plea of Alibi).",
        "forensic_error_rate": "Official authentication error < 0.1%.",
        "notes": "First-class clearing factor: establishes physical impossibility of presence; reduces culpability by 1000-fold."
    },
    "dna_exclusion": {
        "evidence_type": "DNA",
        "finding_name": "DNA Definitive Exclusion / Genotype Non-Match",
        "finding_description": "Suspect alleles demonstrably absent from single-source crime scene trace across 3+ un-degraded STR loci.",
        "min_lr": 0.000001,
        "max_lr": 0.0001,
        "typical_lr": 0.00001,
        "support_direction": "exculpates",
        "source_citation": "National Research Council (1996) The Evaluation of Forensic DNA Evidence; Butler (2015).",
        "forensic_error_rate": "Biological mutation rate < 0.1%; decisive elimination for single-source stain.",
        "notes": "First-class clearing factor: decisively refutes suspect as the physical biological source."
    },
    "cctv_elsewhere": {
        "evidence_type": "CCTV",
        "finding_name": "CCTV Elsewhere (Time-Stamped Video Surveillance at Distant Location)",
        "finding_description": "Time-stamped surveillance video frames definitively depicting suspect at a separate physical location during crime timeframe.",
        "min_lr": 0.0005,
        "max_lr": 0.01,
        "typical_lr": 0.002,
        "support_direction": "exculpates",
        "source_citation": "SWGDE Best Practices for Forensic Video Analysis (2018); FISWG Standards.",
        "forensic_error_rate": "Facial lookalike / system time drift error ~1%.",
        "notes": "First-class clearing factor: visual confirmation of physical presence at distant venue."
    },
    "device_location_elsewhere": {
        "evidence_type": "digital",
        "finding_name": "Device Location Elsewhere (Cell Tower / GPS Fix Distant From Scene)",
        "finding_description": "Active cellular antenna registration, Google Timeline GPS fix, or network session placing suspect device over 25 km away during crime timeframe.",
        "min_lr": 0.001,
        "max_lr": 0.05,
        "typical_lr": 0.005,
        "support_direction": "exculpates",
        "source_citation": "ETSI TS 102 657; ISO/IEC 27037 Digital Forensics Standards.",
        "forensic_error_rate": "Device lending without user present ~5%.",
        "notes": "First-class clearing factor: electronic telematics proof of physical distance."
    }
}

# ==============================================================================
# CHANGE 5: EXCULPATORY CLEARING FACTORS CONFIGURATION
# ==============================================================================
EXCULPATORY_EVIDENCE_TYPES_CONFIG: Dict[str, Dict[str, Any]] = {
    "verified_alibi": {
        "finding_category": "verified_alibi",
        "finding_name": "Verified Independent Alibi",
        "evidence_type": "alibi",
        "typical_lr": 0.001,
        "clearing_level": "conclusive",
        "clearing_rationale": "Places suspect at physically distant location; eliminates direct physical perpetrator role.",
        "statutory_reference": "Section 11 Indian Evidence Act / Section 9 Bharatiya Sakshya Adhiniyam (Plea of Alibi)"
    },
    "dna_exclusion": {
        "finding_category": "dna_exclusion",
        "finding_name": "DNA Definitive Exclusion",
        "evidence_type": "DNA",
        "typical_lr": 0.00001,
        "clearing_level": "conclusive",
        "clearing_rationale": "Scientific genotype incompatibility proves suspect did not leave the recovered biological stain.",
        "statutory_reference": "Forensic DNA Expert Opinion (Sec 45 IEA / Sec 39 BSA)"
    },
    "cctv_elsewhere": {
        "finding_category": "cctv_elsewhere",
        "finding_name": "CCTV Footage Elsewhere",
        "evidence_type": "CCTV",
        "typical_lr": 0.002,
        "clearing_level": "strong",
        "clearing_rationale": "Objective video frames demonstrate presence at separate location during crime window.",
        "statutory_reference": "Electronic Evidence under Sec 65B IEA / Sec 63 BSA"
    },
    "device_location_elsewhere": {
        "finding_category": "device_location_elsewhere",
        "finding_name": "Device Location Elsewhere",
        "evidence_type": "digital",
        "typical_lr": 0.005,
        "clearing_level": "strong",
        "clearing_rationale": "GPS/Cellular records confirm device was in a distant sector during incident timeframe.",
        "statutory_reference": "Call Detail Record (CDR) & Telematics Telecommunications Evidence"
    },
    "dna_definitive_exclusion": {
        "finding_category": "dna_definitive_exclusion",
        "finding_name": "DNA Non-Match",
        "evidence_type": "DNA",
        "typical_lr": 0.00001,
        "clearing_level": "conclusive",
        "clearing_rationale": "Single-source perpetrator stain alleles incompatible with suspect profile.",
        "statutory_reference": "Forensic DNA Analysis Standards"
    },
    "fingerprint_definitive_exclusion": {
        "finding_category": "fingerprint_definitive_exclusion",
        "finding_name": "Fingerprint Pattern Exclusion",
        "evidence_type": "fingerprint",
        "typical_lr": 0.01,
        "clearing_level": "strong",
        "clearing_rationale": "Friction ridge pattern and core structure fundamentally incompatible with suspect impression.",
        "statutory_reference": "Dactyloscopy Expert Opinion"
    },
    "ballistics_definitive_exclusion": {
        "finding_category": "ballistics_definitive_exclusion",
        "finding_name": "Ballistics Incompatibility",
        "evidence_type": "ballistics",
        "typical_lr": 0.005,
        "clearing_level": "strong",
        "clearing_rationale": "Fired projectile land/groove dimensions cannot match suspect seized firearm.",
        "statutory_reference": "Forensic Ballistics Opinion"
    },
    "eyewitness_non_identification": {
        "finding_category": "eyewitness_non_identification",
        "finding_name": "Eyewitness Non-Identification",
        "evidence_type": "witness",
        "typical_lr": 0.20,
        "clearing_level": "moderate",
        "clearing_rationale": "Eyewitness directly observed perpetrator and states suspect is not the individual.",
        "statutory_reference": "Test Identification Parade (TIP) Results"
    },
    "cdr_distant_tower_exclusion": {
        "finding_category": "cdr_distant_tower_exclusion",
        "finding_name": "Distant Cell Tower Sector",
        "evidence_type": "CDR",
        "typical_lr": 0.03,
        "clearing_level": "strong",
        "clearing_rationale": "Mobile handset connected through base station antenna >50 km away during crime window.",
        "statutory_reference": "Cell Site Location Information (CSLI)"
    },
    "digital_remote_activity_exclusion": {
        "finding_category": "digital_remote_activity_exclusion",
        "finding_name": "Active Remote Biometric Session",
        "evidence_type": "digital",
        "typical_lr": 0.01,
        "clearing_level": "strong",
        "clearing_rationale": "Live interactive biometric video authentication session recorded elsewhere during crime.",
        "statutory_reference": "Digital Telematics & Audit Trail"
    }
}

UNKNOWN_HYPOTHESIS_TITLE = "Unknown / Other Explanation"
DEFAULT_UNKNOWN_PRIOR = 10.0
