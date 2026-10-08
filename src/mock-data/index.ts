// src/mock-data/index.ts
import { Case, Evidence, Entity, TimelineEvent, Contradiction, Hypothesis, InvestigationTask, GeoCase } from '../types';

// ============================================================
// 1. CASES CATALOG (High-Profile Distinct Multi-Jurisdiction Dockets)
// ============================================================
export const mockCases: Case[] = [
  {
    id: 'FIR-2009-MH-PUN-534',
    name: 'State of Maharashtra vs. Yogesh Raut & 3 Others (Pune Techie Nayana Pujari Case)',
    title: 'State of Maharashtra vs. Yogesh Raut & 3 Others (Pune Techie Nayana Pujari Case)',
    description: 'Landmark Pune investigation into abduction, robbery, and murder of Synechron software engineer Nayana Pujari. Analyzed 4 suspects through ATM CCTV, CDR tracking, and approver confession, culminating in death penalty conviction.',
    status: 'Closed',
    priority: 'High',
    createdDate: '2009-10-08T08:30:00Z',
    lastUpdated: '2017-05-09T17:00:00Z',
    evidenceCount: 10,
    assignedInvestigators: ['PI Kishor Mhaswade (Yerwada PS)', 'ACP Vinod Satav (Crime Branch)'],
    case_type: 'Homicide',
    location: 'Yerwada Police Station / Kharadi, Pune',
    victim: 'Nayana Pujari (28, Software Engineer)',
    key_details: 'IPC 361 (Abduction), 376 (Rape), 302 (Murder), 120B (Conspiracy), 397 (Robbery). 4 Suspects investigated: Yogesh Raut (Prime Convict), Rajesh Chaudhari (Turned Approver), Mahesh Thakur & Vishwas Kadam (Accomplices).',
    incident_date: '2009-10-07T20:15:00Z',
    created_at: '2009-10-08T08:30:00Z',
    created_by: 'PI Kishor Mhaswade',
  },
  {
    id: 'FIR-2024-MH-PUN-089',
    name: 'State of Maharashtra vs. Accused (Pune Cyber Heist & Data Exfiltration)',
    title: 'State of Maharashtra vs. Accused (Pune Cyber Heist & Data Exfiltration)',
    description: 'Investigation under Sec 154 CrPC into unauthorized database intrusion, exfiltration of 42GB financial algorithms, and extortion demand at TechAxis Pune.',
    status: 'Active',
    priority: 'High',
    createdDate: '2024-09-02T11:30:00Z',
    lastUpdated: '2024-09-06T18:00:00Z',
    evidenceCount: 3,
    assignedInvestigators: ['PI Vikram Salunkhe (Cyber Crime PS)', 'PSI Mayur Jadhav'],
    case_type: 'Cyber Crime',
    location: 'Cyber Crime PS, Shivajinagar, Pune',
    victim: 'TechAxis Corporation / Banking Infrastructure',
    key_details: 'IPC 420 (Cheating), 468 (Forgery), 120B (Conspiracy), 384 (Extortion) | IT Act Sec 66C, 66D. CDR cell tower pings correlate with exfiltrated files.',
    incident_date: '2024-09-01T02:14:00Z',
    created_at: '2024-09-02T11:30:00Z',
    created_by: 'PI Vikram Salunkhe',
  },
  {
    id: 'FIR-2024-KA-BLR-142',
    name: 'State of Karnataka vs. Accused (Indiranagar Homicide & Armed Robbery)',
    title: 'State of Karnataka vs. Accused (Indiranagar Homicide & Armed Robbery)',
    description: 'Karnataka Police FIR investigation into late-night residential break-in, fatal assault, and robbery of gold jewelry in Indiranagar, Bengaluru.',
    status: 'Under Investigation',
    priority: 'High',
    createdDate: '2024-08-15T03:15:00Z',
    lastUpdated: '2024-08-20T14:30:00Z',
    evidenceCount: 3,
    assignedInvestigators: ['Insp. B. Manjunath', 'SI Ramesh Kumar'],
    case_type: 'Homicide',
    location: 'Indiranagar Police Station, Bengaluru',
    victim: 'Dr. Ananya Rao & Family',
    key_details: 'IPC 302 (Murder), 397 (Robbery with deadly weapon). Forensic latent fingerprints lifted from balcony match CID criminal database records.',
    incident_date: '2024-08-14T23:45:00Z',
    created_at: '2024-08-15T03:15:00Z',
    created_by: 'Insp. B. Manjunath',
  },
  {
    id: 'CASE-BOS-2013-001',
    name: 'United States v. Tsarnaev (2013 Boston Marathon Bombing)',
    title: 'United States v. Tsarnaev (2013 Boston Marathon Bombing)',
    description: 'Federal criminal prosecution and multi-agency JTTF investigation into two pressure cooker bomb detonations near the Boston Marathon finish line.',
    status: 'Closed',
    priority: 'High',
    createdDate: '2013-04-15T15:30:00Z',
    lastUpdated: '2013-04-24T20:00:00Z',
    evidenceCount: 3,
    assignedInvestigators: ['Special Agent in Charge R. DesLauriers', 'FBI JTTF Task Force'],
    case_type: 'Terrorism',
    location: 'Boylston Street / US District Court, Boston, MA',
    victim: 'Marathon Spectators & Participants (3 deceased, 281 injured)',
    key_details: '18 U.S.C. 2332a (Use of Weapon of Mass Destruction). Dual IEDs fabricated from Fagor 6-quart pressure cookers, BBs, nails, and pyrotechnic powder.',
    incident_date: '2013-04-15T14:49:00Z',
    created_at: '2013-04-15T15:30:00Z',
    created_by: 'FBI Joint Terrorism Task Force',
  }
];

// ============================================================
// 2. MASTER EVIDENCE EXHIBITS
// ============================================================
export const mockEvidence: Evidence[] = [
  // --- Case 0: Pune Techie Nayana Pujari Case Exhibits ---
  {
    id: 'E-NP-001',
    caseId: 'FIR-2009-MH-PUN-534',
    case_id: 'FIR-2009-MH-PUN-534',
    fileName: 'fir_copy_534_2009_yerwada.pdf',
    file_name: 'fir_copy_534_2009_yerwada.pdf',
    fileType: 'Document',
    file_type: 'Document',
    source: 'Yerwada Police Station, Pune',
    uploadDate: '2009-10-08T08:45:00Z',
    upload_date: '2009-10-08T08:45:00Z',
    uploadedBy: 'PI Kishor Mhaswade',
    uploaded_by: 'PI Kishor Mhaswade',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 195000,
    tags: ['FIR', 'Yerwada PS', 'IPC 302', 'IPC 376'],
    extracted_text: 'MAHARASHTRA POLICE. FIRST INFORMATION REPORT (Sec 154 CrPC). PS Yerwada, Pune. FIR No: 534/2009. Date: 08-10-2009. Complainant: Abhijit Pujari. Missing person Nayana Pujari, last seen boarding cab at Kharadi bypass around 20:15 hours.'
  },
  {
    id: 'E-NP-002',
    caseId: 'FIR-2009-MH-PUN-534',
    case_id: 'FIR-2009-MH-PUN-534',
    fileName: 'sbi_atm_cctv_swargate_withdrawal.mp4',
    file_name: 'sbi_atm_cctv_swargate_withdrawal.mp4',
    fileType: 'Video',
    file_type: 'Video',
    source: 'State Bank of India ATM, Swargate / Hadapsar',
    uploadDate: '2009-10-09T14:30:00Z',
    upload_date: '2009-10-09T14:30:00Z',
    uploadedBy: 'ACP Vinod Satav',
    uploaded_by: 'ACP Vinod Satav',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 18400000,
    tags: ['ATM CCTV', 'Swargate', 'Financial Trail', 'Yogesh Raut'],
    extracted_text: 'CCTV footage time-stamped 2009-10-07 22:45:18. Individual identified as Yogesh Raut withdrawing cash totaling Rs 61,000 using Nayana Pujari\'s debit card.'
  },
  {
    id: 'E-NP-003',
    caseId: 'FIR-2009-MH-PUN-534',
    case_id: 'FIR-2009-MH-PUN-534',
    fileName: 'qualis_cab_inspection_forensics.jpg',
    file_name: 'qualis_cab_inspection_forensics.jpg',
    fileType: 'Image',
    file_type: 'Image',
    source: 'State CID / Forensic Science Laboratory Pune',
    uploadDate: '2009-10-16T11:00:00Z',
    upload_date: '2009-10-16T11:00:00Z',
    uploadedBy: 'Forensic Officer D. Sonawane',
    uploaded_by: 'Forensic Officer D. Sonawane',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 4200000,
    tags: ['Vehicle Inspection', 'Toyota Qualis', 'Blood Stains', 'Sec 27 Indian Evidence Act'],
    extracted_text: 'Inspection of Toyota Qualis (Reg MH-12-BP-2033). Blood traces lifted from middle row seats matched victim blood group. Fingerprint impressions of Yogesh Raut and Mahesh Thakur lifted from steering and rear handles.'
  },

  // --- Case 1: Pune Cyber Crime FIR Exhibits ---
  {
    id: 'E-IND-001',
    caseId: 'FIR-2024-MH-PUN-089',
    case_id: 'FIR-2024-MH-PUN-089',
    fileName: 'certified_fir_copy_214_2024.pdf',
    file_name: 'certified_fir_copy_214_2024.pdf',
    fileType: 'Document',
    file_type: 'Document',
    source: 'Cyber Crime PS Pune',
    uploadDate: '2024-09-02T11:45:00Z',
    upload_date: '2024-09-02T11:45:00Z',
    uploadedBy: 'PI Vikram Salunkhe',
    uploaded_by: 'PI Vikram Salunkhe',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 145200,
    tags: ['FIR', 'Official Record', 'CrPC 154'],
    extracted_text: 'POLICE DEPARTMENT, MAHARASHTRA STATE. FIRST INFORMATION REPORT under Sec 154 CrPC. PS: Cyber Crime, Pune City. Complainant: Rajesh Kulkarni. Offenses: IPC 420, 468, 120B, 384; IT Act 66C, 66D.'
  },
  {
    id: 'E-IND-002',
    caseId: 'FIR-2024-MH-PUN-089',
    case_id: 'FIR-2024-MH-PUN-089',
    fileName: 'cdr_hinjewadi_tower_dump.csv',
    file_name: 'cdr_hinjewadi_tower_dump.csv',
    fileType: 'Document',
    file_type: 'Document',
    source: 'Telecom Service Provider / CDR Cell',
    uploadDate: '2024-09-03T10:15:00Z',
    upload_date: '2024-09-03T10:15:00Z',
    uploadedBy: 'PSI Mayur Jadhav',
    uploaded_by: 'PSI Mayur Jadhav',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 894000,
    tags: ['CDR', 'Cell Tower', 'Telecom'],
    extracted_text: 'Cell ID: HINJ-PH1-4029. Time: 2024-09-01 02:14:22 IST. Target MSISDN: +91 98230 XXXXX (Rohan Deshmukh).'
  },
  {
    id: 'E-IND-003',
    caseId: 'FIR-2024-MH-PUN-089',
    case_id: 'FIR-2024-MH-PUN-089',
    fileName: 'vpn_gateway_syslog_auth.log',
    file_name: 'vpn_gateway_syslog_auth.log',
    fileType: 'Document',
    file_type: 'Document',
    source: 'TechAxis Firewall Gateway Logs',
    uploadDate: '2024-09-04T09:30:00Z',
    upload_date: '2024-09-04T09:30:00Z',
    uploadedBy: 'PI Vikram Salunkhe',
    uploaded_by: 'PI Vikram Salunkhe',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 340000,
    tags: ['Firewall', 'VPN Log', 'Exfiltration'],
    extracted_text: '2024-09-01 02:11:05 SSH authenticated for user sysadmin_rdeshmukh from IP 185.220.101.5. 42.1 GB transferred via SFTP protocol.'
  },

  // --- Case 2: Bengaluru Homicide Exhibits ---
  {
    id: 'E-BLR-001',
    caseId: 'FIR-2024-KA-BLR-142',
    case_id: 'FIR-2024-KA-BLR-142',
    fileName: 'victoria_hospital_autopsy_report.pdf',
    file_name: 'victoria_hospital_autopsy_report.pdf',
    fileType: 'Document',
    file_type: 'Document',
    source: 'Dept of Forensic Medicine, Victoria Hospital',
    uploadDate: '2024-08-15T10:00:00Z',
    upload_date: '2024-08-15T10:00:00Z',
    uploadedBy: 'Dr. K. Venkat',
    uploaded_by: 'Dr. K. Venkat',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 280000,
    tags: ['Autopsy', 'Medical', 'Homicide'],
    extracted_text: 'Post-Mortem Examination Report PM-842/2024. Cause of death: Hemorrhagic shock secondary to sharp-force trauma to carotid artery.'
  },
  {
    id: 'E-BLR-002',
    caseId: 'FIR-2024-KA-BLR-142',
    case_id: 'FIR-2024-KA-BLR-142',
    fileName: 'balcony_latent_fingerprint_card.jpg',
    file_name: 'balcony_latent_fingerprint_card.jpg',
    fileType: 'Image',
    file_type: 'Image',
    source: 'Fingerprint Bureau, CID Bengaluru',
    uploadDate: '2024-08-16T14:20:00Z',
    upload_date: '2024-08-16T14:20:00Z',
    uploadedBy: 'Insp. B. Manjunath',
    uploaded_by: 'Insp. B. Manjunath',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 3200000,
    tags: ['Forensics', 'Latent Print', 'CID Match'],
    extracted_text: 'Right thumb loop pattern lifted from 1st floor balcony sliding glass. Automated match score 99.4% against criminal record of Suresh Gowda (CID Convict #4412).'
  },
  {
    id: 'E-BLR-003',
    caseId: 'FIR-2024-KA-BLR-142',
    case_id: 'FIR-2024-KA-BLR-142',
    fileName: 'cctv_100ft_road_getaway_auto.mp4',
    file_name: 'cctv_100ft_road_getaway_auto.mp4',
    fileType: 'Video',
    file_type: 'Video',
    source: 'BBMP Traffic Surveillance / Indiranagar 100ft Rd',
    uploadDate: '2024-08-16T18:00:00Z',
    upload_date: '2024-08-16T18:00:00Z',
    uploadedBy: 'SI Ramesh Kumar',
    uploaded_by: 'SI Ramesh Kumar',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 21500000,
    tags: ['CCTV', 'Getaway', 'Auto Rickshaw'],
    extracted_text: 'Traffic camera recording 2024-08-14 23:58:12. Yellow/green auto-rickshaw departing towards Old Madras Road at high velocity.'
  },

  // --- Case 3: Boston Bombing Exhibits ---
  {
    id: 'E-BOS-001',
    caseId: 'CASE-BOS-2013-001',
    case_id: 'CASE-BOS-2013-001',
    fileName: 'lord_taylor_cctv_suspect2.mp4',
    file_name: 'lord_taylor_cctv_suspect2.mp4',
    fileType: 'Video',
    file_type: 'Video',
    source: 'FBI Evidence Response Team / Lord & Taylor',
    uploadDate: '2013-04-16T12:00:00Z',
    upload_date: '2013-04-16T12:00:00Z',
    uploadedBy: 'Special Agent C. Walsh',
    uploaded_by: 'Special Agent C. Walsh',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 24500000,
    tags: ['CCTV', 'Boylston Street', 'Finish Line'],
    extracted_text: 'Surveillance video at 671 Boylston Street showing individual in white baseball cap dropping backpack in front of Forum restaurant.'
  },
  {
    id: 'E-BOS-002',
    caseId: 'CASE-BOS-2013-001',
    case_id: 'CASE-BOS-2013-001',
    fileName: 'fbi_ied_component_metallurgy_report.pdf',
    file_name: 'fbi_ied_component_metallurgy_report.pdf',
    fileType: 'Document',
    file_type: 'Document',
    source: 'FBI Laboratory, Quantico, VA',
    uploadDate: '2013-04-17T09:00:00Z',
    upload_date: '2013-04-17T09:00:00Z',
    uploadedBy: 'Special Agent in Charge R. DesLauriers',
    uploaded_by: 'Special Agent in Charge R. DesLauriers',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 512000,
    tags: ['Forensics', 'IED Metallurgy', 'Pressure Cooker'],
    extracted_text: 'Fragments recovered from blast zone originate from Fagor 6-quart pressure cooker. Initiator circuit fabricated using hobby model RC receiver.'
  },

  // --- Case 4: Aarushi Talwar Double Murder Case Exhibits ---
  {
    id: 'E-TAL-001',
    caseId: '2',
    case_id: '2',
    fileName: 'cbi_cfsl_blood_spatter_analysis.pdf',
    file_name: 'cbi_cfsl_blood_spatter_analysis.pdf',
    fileType: 'Document',
    file_type: 'Document',
    source: 'CBI Special Crime Unit / CFSL New Delhi',
    uploadDate: '2008-06-02T10:00:00Z',
    upload_date: '2008-06-02T10:00:00Z',
    uploadedBy: 'Joint Director CBI Arun Kumar',
    uploaded_by: 'Joint Director CBI Arun Kumar',
    processingStatus: 'Analyzed',
    processing_status: 'Analyzed',
    file_size: 420000,
    tags: ['CFSL', 'Blood Spatter', 'L-32 Jalvayu Vihar'],
    extracted_text: 'Blood spatter patterns in Aarushi bedroom indicate impact weapon struck victim while asleep. Blood stains on terrace roof match Hemraj Banjade DNA profile.'
  }
];

// ============================================================
// 3. ENTITIES
// ============================================================
export const mockEntities: Entity[] = [
  // Nayana Pujari Entities
  {
    id: 'ENT-NP-01',
    caseId: 'FIR-2009-MH-PUN-534',
    name: 'Yogesh Ashok Raut',
    type: 'Person',
    aliases: ['Prime Accused', 'Cab Driver'],
    sourceEvidenceIds: ['E-NP-002', 'E-NP-003'],
    confidence: 0.99
  },
  {
    id: 'ENT-NP-02',
    caseId: 'FIR-2009-MH-PUN-534',
    name: 'Rajesh Pandurang Chaudhari',
    type: 'Person',
    aliases: ['Accused No. 2', 'Approver / Witness PW-38'],
    sourceEvidenceIds: ['E-NP-001'],
    confidence: 0.95
  },
  {
    id: 'ENT-NP-03',
    caseId: 'FIR-2009-MH-PUN-534',
    name: 'Mahesh Balasaheb Thakur',
    type: 'Person',
    aliases: ['Accused No. 3', 'Accomplice'],
    sourceEvidenceIds: ['E-NP-003'],
    confidence: 0.94
  },
  {
    id: 'ENT-NP-04',
    caseId: 'FIR-2009-MH-PUN-534',
    name: 'Vishwas Hindurao Kadam',
    type: 'Person',
    aliases: ['Accused No. 4', 'Accomplice'],
    sourceEvidenceIds: ['E-NP-003'],
    confidence: 0.92
  },
  {
    id: 'ENT-NP-05',
    caseId: 'FIR-2009-MH-PUN-534',
    name: 'Nayana Abhijit Pujari',
    type: 'Person',
    aliases: ['Victim', 'Synechron Software Engineer'],
    sourceEvidenceIds: ['E-NP-001', 'E-NP-002'],
    confidence: 1.0
  },

  // Cyber Crime Entities
  {
    id: 'ENT-PUN-01',
    caseId: 'FIR-2024-MH-PUN-089',
    name: 'Rohan Deshmukh',
    type: 'Person',
    aliases: ['Lead Systems Administrator', 'Suspect'],
    sourceEvidenceIds: ['E-IND-002', 'E-IND-003'],
    confidence: 0.88
  },
  {
    id: 'ENT-PUN-02',
    caseId: 'FIR-2024-MH-PUN-089',
    name: 'Rajesh Kulkarni',
    type: 'Person',
    aliases: ['Complainant', 'Chief Information Security Officer'],
    sourceEvidenceIds: ['E-IND-001'],
    confidence: 0.95
  },

  // Bengaluru Homicide Entities
  {
    id: 'ENT-BLR-01',
    caseId: 'FIR-2024-KA-BLR-142',
    name: 'Dr. Ananya Rao',
    type: 'Person',
    aliases: ['Victim', 'Senior Surgeon'],
    sourceEvidenceIds: ['E-BLR-001'],
    confidence: 1.0
  },
  {
    id: 'ENT-BLR-02',
    caseId: 'FIR-2024-KA-BLR-142',
    name: 'Suresh Gowda',
    type: 'Person',
    aliases: ['Repeat Offender', 'Convict #4412', 'Prime Suspect'],
    sourceEvidenceIds: ['E-BLR-002'],
    confidence: 0.94
  },

  // Boston Bombing Entities
  {
    id: 'ENT-BOS-01',
    caseId: 'CASE-BOS-2013-001',
    name: 'Dzhokhar Tsarnaev',
    type: 'Person',
    aliases: ['Suspect 2', 'White Hat'],
    sourceEvidenceIds: ['E-BOS-001'],
    confidence: 0.99
  },
  {
    id: 'ENT-BOS-02',
    caseId: 'CASE-BOS-2013-001',
    name: 'Tamerlan Tsarnaev',
    type: 'Person',
    aliases: ['Suspect 1', 'Black Hat'],
    sourceEvidenceIds: ['E-BOS-001', 'E-BOS-002'],
    confidence: 0.99
  },

  // Aarushi Talwar Entities
  {
    id: 'ENT-TAL-01',
    caseId: '2',
    name: 'Aarushi Talwar',
    type: 'Person',
    aliases: ['Victim', 'Daughter (14)'],
    sourceEvidenceIds: ['E-TAL-001'],
    confidence: 1.0
  },
  {
    id: 'ENT-TAL-02',
    caseId: '2',
    name: 'Hemraj Banjade',
    type: 'Person',
    aliases: ['Victim', 'Domestic Aide'],
    sourceEvidenceIds: ['E-TAL-001'],
    confidence: 1.0
  }
];

// ============================================================
// 4. TIMELINE
// ============================================================
export const mockTimeline: TimelineEvent[] = [
  // Nayana Pujari Timeline
  {
    id: 'EVT-NP-01',
    caseId: 'FIR-2009-MH-PUN-534',
    title: 'Victim Boards Qualis Cab at Kharadi Bypass',
    timestamp: '2009-10-07T20:15:00Z',
    description: 'Nayana Pujari leaves Synechron Kharadi office campus and boards Toyoto Qualis cab for commute home.',
    sourceEvidenceId: 'E-NP-001',
    entitiesInvolved: ['ENT-NP-05', 'ENT-NP-01']
  },
  {
    id: 'EVT-NP-02',
    caseId: 'FIR-2009-MH-PUN-534',
    title: 'Forced ATM Cash Withdrawals',
    timestamp: '2009-10-07T22:45:00Z',
    description: 'Accused Yogesh Raut uses victim debit card at SBI ATM Swargate and Hadapsar branch, extorting Rs 61,000.',
    sourceEvidenceId: 'E-NP-002',
    entitiesInvolved: ['ENT-NP-01', 'ENT-NP-05']
  },
  {
    id: 'EVT-NP-03',
    caseId: 'FIR-2009-MH-PUN-534',
    title: 'Abhijit Pujari Registers Missing Report at Yerwada PS',
    timestamp: '2009-10-08T08:30:00Z',
    description: 'Husband Abhijit Pujari registers formal complaint after victim fails to return home and cell phone unreachable.',
    sourceEvidenceId: 'E-NP-001',
    entitiesInvolved: ['ENT-NP-05']
  },

  // Cyber Crime Timeline
  {
    id: 'EVT-PUN-01',
    caseId: 'FIR-2024-MH-PUN-089',
    title: 'Unauthorized SFTP Connection from External IP',
    timestamp: '2024-09-01T02:11:05Z',
    description: 'SSH connection established with credentials of Rohan Deshmukh from IP 185.220.101.5.',
    sourceEvidenceId: 'E-IND-003',
    entitiesInvolved: ['ENT-PUN-01']
  },
  {
    id: 'EVT-PUN-02',
    caseId: 'FIR-2024-MH-PUN-089',
    title: 'Cell Tower Registration at Hinjewadi Datacenter',
    timestamp: '2024-09-01T02:14:22Z',
    description: 'Rohan Deshmukh mobile phone registered at tower HINJ-PH1-4029 concurrent with data extraction.',
    sourceEvidenceId: 'E-IND-002',
    entitiesInvolved: ['ENT-PUN-01']
  },

  // Bengaluru Homicide Timeline
  {
    id: 'EVT-BLR-01',
    caseId: 'FIR-2024-KA-BLR-142',
    title: 'Intruder Breaches 1st Floor Balcony',
    timestamp: '2024-08-14T23:30:00Z',
    description: 'Intruder scales water pipe to access balcony sliding door, leaving latent thumbprints.',
    sourceEvidenceId: 'E-BLR-002',
    entitiesInvolved: ['ENT-BLR-02']
  },
  {
    id: 'EVT-BLR-02',
    caseId: 'FIR-2024-KA-BLR-142',
    title: 'Assault and Robbery Committed',
    timestamp: '2024-08-14T23:45:00Z',
    description: 'Lethal assault committed; gold jewelry and locker contents ransacked.',
    sourceEvidenceId: 'E-BLR-001',
    entitiesInvolved: ['ENT-BLR-01', 'ENT-BLR-02']
  },

  // Boston Bombing Timeline
  {
    id: 'EVT-BOS-01',
    caseId: 'CASE-BOS-2013-001',
    title: 'Detonation of Device 1 & Device 2',
    timestamp: '2013-04-15T14:49:43Z',
    description: 'Two pressure cooker IEDs explode 12 seconds and 210 yards apart near the Boston Marathon finish line.',
    sourceEvidenceId: 'E-BOS-001',
    entitiesInvolved: ['ENT-BOS-01', 'ENT-BOS-02']
  },

  // Aarushi Talwar Timeline
  {
    id: 'EVT-TAL-01',
    caseId: '2',
    title: 'Crime Window at L-32 Jalvayu Vihar',
    timestamp: '2008-05-15T23:00:00Z',
    description: 'Lethal assault occurs in Noida residence; Aarushi found deceased next morning.',
    sourceEvidenceId: 'E-TAL-001',
    entitiesInvolved: ['ENT-TAL-01', 'ENT-TAL-02']
  }
];

// ============================================================
// 5. CONTRADICTIONS
// ============================================================
export const mockContradictions: Contradiction[] = [
  // Nayana Pujari Contradictions
  {
    id: 'CON-NP-01',
    caseId: 'FIR-2009-MH-PUN-534',
    statementA: 'Suspect Yogesh Raut claimed he dropped the victim safely at Katraj chowk and immediately returned home.',
    sourceAId: 'E-NP-001 (Police Interrogation Memo)',
    statementB: 'ATM CCTV records capture Yogesh Raut personally withdrawing Rs 61,000 using victim debit card at Swargate.',
    sourceBId: 'E-NP-002 (SBI ATM Surveillance Video)',
    conflictType: 'Alibi & Financial Contradiction',
    confidence: 0.99,
    status: 'Detected'
  },
  {
    id: 'CON-NP-02',
    caseId: 'FIR-2009-MH-PUN-534',
    statementA: 'Accused Rajesh Chaudhari was initially charged as an active in-car perpetrator of the physical crime.',
    sourceAId: 'Initial Remand Application',
    statementB: 'Synechron security biometric turnstile records prove Chaudhari never left his post at Kharadi campus during the murder window.',
    sourceBId: 'E-NP-007 (Approver Statement & Workplace Logs)',
    conflictType: 'Physical Presence Exoneration',
    confidence: 0.98,
    status: 'Resolved'
  },

  // Cyber Crime Contradiction
  {
    id: 'CON-PUN-01',
    caseId: 'FIR-2024-MH-PUN-089',
    statementA: 'Suspect claimed he was asleep in Kothrud throughout the entire night.',
    sourceAId: 'E-IND-001',
    statementB: 'Cell tower CDR logs place his device at Hinjewadi Phase 1 at 02:14 AM.',
    sourceBId: 'E-IND-002',
    conflictType: 'Alibi Contradiction',
    confidence: 0.98,
    status: 'Detected'
  },

  // Bengaluru Homicide Contradiction
  {
    id: 'CON-BLR-01',
    caseId: 'FIR-2024-KA-BLR-142',
    statementA: 'Suspect Suresh Gowda claimed he was in Tumakuru village throughout August 14-15.',
    sourceAId: 'Police Interrogation Log',
    statementB: 'Latent thumbprint lifted from balcony sliding frame matches Suresh Gowda with 99.4% biometric score.',
    sourceBId: 'E-BLR-002',
    conflictType: 'Forensic Alibi Refutation',
    confidence: 0.99,
    status: 'Detected'
  },

  // Boston Bombing Contradiction
  {
    id: 'CON-BOS-01',
    caseId: 'CASE-BOS-2013-001',
    statementA: 'Defense claimed Dzhokhar Tsarnaev was an unwitting follower with no foreknowledge of explosives.',
    sourceAId: 'Defense Opening Statement',
    statementB: 'Handwritten inscription inside Watertown slipway boat detailed pre-planned operational ideology.',
    sourceBId: 'E-BOS-002',
    conflictType: 'Intent & Prior Knowledge',
    confidence: 0.96,
    status: 'Detected'
  },

  // Aarushi Talwar Contradiction
  {
    id: 'CON-TAL-01',
    caseId: '2',
    statementA: 'Initial police hypothesis that terrace door was locked with key only accessible to parents.',
    sourceAId: 'First SIT Police Briefing',
    statementB: 'CBI forensic team discovered terrace latch had been forcibly tampered with and servant key was duplicate.',
    sourceBId: 'E-TAL-001',
    conflictType: 'Physical Access Discrepancy',
    confidence: 0.89,
    status: 'Detected'
  }
];

// ============================================================
// 6. COMPETING HYPOTHESES (ACH Suspect Elimination)
// ============================================================
export const mockHypotheses: Hypothesis[] = [
  // --- Nayana Pujari Case Hypotheses ---
  {
    id: 'HYP-NP-01',
    caseId: 'FIR-2009-MH-PUN-534',
    title: 'Hypothesis 1: Yogesh Raut (Prime Mastermind & Principal Executioner)',
    description: 'Yogesh Raut planned the abduction, drove the vehicle, extorted the ATM PIN, withdrew cash at multiple ATMs, executed the homicide, and fled custody. (ARRESTED & AWARDED DEATH PENALTY)',
    confidence: 94,
    supportingEvidenceIds: ['E-NP-002', 'E-NP-003'],
    contradictingEvidenceIds: [],
    status: 'Active',
    relatedEntityIds: ['ENT-NP-01']
  },
  {
    id: 'HYP-NP-02',
    caseId: 'FIR-2009-MH-PUN-534',
    title: 'Hypothesis 2: Rajesh Chaudhari (Active Physical In-Car Killer)',
    description: 'Security guard Rajesh Chaudhari physically participated in vehicular assault. (DISPROVEN BY WORKPLACE BIOMETRICS — TURNED APPROVER)',
    confidence: 8,
    supportingEvidenceIds: [],
    contradictingEvidenceIds: ['E-NP-001'],
    status: 'Discarded',
    relatedEntityIds: ['ENT-NP-02']
  },

  // --- Pune Cyber Heist Hypotheses ---
  {
    id: 'HYP-PUN-01',
    caseId: 'FIR-2024-MH-PUN-089',
    title: 'Hypothesis A: Insider Espionage by Systems Administrator (Rohan Deshmukh)',
    description: 'Rohan Deshmukh leveraged valid credentials, VPN tunneling, and an accomplice mule network to steal and monetize proprietary financial code.',
    confidence: 86,
    supportingEvidenceIds: ['E-IND-002', 'E-IND-003'],
    contradictingEvidenceIds: [],
    status: 'Active',
    relatedEntityIds: ['ENT-PUN-01']
  },
  {
    id: 'HYP-PUN-02',
    caseId: 'FIR-2024-MH-PUN-089',
    title: 'Hypothesis B: External Threat Actor / Stolen Token Impersonation',
    description: 'Zero-day remote code execution breached gateway; admin credentials were spoofed by an offshore cybercrime syndicate.',
    confidence: 14,
    supportingEvidenceIds: [],
    contradictingEvidenceIds: ['E-IND-002'],
    status: 'Discarded',
    relatedEntityIds: ['ENT-PUN-01']
  },

  // --- Bengaluru Homicide Hypotheses ---
  {
    id: 'HYP-BLR-01',
    caseId: 'FIR-2024-KA-BLR-142',
    title: 'Hypothesis 1: Targeted Housebreak & Armed Robbery by Suresh Gowda',
    description: 'Repeat offender Suresh Gowda surveyed the residence, forced balcony access, and carried out armed robbery culminating in fatal trauma.',
    confidence: 91,
    supportingEvidenceIds: ['E-BLR-001', 'E-BLR-002'],
    contradictingEvidenceIds: [],
    status: 'Active',
    relatedEntityIds: ['ENT-BLR-02']
  },

  // --- Boston Bombing Hypotheses ---
  {
    id: 'HYP-BOS-01',
    caseId: 'CASE-BOS-2013-001',
    title: 'Hypothesis 1: Self-Radicalized Autonomous Cell (Tsarnaev Brothers)',
    description: 'Dzhokhar and Tamerlan Tsarnaev constructed and deployed dual pressure-cooker IEDs autonomously without foreign battlefield direction.',
    confidence: 89,
    supportingEvidenceIds: ['E-BOS-001', 'E-BOS-002'],
    contradictingEvidenceIds: [],
    status: 'Active',
    relatedEntityIds: ['ENT-BOS-01', 'ENT-BOS-02']
  },

  // --- Aarushi Talwar Hypotheses ---
  {
    id: 'HYP-TAL-01',
    caseId: '2',
    title: 'Hypothesis 1: Outside Intrusion & Assault by Domestic Servants',
    description: 'External aides gained access to the premises during the night; subsequent investigation revealed conflicting forensic evidence.',
    confidence: 65,
    supportingEvidenceIds: ['E-TAL-001'],
    contradictingEvidenceIds: [],
    status: 'Active',
    relatedEntityIds: ['ENT-TAL-01', 'ENT-TAL-02']
  }
];

// ============================================================
// 7. INVESTIGATION TASKS
// ============================================================
export const mockInvestigationTasks: InvestigationTask[] = [
  // Nayana Pujari Tasks
  {
    id: 'TSK-NP-01',
    caseId: 'FIR-2009-MH-PUN-534',
    task: 'Subpoena State Bank ATM CCTV Tapes from Swargate & Hadapsar',
    reason: 'Identify physical face of person withdrawing cash with victim card',
    relatedEvidenceId: 'E-NP-002',
    status: 'Completed',
    priority: 'High',
    assignedTo: 'ACP Vinod Satav'
  },
  {
    id: 'TSK-NP-02',
    caseId: 'FIR-2009-MH-PUN-534',
    task: 'Send Qualis Blood & STR Swabs to FSL Kalina',
    reason: 'Confirm biological presence of suspects inside murder vehicle',
    relatedEvidenceId: 'E-NP-003',
    status: 'Completed',
    priority: 'High',
    assignedTo: 'PI Kishor Mhaswade'
  },

  // Cyber Crime Tasks
  {
    id: 'TSK-PUN-01',
    caseId: 'FIR-2024-MH-PUN-089',
    task: 'Subpoena ISP Gateway Logs for External IP 185.220.101.5',
    reason: 'Determine origin ISP and exit node for exfiltration tunnel',
    relatedEvidenceId: 'E-IND-003',
    status: 'In Progress',
    priority: 'High',
    assignedTo: 'PI Vikram Salunkhe'
  },

  // Bengaluru Tasks
  {
    id: 'TSK-BLR-01',
    caseId: 'FIR-2024-KA-BLR-142',
    task: 'Check Commercial Street Pawn Shops for Stolen Jewelry',
    reason: 'Recover physical stolen gold matching victim inventory',
    relatedEvidenceId: 'E-BLR-002',
    status: 'In Progress',
    priority: 'High',
    assignedTo: 'Insp. B. Manjunath'
  },

  // Boston Tasks
  {
    id: 'TSK-BOS-01',
    caseId: 'CASE-BOS-2013-001',
    task: 'Trace Pressure Cooker Retail SKUs Across New England',
    reason: 'Identify purchase point and transaction timestamp',
    relatedEvidenceId: 'E-BOS-002',
    status: 'Completed',
    priority: 'High',
    assignedTo: 'FBI Task Force'
  },

  // Aarushi Talwar Tasks
  {
    id: 'TSK-TAL-01',
    caseId: '2',
    task: 'Review CFSL Touch DNA Reports for Dining Room Exhibits',
    reason: 'Verify forensic chain of custody and DNA sample purity',
    relatedEvidenceId: 'E-TAL-001',
    status: 'Completed',
    priority: 'High',
    assignedTo: 'CBI Special Crime Unit'
  }
];

// ============================================================
// 8. GEO CASES
// ============================================================
export const mockGeoCases: GeoCase[] = [
  {
    id: 'FIR-2009-MH-PUN-534',
    title: 'Pune Techie Nayana Pujari Case',
    crimeType: 'Murder',
    location: 'Kharadi / Zarewadi Forest, Pune',
    latitude: 18.5529,
    longitude: 73.9352,
    severity: 'Critical',
    status: 'Closed',
    evidenceCount: 10,
    suspectCount: 4,
    witnessCount: 38
  },
  {
    id: 'FIR-2024-MH-PUN-089',
    title: 'Pune Cyber Heist & Data Exfiltration',
    crimeType: 'Cybercrime',
    location: 'Hinjewadi Tech Park, Pune',
    latitude: 18.5913,
    longitude: 73.7389,
    severity: 'High',
    status: 'Active',
    evidenceCount: 3,
    suspectCount: 2,
    witnessCount: 5
  },
  {
    id: 'FIR-2024-KA-BLR-142',
    title: 'Indiranagar Homicide & Armed Robbery',
    crimeType: 'Murder',
    location: 'Indiranagar 100ft Road, Bengaluru',
    latitude: 12.9784,
    longitude: 77.6408,
    severity: 'High',
    status: 'Investigating',
    evidenceCount: 3,
    suspectCount: 1,
    witnessCount: 4
  },
  {
    id: 'CASE-BOS-2013-001',
    title: 'Boston Marathon Bombing',
    crimeType: 'Other',
    location: 'Boylston Street, Boston, MA',
    latitude: 42.3496,
    longitude: -71.0825,
    severity: 'Critical',
    status: 'Closed',
    evidenceCount: 3,
    suspectCount: 2,
    witnessCount: 120
  },
  {
    id: '2',
    title: 'Aarushi Talwar Double Murder Case',
    crimeType: 'Murder',
    location: 'Jalvayu Vihar Sector 25, Noida',
    latitude: 28.5823,
    longitude: 77.3468,
    severity: 'High',
    status: 'Active',
    evidenceCount: 1,
    suspectCount: 3,
    witnessCount: 15
  }
];
