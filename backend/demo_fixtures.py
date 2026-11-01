"""
================================================================================
EVIDENTIA-AI DEMO FIXTURES
================================================================================
Isolated pre-written forensic exhibit dossiers used strictly for demonstration cases.
Real uploads and non-demo cases must NEVER use these fixtures and must always go
through the live extraction pipeline.
"""

from pathlib import Path
from typing import Dict, Any, Optional

DEMO_EXHIBIT_DOSSIERS: Dict[str, Dict[str, Any]] = {
    "sample_atm_cctv.mp4": {
        "title": "Yerwada SBI ATM CCTV Footage (21:42:15 IST)",
        "type": "Digital Video Surveillance (CCTV)",
        "legal": "Prosecution Exhibit No. 24 • Sec 65B(4) Indian Evidence Act / Sec 63 BSA 2023",
        "transcript": (
            "Yerwada SBI ATM surveillance camera 02 recorded on 07-Oct-2009 at 21:42:15 IST. "
            "Two adult males observed entering the ATM vestibule using victim Nayana Pujari's SBI debit card. "
            "Accused Yogesh Ashok Raut is clearly observed at the ATM keypad withdrawing Rs 61,000 across three consecutive transactions. "
            "Accomplice Rajesh Chaudhari is seen waiting outside the glass door in the getaway vehicle, a silver Toyota Qualis bearing registration MH-12-AR-2541. "
            "Facial recognition and apparel match subsequent arrest seizures."
        ),
        "entities": [
            {"name": "Yogesh Ashok Raut", "type": "PERSON", "confidence": 0.98, "role": "Prime Accused (Withdrawal Actor)"},
            {"name": "Rajesh Chaudhari", "type": "PERSON", "confidence": 0.94, "role": "Accomplice / Approver"},
            {"name": "Nayana Pujari", "type": "PERSON", "confidence": 0.99, "role": "Victim"},
            {"name": "Yerwada SBI ATM", "type": "LOCATION", "confidence": 0.96, "role": "Crime Scene (Withdrawal)"},
            {"name": "Toyota Qualis (MH-12-AR-2541)", "type": "VEHICLE", "confidence": 0.97, "role": "Crime Cab"}
        ],
        "events": [
            {
                "title": "Nayana Pujari Debit Card Fraudulent Withdrawal",
                "description": "Yogesh Raut and Rajesh Chaudhari withdraw Rs 61,000 from victim's account at Yerwada SBI ATM.",
                "timestamp": "2009-10-07T21:42:15",
                "location": "Yerwada SBI ATM",
                "confidence": 0.97
            }
        ]
    },
    "sample_cdr_dump.pdf": {
        "title": "Call Detail Records & Kharadi Cell Tower Triangulation Dump",
        "type": "Telecommunications Forensic Dump",
        "legal": "Prosecution Exhibit No. 37 • Sec 65B Indian Evidence Act Nodal Certificate",
        "transcript": (
            "Idea & Vodafone Cellular Tower Dump for Kharadi Bypass sector (Cell ID 404-20-1102). "
            "Between 20:30 and 22:15 IST on 07-Oct-2009, three mobile IMEIs co-located under the same cell tower antenna sector: "
            "IMEI 35489002148102 (registered to Yogesh Ashok Raut), IMEI 35910293481230 (registered to Mahesh Thakur), and victim Nayana Pujari's cellular handset. "
            "Outbound call made at 21:05 IST from suspect handset to co-accused Vishwas Kadam. "
            "Cell tower handover route tracks eastward movement along Pune-Ahmednagar Highway towards Rajgurunagar."
        ),
        "entities": [
            {"name": "Yogesh Ashok Raut", "type": "PERSON", "confidence": 0.97, "role": "Prime Accused Handset User"},
            {"name": "Mahesh Thakur", "type": "PERSON", "confidence": 0.95, "role": "Co-Accused"},
            {"name": "Vishwas Kadam", "type": "PERSON", "confidence": 0.93, "role": "Co-Accused"},
            {"name": "Nayana Pujari", "type": "PERSON", "confidence": 0.99, "role": "Victim"},
            {"name": "Kharadi Bypass", "type": "LOCATION", "confidence": 0.98, "role": "Abduction Scene"},
            {"name": "Rajgurunagar", "type": "LOCATION", "confidence": 0.92, "role": "Secondary Scene"}
        ],
        "events": [
            {
                "title": "Cellular Tower Co-location at Kharadi Bypass",
                "description": "Suspect handsets and victim phone co-locate under Kharadi cell tower 404-20-1102 between 20:30 and 22:15 IST.",
                "timestamp": "2009-10-07T20:30:00",
                "location": "Kharadi Bypass, Pune",
                "confidence": 0.96
            }
        ]
    },
    "qualis_forensics.pdf": {
        "title": "Forensic Science Laboratory (FSL) Biological Examination - Toyota Qualis",
        "type": "Forensic Biological & Trace Report",
        "legal": "Prosecution Exhibit No. 49 • Sec 45 Indian Evidence Act (Forensic Expert)",
        "transcript": (
            "Forensic Science Laboratory (FSL) Kalina inspection of vehicle Toyota Qualis MH-12-AR-2541. "
            "Luminol test revealed positive latent bloodstains on the rear middle seat foam and driver-side floor matting. "
            "Serological test confirms human blood group O Positive matching victim Nayana Pujari. "
            "DNA STR multiplex analysis matched blood stains to reference blood sample of victim with 99.999% certainty. "
            "Hair follicles recovered from front passenger headrest match suspect Yogesh Ashok Raut."
        ),
        "entities": [
            {"name": "Nayana Pujari", "type": "PERSON", "confidence": 0.99, "role": "Victim (DNA Match)"},
            {"name": "Yogesh Ashok Raut", "type": "PERSON", "confidence": 0.96, "role": "Suspect (Hair Trace)"},
            {"name": "Toyota Qualis (MH-12-AR-2541)", "type": "VEHICLE", "confidence": 0.99, "role": "Crime Vehicle"},
            {"name": "FSL Kalina, Mumbai", "type": "ORGANIZATION", "confidence": 0.95, "role": "Forensic Laboratory"}
        ],
        "events": [
            {
                "title": "FSL DNA Blood Trace Match in Qualis Cab",
                "description": "FSL Kalina isolates victim Nayana Pujari DNA from bloodstains inside Toyota Qualis MH-12-AR-2541.",
                "timestamp": "2009-10-18T11:00:00",
                "location": "FSL Kalina, Mumbai",
                "confidence": 0.99
            }
        ]
    },
    "approver_confession.pdf": {
        "title": "Judicial Confession of Approver Rajesh Chaudhari under Section 164 CrPC",
        "type": "Judicial Statement & Confession",
        "legal": "Prosecution Exhibit No. 12 • Sec 164 CrPC & Sec 306/308 CrPC",
        "transcript": (
            "Statement recorded by Judicial Magistrate First Class (JMFC) Pune under Section 164 CrPC. "
            "Approver Rajesh Chaudhari confessed under oath: Yogesh Raut was driving the silver Toyota Qualis on 07-Oct-2009. "
            "At 20:15 IST, they spotted Nayana Pujari waiting for transport near Synechron / EON IT Park Kharadi bypass. "
            "They offered her a shared cab lift. Inside the vehicle, Mahesh Thakur, Vishwas Kadam, and Yogesh Raut restrained her. "
            "They drove to an isolated spot in Zarewadi forest, assaulted and murdered the victim, and disposed of the body."
        ),
        "entities": [
            {"name": "Rajesh Chaudhari", "type": "PERSON", "confidence": 0.99, "role": "Approver / Confessor"},
            {"name": "Yogesh Ashok Raut", "type": "PERSON", "confidence": 0.98, "role": "Prime Conspirator"},
            {"name": "Mahesh Thakur", "type": "PERSON", "confidence": 0.96, "role": "Co-Accused"},
            {"name": "Vishwas Kadam", "type": "PERSON", "confidence": 0.95, "role": "Co-Accused"},
            {"name": "Nayana Pujari", "type": "PERSON", "confidence": 0.99, "role": "Victim"},
            {"name": "Zarewadi Forest, Khed", "type": "LOCATION", "confidence": 0.97, "role": "Murder Scene"},
            {"name": "JMFC Court Pune", "type": "ORGANIZATION", "confidence": 0.94, "role": "Judicial Authority"}
        ],
        "events": [
            {
                "title": "Approver Judicial Confession Recorded",
                "description": "Rajesh Chaudhari confesses complete conspiracy and timeline of Nayana Pujari abduction and murder before JMFC.",
                "timestamp": "2009-11-04T14:30:00",
                "location": "JMFC Court, Pune",
                "confidence": 0.98
            }
        ]
    }
}


def get_demo_fixture(file_name: str) -> Optional[Dict[str, Any]]:
    """
    Lookup pre-written demo exhibit dossier by filename.
    Only called if the case is explicitly tagged as demo.
    Returns None if no matching demo fixture exists.
    """
    if not file_name:
        return None
    base = Path(file_name).name.lower()
    for key, dossier in DEMO_EXHIBIT_DOSSIERS.items():
        if key.lower() in base or base in key.lower():
            return dossier
    return None

