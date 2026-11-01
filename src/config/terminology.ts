/**
 * Central Multilingual Terminology Dictionary
 * 
 * Provides unified, statutory-accurate translations and wording modes across:
 * - investigator: Practical police field wording (English)
 * - methodology: Formal forensic / data science wording (English Academic)
 * - hi: Hindi (हिन्दी) - Official statutory terminology (BNS, BNSS, BSA)
 * - mr: Marathi (मराठी) - Maharashtra Police standard terminology (FIR, Panchanama, Case Diary)
 */

export interface TermEntry {
  investigator: string;
  methodology: string;
  hi: string;
  mr: string;
  description: string;
}

export type SupportedLanguage = 'en' | 'hi' | 'mr';
export type WordingMode = 'investigator' | 'methodology';

export const TERMINOLOGY: Record<string, TermEntry> = {
  // Navigation & High-level Modules
  overview: {
    investigator: 'Overview',
    methodology: 'Case Overview',
    hi: 'केस विहंगावलोकन',
    mr: 'प्रकरणाचा आढावा',
    description: 'Executive situation board, primary suspect strength, and operational summary'
  },
  priorities: {
    investigator: "Today's Priorities",
    methodology: 'Operational Priorities',
    hi: 'आज की प्राथमिकताएं',
    mr: 'आजचे प्राधान्यक्रम',
    description: 'Statutory countdowns (60/90 days), pending lab reports, open alerts, and urgent tasks'
  },
  case_file: {
    investigator: 'Case File',
    methodology: 'Docket & FIR Details',
    hi: 'केस फाईल व तपशील',
    mr: 'केस फाईल व गोषवारा',
    description: 'Official FIR parameters, statutory penal sections, IO metadata, and formal custody registry'
  },
  intake_inbox: {
    investigator: 'Intake Inbox & Reading',
    methodology: 'Multimodal Ingestion Pipeline',
    hi: 'दस्तावेज व ऑडिओ वाचन (इनटेक)',
    mr: 'कॅप्चर व एआय वाचन (इनटेक)',
    description: 'AI document reading and officer confirmation for FIRs, handwritten statements, audio logs, and WhatsApp'
  },
  exhibits: {
    investigator: 'Exhibits & Files',
    methodology: 'Evidence Register',
    hi: 'पुरावे व मुद्देमाल नोंदणी',
    mr: 'पुरावे व कागदपत्रे (मुद्देमाल)',
    description: 'Master exhibit register with chain of custody, OCR text, and forensic test results'
  },
  field_capture: {
    investigator: 'Field Capture',
    methodology: 'Mobile Field Ingest',
    hi: 'फील्ड कॅप्चर (मोबाईल)',
    mr: 'फील्ड कॅप्चर (घटनास्थळ)',
    description: 'Secure mobile field photo, audio, and seizure memo capture with tamper-proof hashing'
  },
  live_feeds: {
    investigator: 'Live Feeds & Ingestion',
    methodology: 'Data Connectors',
    hi: 'लाईव्ह फीड्स व कनेक्टर्स',
    mr: 'थेट डेटा व स्वयंचलित जोडण्या',
    description: 'Automated ingestion pipelines from forensic lab SFTPs, CCTV dumps, and network folders'
  },
  data_quality: {
    investigator: 'Data Quality & Integrity',
    methodology: 'Cryptographic Audit',
    hi: 'डेटा गुणवत्ता व अखंडता',
    mr: 'डेटा गुणवत्ता व अखंडता तपासणी',
    description: 'SHA-256 integrity audits, Section 63 BSA / 65B compliance, and low-confidence OCR verification'
  },
  malkhana: {
    investigator: 'Malkhana Register',
    methodology: 'Evidence Vault & Seals',
    hi: 'मालखाना नोंदवही व सील',
    mr: 'मुद्देमाल मालखाना नोंदवही',
    description: 'Station-level Muddimalkhana inventory, tamper-evident seals, rack allocations, and custody approvals'
  },
  suspects_theories: {
    investigator: 'Suspects and Theories',
    methodology: 'Hypotheses & Elimination (ACH)',
    hi: 'संशयित व तपास सिद्धांत',
    mr: 'संशयित व तपास सिद्धांत',
    description: 'Suspect case strength, alibi verification, and forensic proof elimination matrix'
  },
  witnesses: {
    investigator: 'Witnesses & Statements',
    methodology: 'Interviews & Testimonies',
    hi: 'साक्षीदार व नोंदवलेले जबाब',
    mr: 'साक्षीदार व त्यांचे जबाब',
    description: 'Witness testimonies, suspect interrogations, audio recordings, and Section 180 BNSS / 161 CrPC statements'
  },
  link_analysis: {
    investigator: 'Link Analysis & Graph',
    methodology: 'Knowledge Graph & Entities',
    hi: 'संबंध व नेटवर्क विश्लेषण',
    mr: 'संबंध व नेटवर्क विश्लेषण (दुवे)',
    description: 'Unified visual graph, people & places registry, workspace, and cross-case intelligence'
  },
  phone_bank: {
    investigator: 'Phone & Bank Analytics',
    methodology: 'CDR & Financial Analytics',
    hi: 'सीडीआर व बँक व्यवहार विश्लेषण',
    mr: 'सीडीआर व बँक व्यवहार विश्लेषण',
    description: 'Call Detail Records (CDR), cell tower triangulation, and suspicious bank transaction trails'
  },
  map_timeline: {
    investigator: 'Map & Timeline',
    methodology: 'Spatio-Temporal Analysis',
    hi: 'घटना नकाशा व कालक्रम',
    mr: 'घटना नकाशा व कालक्रम',
    description: 'Minute-by-minute chronology and interactive crime scene / cell tower mapping'
  },
  alibi_conflicts: {
    investigator: 'Alibi & Statement Conflicts',
    methodology: 'Contradiction Engine',
    hi: 'अलिबाय व जबाबांमधील विसंगती',
    mr: 'अलिबाय व जबाबांमधील विसंगती',
    description: 'Automated cross-examination of suspect claims against CDR, witnesses, and timestamps'
  },
  missing_evidence: {
    investigator: 'Missing Evidence & Gaps',
    methodology: 'Investigation Plan & Gaps',
    hi: 'अपूर्ण पुरावे व तपास कृती',
    mr: 'अपूर्ण पुरावे व तपास कृती',
    description: 'Critical proof required to secure conviction, procedural gap detection, and assigned field tasks'
  },
  defense_stress_test: {
    investigator: 'Trial Defense Stress-Test',
    methodology: "Devil's Advocate Analysis",
    hi: 'न्यायालयीन बचाव चाचणी (तपास पडताळणी)',
    mr: 'न्यायालयीन बचाव प्रतिवाद चाचणी',
    description: 'Stress-tests case against reasonable doubt: assembles defense attorney counter-case before trial'
  },
  chargesheet: {
    investigator: 'Chargesheet Assistant',
    methodology: 'Statutory Final Report (Sec 193 BNSS)',
    hi: 'चार्जशीट सहाय्यक (दोषारोपपत्र)',
    mr: 'दोषारोपपत्र सहाय्यक (चार्जशीट)',
    description: 'Court-ready chargesheet generator compliant with BNSS / CrPC statutory prosecution standards'
  },
  handover: {
    investigator: 'Officer Handover',
    methodology: 'Transfer Briefing Memo',
    hi: 'अधिकारी हस्तांतरण नोंद',
    mr: 'तपास अधिकारी हस्तांतरण नोंद',
    description: 'Four-eyes transfer briefing, unverified leads memo, and investigator custody handover'
  },
  activity_log: {
    investigator: 'Activity & Audit Log',
    methodology: 'Cryptographic Audit Trail',
    hi: 'अखंड ऑडिट नोंदवही',
    mr: 'अखंड ऑडिट नोंदवही',
    description: 'Court-admissible tamper-evident activity log tracking every classification, edit, and export'
  },
  reports: {
    investigator: 'Reports & Export',
    methodology: 'Briefing Packs & Products',
    hi: 'अहवाल व कागदपत्रे',
    mr: 'अहवाल व न्यायालयीन नस्ती',
    description: 'Generate briefing packs, forensic summaries, timeline exhibits, and supervisory status reports'
  },

  // Statutory & Procedural Terms
  fir: {
    investigator: 'First Information Report (FIR)',
    methodology: 'Initial Crime Report',
    hi: 'प्रथम सूचना अहवाल (एफ.आय.आर.)',
    mr: 'प्रथम खबरी अहवाल (एफ.आय.आर.)',
    description: 'First Information Report under Section 173 BNSS / 154 CrPC'
  },
  panchanama: {
    investigator: 'Panchanama / Spot Memo',
    methodology: 'Contemporaneous Record of Seizure',
    hi: 'पंचनामा (घटनास्थळ / जप्ती पंचनामा)',
    mr: 'पंचनामा (घटनास्थळ / जप्ती पंचनामा)',
    description: 'Contemporaneous record of inspection or seizure attested by two independent witnesses'
  },
  remand: {
    investigator: 'Police / Judicial Custody (Remand)',
    methodology: 'Pre-Trial Detention Order',
    hi: 'पोलीस / न्यायालयीन कोठडी (रिमांड)',
    mr: 'पोलीस / न्यायालयीन कोठडी (रिमांड)',
    description: 'Custody authorization under Section 187 BNSS / 167 CrPC (max 60/90 days)'
  },
  sec_180_bnss: {
    investigator: 'Police Statement (Sec 180 BNSS / 161 CrPC)',
    methodology: 'Witness Examination by Police',
    hi: 'पोलीस जबाब (कलम १८० बीएनएसएस / १६१ सीआरपीसी)',
    mr: 'पोलीस जबाब (कलम १८० बीएनएसएस / १६१ सीआरपीसी)',
    description: 'Statement recorded by IO during investigation, non-admissible as substantive evidence'
  },
  sec_183_bnss: {
    investigator: 'Magisterial Confession (Sec 183 BNSS / 164 CrPC)',
    methodology: 'Judicial Recording of Confession',
    hi: 'दंडाधिकारी जबाब / कबुली (कलम १८३ बीएनएसएस / १६४ सीआरपीसी)',
    mr: 'दंडाधिकारी जबाब / कबुली (कलम १८३ बीएनएसएस / १६४ सीआरपीसी)',
    description: 'Confession or statement recorded under oath before a Judicial Magistrate'
  },
  sec_63_bsa: {
    investigator: 'Electronic Record Certificate (Sec 63 BSA / 65B IEA)',
    methodology: 'Digital Evidence Admissibility Certification',
    hi: 'इलेक्ट्रॉनिक पुरावा प्रमाणपत्र (कलम ६३ बीएसए / ६५बी पुरावा कायदा)',
    mr: 'इलेक्ट्रॉनिक पुरावा प्रमाणपत्र (कलम ६३ बीएसए / ६५बी पुरावा कायदा)',
    description: 'Mandatory certificate from device custodian required for court admissibility of digital records'
  },
  sec_23_bsa: {
    investigator: 'Recovery on Disclosure (Sec 23 BSA / 27 IEA)',
    methodology: 'Information Leading to Discovery',
    hi: 'खुलासा जप्ती पंचनामा (कलम २३ बीएसए / २७ पुरावा कायदा)',
    mr: 'कबुलीजबाब जप्ती पंचनामा (कलम २३ बीएसए / २७ पुरावा कायदा)',
    description: 'Statement by accused in custody leading directly to recovery of hidden weapon or material object'
  },
  default_bail: {
    investigator: 'Statutory Default Bail Countdown',
    methodology: '60/90 Day Detention Boundary',
    hi: 'वैधानिक डीफॉल्ट जामीन मर्यादा (६०/९० दिवस)',
    mr: 'वैधानिक डीफॉल्ट जामीन मर्यादा (६०/९० दिवस)',
    description: 'Accused right to bail if investigation chargesheet is not filed within 60 or 90 days'
  },

  // Reading Card & Intake Terms
  reading_card_title: {
    investigator: 'What the AI Read (Officer Review Required)',
    methodology: 'Extracted Entity Candidates & Citations',
    hi: 'एआय द्वारे वाचलेला तपशील (तपासी अधिकाऱ्याची मंजुरी आवश्यक)',
    mr: 'एआय द्वारे वाचलेला तपशील (तपासी अधिकाऱ्याची खात्री आवश्यक)',
    description: 'Extracted values from scanned documents, statements, audio logs, and chats pending human confirmation'
  },
  confirm_action: {
    investigator: 'Confirm & Accept',
    methodology: 'Accept Extraction',
    hi: 'स्वीकार करा (योग्य)',
    mr: 'स्वीकार करा (बरोबर)',
    description: 'Accept the extracted field and commit to official case registry'
  },
  edit_action: {
    investigator: 'Edit Field',
    methodology: 'Manual Override',
    hi: 'दुरुस्ती करा',
    mr: 'बदल / दुरुस्ती करा',
    description: 'Correct the AI reading before committing'
  },
  reject_action: {
    investigator: 'Reject Field',
    methodology: 'Discard Candidate',
    hi: 'नाकारा (अयोग्य)',
    mr: 'नाकारा (चूक)',
    description: 'Reject the extracted value as spurious or inaccurate'
  },
  keyboard_shortcuts_hint: {
    investigator: 'Shortcuts: [C] Confirm • [E] Edit • [R] Reject • [Tab] Next field',
    methodology: 'Keyboard: [C] Validate • [E] Modify • [R] Invalidate',
    hi: 'शॉर्टकट: [C] स्वीकृती • [E] दुरुस्ती • [R] नकार • [Tab] पुढील फील्ड',
    mr: 'शॉर्टकट: [C] बरोबर • [E] दुरुस्ती • [R] नकार • [Tab] पुढील नोंद',
    description: 'High-speed keyboard shortcuts for low-typing review'
  },
  unconfirmed_isolation_notice: {
    investigator: 'Strict Isolation: Unconfirmed values remain drafts and never affect suspect scoring, prior records, or court documents.',
    methodology: 'Isolation Guarantee: Draft extractions are walled off from probabilistic models and export payloads.',
    hi: 'कडक नियम: जोपर्यंत तपासी अधिकारी खात्री करत नाही, तोपर्यंत हा डेटा अंतिम केस किंवा न्यायालयात सादर होत नाही.',
    mr: 'कडक नियम: जोपर्यंत तपासी अधिकारी खात्री करत नाही, तोपर्यंत हा कच्चा डेटा अंतिम केस किंवा न्यायालयात वापरला जात नाही.',
    description: 'Legal safeguard ensuring AI extractions never leak unverified into official court records'
  }
};

/**
 * Returns translated string for a given key, language, and wording mode.
 * Falls back per key: requested lang -> en (investigator) -> raw key.
 */
export function getTerminology(
  key: string,
  lang: SupportedLanguage = 'en',
  wordingMode: WordingMode = 'investigator'
): string {
  const entry = TERMINOLOGY[key];
  if (!entry) return key;

  if (lang === 'hi') return entry.hi || entry[wordingMode] || entry.investigator;
  if (lang === 'mr') return entry.mr || entry[wordingMode] || entry.investigator;

  return entry[wordingMode] || entry.investigator || key;
}

/**
 * Generates an i18next resource dictionary for seamless hook usage.
 */
export function buildI18nResources() {
  const enInvestigator: Record<string, string> = {};
  const enMethodology: Record<string, string> = {};
  const hi: Record<string, string> = {};
  const mr: Record<string, string> = {};

  for (const [key, item] of Object.entries(TERMINOLOGY)) {
    enInvestigator[key] = item.investigator;
    enMethodology[key] = item.methodology;
    hi[key] = item.hi;
    mr[key] = item.mr;
  }

  return {
    en: {
      translation: enInvestigator,
      methodology: enMethodology,
    },
    hi: {
      translation: hi,
    },
    mr: {
      translation: mr,
    }
  };
}

