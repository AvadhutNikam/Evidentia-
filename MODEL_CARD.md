# Model Card: Evidentia-AI Cognitive Analysis & Forensic Scoring Engine
**Model Version**: v2.4-probabilistic  
**Release Date**: October 2026  
**License**: Proprietary / Government Law Enforcement Restricted  
**Primary Standard**: Sherman Kent Center Analysis of Competing Hypotheses (ACH) & ENFSI Guideline for Evaluative Reporting  

---

## 1. Model Details

### Basic Information
- **Model Name**: Evidentia-AI Forensic Intelligence & Cognitive Debiasing System
- **Developers**: Evidentia AI Applied Forensics & Engineering Team
- **Model Type**: Hybrid Symbolic-Probabilistic Updating (Commutative Bayesian Likelihood Ratios) combined with Large Language Model Information Extraction (Google Gemini 2.5 series)
- **Primary Engine**: 3-Layer Probabilistic Synthesis:
  1. *Layer 1*: Physical & Forensic Evidence Likelihood Ratios (Bayesian Matrix Updating)
  2. *Layer 2*: Objective Background Plausibility Priors (Means, Motive, Opportunity, Travel Feasibility)
  3. *Layer 3*: Safeguarded Criminal History Prior (Hard-capped at $+10.0\%$ max contribution)
- **Upstream Foundation Models**: Gemini Flash-Lite (`gemini-flash-lite-latest`), Gemini Flash (`gemini-1.5-flash`), Gemini Pro (`gemini-1.5-pro`)

---

## 2. Intended Use

### Primary Intended Uses
- **Investigative Decision Support**: Assisting law enforcement detectives, intelligence analysts, and forensic examiners in structuring complex evidence dockets.
- **Cognitive Debiasing**: Counteracting confirmation bias, premature suspect fixation, and investigative tunnel vision via Richards J. Heuer Jr.’s Analysis of Competing Hypotheses.
- **Forensic Diagnosticity Assessment**: Automatically determining whether an exhibit actually discriminates between competing theories or is merely consistent with all hypotheses.
- **Investigative Gap Detection**: Highlighting missing evidentiary items (e.g., missing alibi verification, unverified weapon recovery) and proposing the next best investigative steps.
- **Chain of Custody & Audit Integrity**: Generating court-admissible dossiers with cryptographic SHA-256 Merkle chain verification and Section 65B Indian Evidence Act / Section 63 BSA certificates.

### Out-of-Scope & Prohibited Uses
- **Autonomous Judicial Verdicts**: Evidentia-AI is **never** an autonomous adjudicator. It does not replace judges, magistrates, or juries.
- **Autonomous Arrest or Detention**: Law enforcement authorities must never issue arrest warrants or detentions based solely on system probability rankings.
- **Demographic Profiling**: Generating inferences or suspicion based on caste, religion, ethnicity, gender, sexual orientation, or socioeconomic status is strictly prohibited and technically prevented by the architecture.
- **Unverified AI Evidence in Court**: Unverified AI quotes or unanchored claims must never be presented in legal proceedings without human corroboration against primary source documents.

---

## 3. Data Used

### Input Modalities
- **Primary Documents**: Forensic laboratory examination reports (DNA, ballistics, toxicology), autopsy protocols, CCTV extraction logs, Call Detail Records (CDR), cellular tower dumps, financial ledger exports, cyber incident packet captures (PCAP), and authenticated witness interview transcripts.
- **Supported File Types**: PDF, PNG, JPG, WEBP, MP3, WAV, MP4, TXT, CSV, JSON, PCAP.

### Evaluation & Calibration Benchmark Dataset
- **Evaluation Corpus**: 20 comprehensive synthetic criminal and digital investigation dockets with known ground truths:
  - Violent crimes (homicides, aggravated robberies, kidnapping)
  - Financial & corporate fraud (insider trading, embezzlement, falsified accounting)
  - Cybercrime & digital sabotage (unauthorized intrusion, ransomware deployment, data exfiltration)
- **Baseline Models Compared**:
  1. *Keyword / Frequency Heuristic Baseline*
  2. *Plain Zero-Shot LLM Reasoning Baseline*
  3. *Legacy Additive Scoring Engine (Old System)*
  4. *Evidentia-AI Full Bayesian ACH Engine*

---

## 4. Known Failures & Limitations

| Limitation Area | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **OCR Quality & Degraded Scans** | Heavily corrupted scans or degraded handwriting can cause entity or date extraction errors. | Multi-pass OCR pre-processing, character boundary validation, and mandatory manual analyst transcript correction tools. |
| **Shared Evidence Dependency** | Multiple exhibits stemming from a single common source (e.g., three witnesses repeating the same rumor) can cause double-counting if treated as independent. | Automated Dependency Grouping (`W-SHINDE-CLUSTER`) with sub-linear logarithmic damping multipliers ($1/\sqrt{K}$). |
| **Uncorroborated Alibis** | Vague testimonial alibis lacking digital/cellular or CCTV anchor stamps cannot be treated as definitive exclusions. | Multi-tier alibi classification: only timestamped, third-party corroborated records receive high exculpatory weight. |
| **Open-World Perpetrators** | If the true perpetrator is not included in the initial suspect list, closed-set evaluation produces misleading rankings. | Automatic inclusion and calibration of an explicit *"Unknown / Alternative Perpetrator"* hypothesis in every case docket. |

---

## 5. Counterfactual Bias & Fairness Evaluation

### Demographic Parity Results
- **Methodology**: Systematic counterfactual perturbation testing across raw exhibit text, altering:
  - Names (e.g., changing suspect name between different cultural/ethnic profiles)
  - Religion markers and caste surnames
  - Gender pronouns and honorifics
  - Geographic/regional origins
- **Testing Results**:
  - Total Tested Matched Pairs: **100+ Counterfactual Pairs**
  - Score Disparities Detected: **0.00%**
  - Suspect Ranking Flips: **0 (Zero)**
  - Diagnostic Consistency: **100.0% invariant**
- **Architectural Safeguard**:
  Names and demographic identity markers **never enter the scoring calculation path**. Bayesian updates operate exclusively on blinded hypothesis indices ($H_1, H_2, \dots$) and objective forensic category codes (`dna_single_source_full_match`, `latent_fingerprint_match`, `verified_alibi_timestamped`).

---

## 6. Responsible-Use & Statutory Compliance Notice

> [!IMPORTANT]
> **LEGAL DOCTRINE: DECISION SUPPORT, NOT A VERDICT**  
> Evidentia-AI outputs are analytical aids designed to minimize human cognitive bias and organize evidentiary logic. Every finding, probability score, and priority ranking is advisory and must be independently verified by a qualified human investigator.

### Statutory Adherence
1. **Section 54, Indian Evidence Act, 1872 / Section 52, Bharatiya Sakshya Adhiniyam, 2023**:
   - Criminal history is partitioned from active exhibit scoring.
   - Character evidence contribution is hard-capped at $+10.0\%$ and cannot overcome contradictory physical exhibits.
2. **Section 65B, Indian Evidence Act, 1872 / Section 63, Bharatiya Sakshya Adhiniyam, 2023**:
   - Cryptographic SHA-256 byte-level hash verification on upload.
   - Court-admissible electronic record certificate generation with custodian attestation.
3. **Append-Only Merkle Audit Ledger**:
   - Every analyst override, evidence inspection, and scoring recalculation is cryptographically signed and chained.
   - Tamper-evident ledger ensures full transparency under judicial cross-examination.

