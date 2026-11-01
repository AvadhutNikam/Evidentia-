# backend/routers/legal_glossary.py
"""
Evidentia-AI Legal Glossary & Terminology Router
Manages statutory and forensic definitions across English, Hindi, and Marathi.
Used for tooltips, AI prompt constraints, and omni-search synonym expansion.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import User, LegalTerm
from schemas import LegalTermOut, LegalTermCreate, LegalTermUpdate
from auth import get_current_user

router = APIRouter(prefix="/legal-terms", tags=["legal-glossary"])


SEED_TERMS = [
    {
        "term_en": "Panchanama",
        "term_hi": "पंचनामा",
        "term_mr": "पंचनामा",
        "plain_explanation_en": "Contemporaneous record of what police officers find and seize, witnessed and verified by two respectable local citizens (panchas).",
        "plain_explanation_hi": "घटनास्थल पर पुलिस द्वारा की गई कार्रवाई और बरामदगी का दो स्वतंत्र गवाहों (पंचों) के समक्ष तैयार किया गया आधिकारिक विवरण।",
        "plain_explanation_mr": "गुन्ह्याच्या ठिकाणी किंवा जप्तीवेळी दोन निष्पक्ष पंचांसमक्ष पोलीस अधिकाऱ्यांनी केलेल्या प्रत्यक्ष कारवाईचा समकालीन अधिकृत दस्तऐवज.",
        "legal_provision_new": "Section 185 BNSS",
        "legal_provision_old": "Section 100 CrPC",
        "category": "panchanama"
    },
    {
        "term_en": "Police Examination Statement",
        "term_hi": "पुलिस बयान",
        "term_mr": "पोलीस जबाब",
        "plain_explanation_en": "Record of witness examination conducted by an investigating officer during investigation. Unsigned and cannot be used as substantive trial evidence except for contradiction.",
        "plain_explanation_hi": "जांच के दौरान पुलिस अधिकारी द्वारा दर्ज गवाह का बयान। यह केवल विरोधाभास साबित करने हेतु उपयोगी है, मुख्य साक्ष्य नहीं।",
        "plain_explanation_mr": "तपास अधिकाऱ्याने घेतलेला साक्षीदाराचा जबाब. यावर सही घेतली जात नाही व हा केवळ कोर्टात विरोधाभास दाखवण्यासाठी वापरला जातो.",
        "legal_provision_new": "Section 180 BNSS",
        "legal_provision_old": "Section 161 CrPC",
        "category": "statement"
    },
    {
        "term_en": "Magistrate Statement under Oath",
        "term_hi": "मजिस्ट्रेट के समक्ष बयान / संस्वीकृति",
        "term_mr": "मॅजिस्ट्रेटसमोर नोंदवलेला जबाब / कबुली",
        "plain_explanation_en": "Confession or statement recorded under oath before a Judicial or Metropolitan Magistrate. Admissible as direct substantive evidence in court.",
        "plain_explanation_hi": "न्यायिक मजिस्ट्रेट के समक्ष शपथ पर दिया गया बयान या इकबाल-ए-जुर्म, जो अदालत में मूल साक्ष्य के रूप में स्वीकार्य है।",
        "plain_explanation_mr": "न्यायदंडाधिकाऱ्यांसमोर शपथेवर दिलेला जबाब किंवा कबुलीजबाब, जो न्यायालयात प्रत्यक्ष पुरावा म्हणून ग्राह्य धरला जातो.",
        "legal_provision_new": "Section 183 BNSS",
        "legal_provision_old": "Section 164 CrPC",
        "category": "statement"
    },
    {
        "term_en": "Electronic Record Certificate",
        "term_hi": "इलेक्ट्रॉनिक साक्ष्य प्रमाणपत्र",
        "term_mr": "इलेक्ट्रॉनिक पुरावा प्रमाणपत्र",
        "plain_explanation_en": "Mandatory authentication certificate certifying lawful computer operation and device custody for electronic evidence (CCTV, CDR, WhatsApp, emails).",
        "plain_explanation_hi": "डिजिटल साक्ष्य (सीसीटीवी, सीडीआर, व्हाट्सएप) को अदालत में वैध ठहराने के लिए आवश्यक वैधानिक तकनीकी प्रमाणपत्र।",
        "plain_explanation_mr": "डिजिटल व इलेक्ट्रॉनिक पुरावे (सीसीटीव्ही, सीडीआर, व्हॉट्सअ‍ॅप) कोर्टात ग्राह्य ठरवण्यासाठी उपकरणाच्या ताबेदाराने दिलेले अनिवार्य प्रमाणपत्र.",
        "legal_provision_new": "Section 63 BSA",
        "legal_provision_old": "Section 65B IEA",
        "category": "cyber"
    },
    {
        "term_en": "Discovery / Disclosure Statement",
        "term_hi": "बरामदगी / प्रकटीकरण मेमो",
        "term_mr": "कबुलीजबाब / शोध मेमो",
        "plain_explanation_en": "Information provided by an accused in custody leading directly to the recovery of a weapon, body, or stolen object, admissible to the extent of discovery.",
        "plain_explanation_hi": "हिरासत में आरोपी द्वारा दी गई वह जानकारी जिसके आधार पर हथियार, शव या चोरी की संपत्ति बरामद होती है।",
        "plain_explanation_mr": "ताब्यात असलेल्या आरोपीने दिलेल्या माहितीवरून हत्यार, मृतदेह किंवा मालमत्ता प्रत्यक्ष हस्तगत झाल्याचा पंचनामा.",
        "legal_provision_new": "Section 23 BSA",
        "legal_provision_old": "Section 27 IEA",
        "category": "forensic"
    },
    {
        "term_en": "Default / Statutory Bail",
        "term_hi": "डिफ़ॉल्ट / वैधानिक जमानत",
        "term_mr": "वैधानिक जामीन (डिफॉल्ट बेल)",
        "plain_explanation_en": "Indefeasible statutory right of the accused to release on bail if police fail to file a chargesheet within 60 or 90 days of detention.",
        "plain_explanation_hi": "यदि पुलिस 60 या 90 दिनों में आरोप पत्र दाखिल नहीं करती है, तो आरोपी को मिलने वाला स्वतः जमानत का अचूक अधिकार।",
        "plain_explanation_mr": "पोलिसांनी ६० किंवा ९० दिवसांत दोषारोपपत्र दाखल न केल्यास आरोपीला मिळणारा कायद्यानुसार अनिर्बंध जामिनाचा हक्क.",
        "legal_provision_new": "Section 187(3) BNSS",
        "legal_provision_old": "Section 167(2) CrPC",
        "category": "arrest_remand"
    },
    {
        "term_en": "Chargesheet / Police Final Report",
        "term_hi": "आरोप पत्र / चालान",
        "term_mr": "दोषारोपपत्र / अंतिम अहवाल",
        "plain_explanation_en": "Official comprehensive police report submitted to magistrate stating completion of investigation, evidence collected, and specific charges against accused.",
        "plain_explanation_hi": "जांच पूरी होने पर मजिस्ट्रेट को प्रस्तुत की जाने वाली अंतिम रिपोर्ट, जिसमें गवाहों, साक्ष्यों और आरोपों का विवरण होता है।",
        "plain_explanation_mr": "तपास पूर्ण झाल्यावर गुन्ह्यातील साक्षीदार, पुरावे व लावलेली कलमे यांसह न्यायालयात सादर केले जाणारे अंतिम आरोपपत्र.",
        "legal_provision_new": "Section 193 BNSS",
        "legal_provision_old": "Section 173 CrPC",
        "category": "arrest_remand"
    }
]


def ensure_glossary_seeded(db: Session) -> None:
    """Seeds foundational legal terms if table is empty."""
    if db.query(LegalTerm).count() >= len(SEED_TERMS):
        return

    for t in SEED_TERMS:
        existing = db.query(LegalTerm).filter(LegalTerm.term_en == t["term_en"]).first()
        if not existing:
            row = LegalTerm(
                term_en=t["term_en"],
                term_hi=t["term_hi"],
                term_mr=t["term_mr"],
                plain_explanation_en=t["plain_explanation_en"],
                plain_explanation_hi=t["plain_explanation_hi"],
                plain_explanation_mr=t["plain_explanation_mr"],
                legal_provision_new=t["legal_provision_new"],
                legal_provision_old=t["legal_provision_old"],
                category=t["category"],
                is_verified=True,
                verified_by="Special Legal Advisor",
                version=1
            )
            db.add(row)
    db.commit()


@router.get("", response_model=List[LegalTermOut])
def list_legal_terms(
    q: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists legal glossary terms with optional keyword search across English, Hindi, and Marathi."""
    ensure_glossary_seeded(db)
    query = db.query(LegalTerm)

    if category:
        query = query.filter(LegalTerm.category == category)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                LegalTerm.term_en.ilike(search_pattern),
                LegalTerm.term_hi.ilike(search_pattern),
                LegalTerm.term_mr.ilike(search_pattern),
                LegalTerm.plain_explanation_en.ilike(search_pattern),
                LegalTerm.legal_provision_new.ilike(search_pattern),
                LegalTerm.legal_provision_old.ilike(search_pattern)
            )
        )

    return query.order_by(LegalTerm.term_en.asc()).all()


@router.get("/lookup/{keyword}", response_model=Optional[LegalTermOut])
def lookup_term_tooltip(
    keyword: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rapid tooltip lookup for statutory terms in panchanama, statements, or section references."""
    ensure_glossary_seeded(db)
    kw = keyword.strip()
    term = db.query(LegalTerm).filter(
        or_(
            LegalTerm.term_en.ilike(kw),
            LegalTerm.term_hi == kw,
            LegalTerm.term_mr == kw,
            LegalTerm.legal_provision_new.ilike(f"%{kw}%"),
            LegalTerm.legal_provision_old.ilike(f"%{kw}%")
        )
    ).first()

    return term


@router.post("", response_model=LegalTermOut)
def create_legal_term(
    req: LegalTermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new verified legal term."""
    term = LegalTerm(
        term_en=req.term_en,
        term_hi=req.term_hi,
        term_mr=req.term_mr,
        plain_explanation_en=req.plain_explanation_en,
        plain_explanation_hi=req.plain_explanation_hi,
        plain_explanation_mr=req.plain_explanation_mr,
        legal_provision_new=req.legal_provision_new,
        legal_provision_old=req.legal_provision_old,
        category=req.category,
        is_verified=req.is_verified,
        verified_by=current_user.full_name,
        version=1
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term

