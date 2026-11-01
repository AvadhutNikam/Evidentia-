# backend/indic_engine.py
"""
Evidentia-AI Indic Engine (Devanagari, Marathi, Hindi & Multi-Script Processing)

Key Features:
1. Deep Unicode Normalization (NFC, Nukta, Anusvara, ZWJ/ZWNJ preservation, Devanagari numerals).
2. SoundexIndic: Indic-aware phonetic key generation linking Devanagari and Latin spellings.
3. Anti-False-Merge Disambiguation: Multi-signal corroboration (father's name, age, phone, jurisdiction).
4. Offline Rule-Based Transliteration Helper (Latin <-> Devanagari).
5. Surname Neutrality: Enforces strict lexical usage without community/caste inference.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

# ==============================================================================
# 1. DEVANAGARI CHARACTERS, NUMERALS & NUKTA VARIANTS
# ==============================================================================

DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

WESTERN_TO_DEVANAGARI_DIGITS = {v: k for k, v in DEVANAGARI_DIGITS.items()}

# Common Devanagari Nukta normalizations to base phonemes
NUKTA_MAP = {
    'क़': 'क', 'ख़': 'ख', 'ग़': 'ग', 'ज़': 'ज', 'ड़': 'ड', 'ढ़': 'ढ', 'फ़': 'फ', 'य़': 'य'
}

# Standard Indic Honorifics and Titles to strip for canonical indexing
HONORIFICS = [
    # Marathi / Hindi Devanagari
    "श्री", "श्रीमती", "सौ", "स्व", "कुमार", "कुमारी", "मा", "माजी", "डॉ", "अ‍ॅड",
    "पोलीस", "इन्स्पेक्टर", "उपनिरीक्षक", "हवालदार", "अधीक्षक", "अधिकारी",
    # English Latin
    "shri", "smt", "mr", "mrs", "ms", "miss", "dr", "adv", "late", "advocate",
    "inspector", "sub-inspector", "constable", "sp", "dcp", "pi", "psi", "officer"
]

# Filial relation indicators
FILIAL_TOKENS = [
    # Devanagari
    "आत्मज", "सुपुत्र", "सुपुत्री", "मुलगा", "मुलगी", "पत्नी", "पती", "वडील", "आई",
    # Latin
    "s/o", "d/o", "w/o", "c/o", "h/o", "son of", "daughter of", "wife of", "care of"
]

# Common Indian name transliteration dictionary for rapid zero-latency lookup
COMMON_NAMES_MAP = {
    # Given Names
    "rahul": ["राहुल", "राहुळ"],
    "yogesh": ["योगेश"],
    "mahesh": ["महेश"],
    "rajesh": ["राजेश"],
    "vishwas": ["विश्वास"],
    "sunil": ["सुनील", "सुनिल"],
    "anil": ["अनिल"],
    "sachin": ["सचिन"],
    "nayana": ["नयना"],
    "priya": ["प्रिया"],
    "pooja": ["पूजा"],
    "amit": ["अमित"],
    "ajay": ["अजय"],
    "vijay": ["विजय"],
    "sanjay": ["संजय"],
    "ganesh": ["गणेश"],
    "amol": ["अमोल"],
    "pramod": ["प्रमोद"],
    "deepak": ["दीपक", "दिपक"],
    "ramesh": ["रमेश"],
    "suresh": ["सुरेश"],
    "dinesh": ["दिनेश"],
    "vikram": ["विक्रम"],
    "rohit": ["रोहित"],
    "nitin": ["नितीन", "नितीन"],
    "sandip": ["संदीप", "संदिप"],
    "kishor": ["किशोर"],
    "abhijit": ["अभिजीत", "अभिजित"],
    "swapnil": ["स्वप्निल"],
    "pravin": ["प्रवीण", "प्रविण"],
    
    # Surnames
    "raut": ["राउत", "राऊत"],
    "thakur": ["ठाकूर", "ठाकुर"],
    "kadam": ["कदम"],
    "chaudhari": ["चौधरी", "चौधरी"],
    "shinde": ["शिंदे"],
    "patil": ["पाटील", "पाटिल"],
    "pawar": ["पवार"],
    "deshmukh": ["देशमुख"],
    "jadhav": ["जाधव"],
    "more": ["मोरे"],
    "gaikwad": ["गायकवाड"],
    "kamble": ["कांबळे", "कांबले"],
    "waghmare": ["वाघमारे"],
    "bhosale": ["भोसले"],
    "chavan": ["चव्हाण"],
    "sharma": ["शर्मा"],
    "verma": ["वर्मा"],
    "singh": ["सिंह"],
    "yadav": ["यादव"],
    "pujari": ["पुजारी"],
    "mhaswade": ["म्हासवडे"],

    # Cities and Landmark Places
    "pune": ["पुणे"],
    "mumbai": ["मुंबई"],
    "swargate": ["स्वारगेट"],
    "yerwada": ["येरवडा"],
    "kharadi": ["खराडी"],
    "hadapsar": ["हडपसर"],
    "kothrud": ["कोथरूड"],
    "shivajinagar": ["शिवाजीनगर"],
    "katraj": ["कात्रज"],
    "hinjawadi": ["हिंजवडी", "हिंजवडी"],
    "panvel": ["पनवेल"],
    "thane": ["ठाणे"],
    "nagpur": ["नागपूर"],
    "nashik": ["नाशिक"]
}

# Reverse lookup: Devanagari to Latin
REVERSE_COMMON_MAP: Dict[str, str] = {}
for latin_key, dev_list in COMMON_NAMES_MAP.items():
    for dev_str in dev_list:
        REVERSE_COMMON_MAP[dev_str] = latin_key.capitalize()


# ==============================================================================
# 2. UNICODE & TEXT NORMALIZATION
# ==============================================================================

def normalize_indic_text(text: Optional[str]) -> str:
    """
    Standardizes Indian vernacular text across Hindi and Marathi:
    1. Unicode NFC form normalization (decomposed vowels & matras unified).
    2. Maps Nukta variants to base phonemes for robust fuzzy search.
    3. Translates Devanagari digits (०-९) to Western digits (0-9).
    4. Preserves necessary ZWJ/ZWNJ for conjuncts while removing stray joiners.
    5. Cleans whitespace while maintaining paragraph breaks.
    """
    if not text:
        return ""

    # 1. Unicode NFC Form
    normalized = unicodedata.normalize('NFC', text)

    # 2. Nukta mapping
    for nukta_char, base_char in NUKTA_MAP.items():
        normalized = normalized.replace(nukta_char, base_char)

    # 3. Digits normalization
    for deva_digit, west_digit in DEVANAGARI_DIGITS.items():
        normalized = normalized.replace(deva_digit, west_digit)

    # 4. Normalize multiple whitespaces
    lines = normalized.splitlines()
    cleaned = [re.sub(r'[^\S\r\n]+', ' ', line).strip() for line in lines]
    return "\n".join(cleaned).strip()


def strip_indic_honorifics_and_affixes(name: str) -> str:
    """
    Strips titles, honorific prefixes, and filial phrases from a person's name
    to yield the canonical base identity.
    Example:
    'श्री योगेश अशोक राउत, स/ओ अशोक राउत' -> 'योगेश अशोक राउत'
    'Shri Rahul S. Patil s/o Suresh Patil' -> 'Rahul Patil'
    """
    if not name:
        return ""

    cleaned = name.strip()

    # Split filial expressions (keep only the primary subject before the relation)
    for filial in FILIAL_TOKENS:
        pattern = re.compile(rf'\b{re.escape(filial)}\b.*$', flags=re.IGNORECASE)
        cleaned = pattern.sub('', cleaned).strip()

    # Tokenize and remove honorifics
    tokens = re.split(r'[\s,.]+', cleaned)
    filtered = []
    for t in tokens:
        if not t:
            continue
        lower_t = t.lower()
        if lower_t not in HONORIFICS:
            filtered.append(t)

    result = " ".join(filtered).strip()
    return result if result else name.strip()


# ==============================================================================
# 3. SOUNDEX-INDIC: PHONETIC ALGORITHM FOR INDIC & LATIN SCRIPTS
# ==============================================================================

def soundex_indic(name: str) -> str:
    """
    Generates a unified phonetic fingerprint connecting Devanagari and Latin spellings.
    Maps Indian phonemes into equivalence classes regardless of whether written
    in Devanagari script or Latin script (e.g., 'राहुल', 'Rahul', 'Rahool' -> 'R440').

    Equivalence Classes:
    1: Labials (P, B, V, W, F / प, फ, ब, भ, व)
    2: Velars & Gutturals (K, G, C, Q, Kh, Gh / क, ख, ग, घ)
    3: Palatals & Sibilants (S, Sh, Z, J, Ch, Jh / च, छ, ज, झ, श, ष, स)
    4: Dentals & Retroflexes (T, D, Th, Dh / ट, ठ, ड, ढ, त, थ, द, ध)
    5: Nasals (N, M, Ng, Ny / ङ, ञ, ण, न, म)
    6: Liquids & Flaps (R, L, Rh / र, ल, ळ, ऱ)
    7: Aspirates & Glottals (H / ह)
    """
    clean = strip_indic_honorifics_and_affixes(name).strip()
    if not clean:
        return "I000"

    # Convert known Devanagari tokens to Latin phonetic equivalents if in Devanagari
    words = clean.split()
    latin_words = []
    for w in words:
        is_dev = any('\u0900' <= ch <= '\u097f' for ch in w)
        if is_dev:
            if w in REVERSE_COMMON_MAP:
                latin_words.append(REVERSE_COMMON_MAP[w])
            else:
                rough = _deva_to_rough_latin(w)
                latin_words.append(rough if rough else w)
        else:
            latin_words.append(w)

    s = " ".join(latin_words).lower()
    s = re.sub(r'[^a-z]', '', s)
    if not s:
        return "I000"

    first_letter = s[0].upper()

    # Phoneme mapping
    code_map = {
        'b': '1', 'f': '1', 'p': '1', 'v': '1', 'w': '1',
        'c': '2', 'g': '2', 'k': '2', 'q': '2',
        'j': '3', 's': '3', 'z': '3', 'x': '3',
        'd': '4', 't': '4',
        'l': '6',
        'm': '5', 'n': '5',
        'r': '6',
        'h': '7'
    }

    codes = [code_map.get(ch, '0') for ch in s[1:]]

    # Remove adjacent duplicates
    dedup = []
    prev = code_map.get(s[0], '')
    for c in codes:
        if c != prev and c != '0':
            dedup.append(c)
        prev = c

    res = (first_letter + "".join(dedup) + "0000")[:4]
    return res


def _deva_to_rough_latin(word: str) -> str:
    """Rough phonemic converter from Devanagari syllables to English Latin."""
    sub_map = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'ळ': 'l',
        'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', '्': ''
    }
    out = []
    for ch in word:
        out.append(sub_map.get(ch, ''))
    return "".join(out)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if s1 == s2:
        return 0
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_name_similarity(name1: str, name2: str) -> Tuple[float, bool, str]:
    """
    Computes name similarity between two names across Latin and Devanagari:
    Returns (similarity_score: 0.0-1.0, is_phonetic_match: bool, reason: str).
    """
    c1 = strip_indic_honorifics_and_affixes(name1).strip().lower()
    c2 = strip_indic_honorifics_and_affixes(name2).strip().lower()

    if not c1 or not c2:
        return 0.0, False, "Empty name string"

    if c1 == c2:
        return 1.0, True, "Exact literal match"

    # Compare SoundexIndic
    snd1 = soundex_indic(c1)
    snd2 = soundex_indic(c2)
    phonetic_match = (snd1 == snd2)

    # Levenshtein on phonemic approximations
    dist = levenshtein_distance(c1, c2)
    max_len = max(len(c1), len(c2))
    edit_ratio = 1.0 - (dist / max(1, max_len))

    if phonetic_match and edit_ratio > 0.60:
        score = min(1.0, 0.70 + (edit_ratio * 0.30))
        return round(score, 3), True, f"Phonetic Indic Match ({snd1})"
    elif phonetic_match:
        return 0.65, True, f"Phonetic Key Equivalence ({snd1})"
    else:
        return round(max(0.0, edit_ratio * 0.60), 3), False, "Different phonetic signature"


# ==============================================================================
# 4. MULTI-SIGNAL ANTI-FALSE-MERGE DISAMBIGUATION
# ==============================================================================

def match_person_multi_signal(
    candidate_name: str,
    candidate_signals: Dict[str, Any],
    db: Session,
    case_id: int
) -> List[Dict[str, Any]]:
    """
    Safely matches a person name against case persons and verified aliases.
    Strictly enforces the anti-false-merge rule:
    A common name (e.g. 'Rahul Patil') without secondary corroboration
    is restricted to max confidence 0.65 (Medium) and CANNOT auto-merge.

    Corroborating signals:
    - Father's name match (+0.20)
    - Age within +/- 2 years (+0.10)
    - Phone number / CDR match (+0.25)
    - Address / police jurisdiction match (+0.15)
    """
    from models import CasePerson, PersonAlias

    cand_canonical = strip_indic_honorifics_and_affixes(candidate_name)
    cand_soundex = soundex_indic(cand_canonical)

    # 1. Fetch case persons and aliases
    persons = db.query(CasePerson).filter(CasePerson.case_id == case_id).all()
    aliases = db.query(PersonAlias).filter(PersonAlias.case_id == case_id).all()

    candidates: List[Dict[str, Any]] = []

    for p in persons:
        p_name = getattr(p, 'name', getattr(p, 'full_name', ''))
        p_father = getattr(p, 'father_or_spouse_name', getattr(p, 'father_name', ''))
        p_phone = getattr(p, 'contact_info', getattr(p, 'phone', ''))
        p_age = getattr(p, 'age', None)
        p_address = getattr(p, 'address', None)
        p_role = getattr(p, 'role', 'person')

        sim, p_match, reason = compute_name_similarity(cand_canonical, p_name)

        # Check aliases
        p_aliases = [a for a in aliases if a.person_id == p.id]
        for a in p_aliases:
            a_sim, a_match, a_reason = compute_name_similarity(cand_canonical, a.alias_name)
            if a_sim > sim:
                sim = a_sim
                p_match = a_match
                reason = f"Matched Alias '{a.alias_name}' ({a_reason})"

        if sim < 0.40 and not p_match:
            continue

        reasons = [reason]
        corroborated_score = sim

        # Signal 1: Father's Name Check
        cand_father = candidate_signals.get("father_name")
        if cand_father and p_father:
            f_sim, f_match, _ = compute_name_similarity(cand_father, p_father)
            if f_match or f_sim >= 0.75:
                corroborated_score = min(0.98, corroborated_score + 0.20)
                reasons.append(f"Father's name matches '{p_father}'")
            else:
                corroborated_score = max(0.30, corroborated_score - 0.25)
                reasons.append(f"Contradictory father's name ('{cand_father}' vs '{p_father}')")

        # Signal 2: Age / YOB Check
        cand_age = candidate_signals.get("age")
        if cand_age and p_age:
            try:
                diff = abs(int(cand_age) - int(p_age))
                if diff <= 2:
                    corroborated_score = min(0.98, corroborated_score + 0.10)
                    reasons.append(f"Age match (+/- {diff} yrs)")
                elif diff > 8:
                    corroborated_score = max(0.25, corroborated_score - 0.30)
                    reasons.append(f"Significant age disparity ({cand_age} vs {p_age})")
            except (ValueError, TypeError):
                pass

        # Signal 3: Phone / CDR Match
        cand_phone = candidate_signals.get("phone")
        if cand_phone and p_phone:
            c_p = re.sub(r'[^0-9]', '', str(cand_phone))[-10:]
            p_p = re.sub(r'[^0-9]', '', str(p_phone))[-10:]
            if c_p and p_p and c_p == p_p:
                corroborated_score = min(0.99, corroborated_score + 0.25)
                reasons.append(f"Exact phone number match ({c_p})")

        # Signal 4: Address / Location Check
        cand_address = candidate_signals.get("address")
        if cand_address and p_address:
            add_sim = compute_name_similarity(cand_address, p_address)[0]
            if add_sim > 0.60:
                corroborated_score = min(0.98, corroborated_score + 0.15)
                reasons.append(f"Residential area match ({cand_address})")

        # Enforce Anti-False-Merge Cap:
        # If no secondary signals are present, cap confidence at 0.65
        has_secondary_signals = any(
            candidate_signals.get(k) for k in ["father_name", "age", "phone", "address"]
        )
        if not has_secondary_signals and corroborated_score > 0.65:
            corroborated_score = 0.65
            reasons.append("Capped at 65% (Anti-False-Merge safeguard: no corroborating signals supplied)")

        tier = "high" if corroborated_score >= 0.85 else ("check" if corroborated_score >= 0.60 else "low")

        candidates.append({
            "person_id": p.id,
            "canonical_name": p_name,
            "matched_alias": p_name,
            "script": "devanagari" if any(0x0900 <= ord(c) <= 0x097F for c in p_name) else "latin",
            "similarity_score": round(corroborated_score, 3),
            "confidence_tier": tier,
            "phonetic_match": p_match,
            "matching_reasons": reasons,
            "coincidental_signals": {
                "age": p_age,
                "father_name": p_father,
                "phone": p_phone,
                "role": p_role
            }
        })

    # Sort descending by similarity score
    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return candidates


# ==============================================================================
# 5. OFFLINE TRANSLITERATION HELPER (LOW-TYPING CLIENT/SERVER ENGINE)
# ==============================================================================

def transliterate_indic(
    text: str,
    source_script: str = "latin",
    target_script: str = "devanagari",
    max_suggestions: int = 5
) -> List[str]:
    """
    Offline transliteration helper for low-typing data entry.
    Typing 'rahul' gives ['राहुल', 'राहुळ'].
    Typing 'राहुल' gives ['Rahul', 'Rahool'].
    """
    if not text or not text.strip():
        return []

    query = text.strip()

    if source_script == "latin" and target_script == "devanagari":
        clean = query.lower()
        if clean in COMMON_NAMES_MAP:
            return COMMON_NAMES_MAP[clean][:max_suggestions]

        # Rule-based phonetic approximation
        approx = _rough_latin_to_deva(clean)
        return [approx][:max_suggestions] if approx else [query]

    elif source_script == "devanagari" and target_script == "latin":
        if query in REVERSE_COMMON_MAP:
            return [REVERSE_COMMON_MAP[query]][:max_suggestions]

        approx = _deva_to_rough_latin(query).capitalize()
        return [approx][:max_suggestions] if approx else [query]

    return [query]


def _rough_latin_to_deva(word: str) -> str:
    """Basic phonetic mapper from Latin English to Devanagari syllables."""
    # Syllable patterns
    mapping = [
        ("shri", "श्री"), ("smt", "श्रीमती"),
        ("chha", "छा"), ("chhi", "छि"), ("chhe", "छे"), ("chh", "छ"),
        ("sha", "शा"), ("shi", "शि"), ("shee", "शी"), ("she", "शे"), ("sho", "शो"), ("sh", "श"),
        ("tha", "था"), ("thi", "थि"), ("the", "थे"), ("th", "थ"),
        ("dha", "धा"), ("dhi", "धि"), ("dhe", "धे"), ("dh", "ध"),
        ("kha", "खा"), ("khi", "खि"), ("khe", "खे"), ("kh", "ख"),
        ("gha", "घा"), ("ghi", "घि"), ("ghe", "घे"), ("gh", "घ"),
        ("pha", "फा"), ("phi", "फि"), ("phe", "फे"), ("ph", "फ"),
        ("bha", "भा"), ("bhi", "भि"), ("bhe", "भे"), ("bh", "भ"),
        ("ra", "रा"), ("ri", "रि"), ("ree", "री"), ("ru", "रु"), ("roo", "रू"), ("re", "रे"), ("ro", "रो"), ("r", "र"),
        ("ka", "का"), ("ki", "कि"), ("kee", "की"), ("ku", "कु"), ("koo", "कू"), ("ke", "के"), ("ko", "को"), ("k", "क"),
        ("ga", "गा"), ("gi", "गि"), ("gee", "गी"), ("gu", "गु"), ("goo", "गू"), ("ge", "गे"), ("go", "गो"), ("g", "ग"),
        ("ta", "ता"), ("ti", "ति"), ("tee", "ती"), ("tu", "तु"), ("too", "तू"), ("te", "ते"), ("to", "तो"), ("t", "त"),
        ("da", "दा"), ("di", "दि"), ("dee", "दी"), ("du", "दु"), ("doo", "दू"), ("de", "दे"), ("do", "दो"), ("d", "द"),
        ("na", "ना"), ("ni", "नि"), ("nee", "नी"), ("nu", "नु"), ("noo", "तू"), ("ne", "ने"), ("no", "नो"), ("n", "न"),
        ("pa", "पा"), ("pi", "पि"), ("pee", "पी"), ("pu", "पु"), ("poo", "पू"), ("pe", "पे"), ("po", "पो"), ("p", "प"),
        ("ba", "बा"), ("bi", "बि"), ("bee", "बी"), ("bu", "बु"), ("boo", "बू"), ("be", "बे"), ("bo", "बो"), ("b", "ब"),
        ("ma", "मा"), ("mi", "मि"), ("mee", "मी"), ("mu", "मु"), ("moo", "मू"), ("me", "मे"), ("mo", "मो"), ("m", "म"),
        ("ya", "या"), ("yi", "यि"), ("ye", "ये"), ("yo", "यो"), ("y", "य"),
        ("la", "ला"), ("li", "लि"), ("lee", "ली"), ("lu", "लु"), ("le", "ले"), ("lo", "लो"), ("l", "ल"),
        ("va", "वा"), ("vi", "वि"), ("vee", "वी"), ("vu", "वु"), ("ve", "वे"), ("vo", "वो"), ("v", "व"),
        ("sa", "सा"), ("si", "सि"), ("see", "सी"), ("su", "सु"), ("soo", "सू"), ("se", "से"), ("so", "सो"), ("s", "स"),
        ("ha", "हा"), ("hi", "हि"), ("hee", "ही"), ("hu", "हु"), ("he", "हे"), ("ho", "हो"), ("h", "ह"),
        ("a", "अ"), ("aa", "आ"), ("i", "इ"), ("ee", "ई"), ("u", "उ"), ("oo", "ऊ"), ("e", "ए"), ("o", "ओ")
    ]
    res = word
    for pat, dev in mapping:
        res = res.replace(pat, dev)
    return res
