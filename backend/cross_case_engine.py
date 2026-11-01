"""
Evidentia AI - Cross-Case Intelligence & Entity Resolution Engine.

Key Capabilities:
1. Multi-Tier Entity Resolution:
   - Tier 1: Exact identifier matching (phone numbers, vehicle registration plates, digital telemetry, IP/crypto/IMEI, emails).
   - Tier 2: Exact name and location matching.
   - Tier 3: Fuzzy name and address matching (token sort ratio & SequenceMatcher >= 85%).
2. Reviewer Confirmation Workflow:
   - Matches are queued as 'pending_review'.
   - Lead investigators / analysts can confirm or reject links with notes and audit trail.
3. Cross-Case MO Similarity:
   - Reuses `compute_mo_similarity` from `scoring.background` across cases.
   - Compares weapon, ingress/decoy method, victim demographics, corridor topology, time patterns, and tradecraft narrative.
   - Returns ranked similar cases with matching feature tags.
4. Strict RBAC Enforcement:
   - Non-admin users only ever see intelligence from cases they have explicit access to.
"""

import re
import json
import difflib
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from models import (
    Case, Entity, Evidence, PriorRecord, SuspectProfileFactor,
    AuditLog, User, CrossCaseEntityLink, CDRRecord, BankTransaction, Alert
)
from auth import check_case_access, get_user_accessible_case_ids
from scoring.background import compute_mo_similarity
from audit_engine import log_audit_event
from alerts_engine import create_or_update_alert
from collaboration import publish_collaboration_event

logger = logging.getLogger("evidentia.cross_case")

# ==============================================================================
# NORMALIZATION & EXTRACTION HELPERS
# ==============================================================================

# Common vehicle registration plate regex (Indian RTO pattern, e.g. MH-12-AQ-4411, DL-1P-C-0149, KA-01-AB-1234)
VEHICLE_PLATE_REGEX = re.compile(
    r'\b([A-Z]{2}[-\s]?[0-9]{1,2}[A-Z]?[-\s]?[A-Z]{1,2}[-\s]?[0-9]{4})\b',
    re.IGNORECASE
)

# Common phone number regex (Indian 10-digit mobile, with or without +91 or 0 prefix, or international format)
PHONE_REGEX = re.compile(
    r'(?:(?:\+|00)91[\s\-]?)?(?:[6789]\d{9})\b|\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b'
)

# Digital telemetry regexes
IP_REGEX = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
IMEI_REGEX = re.compile(r'\b\d{15}\b')
CRYPTO_REGEX = re.compile(r'\b(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,90}|0x[a-fA-F0-9]{40})\b')

PERSON_TITLES = {"dr", "mr", "mrs", "ms", "adv", "advocate", "inspector", "sub-inspector", "constable", "officer", "shri", "smt"}

PERSON_ENTITY_TYPES = {
    "person", "suspect", "victim", "witness", "approver",
    "personofinterest", "threatactor", "expert"
}

LOCATION_ENTITY_TYPES = {
    "location", "address", "facility", "targetinfrastructure", "corridor"
}

VEHICLE_ENTITY_TYPES = {
    "vehicle", "car", "cab", "bus", "truck", "automobile"
}


def normalize_phone_number(text: str) -> Optional[str]:
    """Extracts and normalizes phone number to canonical format with support for hyphens/spaces."""
    if not text:
        return None
    # Find candidate digit sequences with optional hyphens/spaces
    candidates = re.findall(r'(?:\+?91[\s\-]?)?(?:[6-9][0-9\s\-]{8,12}[0-9])', text)
    for cand in candidates:
        digits = re.sub(r'\D', '', cand)
        if len(digits) == 10 and digits[0] in "6789":
            return f"+91{digits}"
        elif len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
            return f"+{digits}"
        elif len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
            return f"+91{digits[1:]}"
    # General international 10-14 digit fallback
    match = PHONE_REGEX.search(text)
    if match:
        digits = re.sub(r'\D', '', match.group(0))
        if len(digits) >= 10:
            return f"+{digits}"
    return None


def extract_vehicle_plate(text: str) -> Optional[str]:
    """Extracts and standardizes vehicle registration plate token."""
    if not text:
        return None
    match = VEHICLE_PLATE_REGEX.search(text)
    if not match:
        return None
    raw = match.group(0).upper()
    # Normalize: strip spaces and hyphens
    cleaned = re.sub(r'[\s\-]', '', raw)
    return cleaned


def extract_digital_identifier(text: str) -> Optional[Tuple[str, str]]:
    """Returns (identifier_type, normalized_value) if digital identifier found."""
    if not text:
        return None
    ip_m = IP_REGEX.search(text)
    if ip_m:
        return ("ip_address", ip_m.group(0))
    email_m = EMAIL_REGEX.search(text)
    if email_m:
        return ("email", email_m.group(0).lower())
    imei_m = IMEI_REGEX.search(text)
    if imei_m:
        return ("imei", imei_m.group(0))
    crypto_m = CRYPTO_REGEX.search(text)
    if crypto_m:
        return ("crypto_wallet", crypto_m.group(0))
    return None


def normalize_person_name(name: str) -> str:
    """Normalizes person names by removing titles, aliases, parenthetical roles."""
    if not name:
        return ""
    # Remove parentheticals like "(Accused - Driver)" or "(Alias Bullet)"
    cleaned = re.sub(r'\(.*?\)', '', name)
    # Remove common prefixes/titles
    words = re.findall(r'[A-Za-z]+', cleaned.lower())
    filtered = [w for w in words if w not in PERSON_TITLES]
    return " ".join(filtered)


def normalize_address(addr: str) -> str:
    """Normalizes location/address string."""
    if not addr:
        return ""
    cleaned = re.sub(r'[^\w\s]', ' ', addr.lower())
    words = re.findall(r'[a-z0-9]+', cleaned)
    # Filter very generic location terms if standalone
    stop_words = {"near", "opp", "opposite", "sector", "area", "cross"}
    filtered = [w for w in words if w not in stop_words]
    return " ".join(filtered)


def compute_string_similarity(s1: str, s2: str) -> float:
    """Calculates maximum of character sequence ratio and token-sort ratio."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()

    # Token sort ratio (handles "Yogesh Raut" vs "Raut Yogesh")
    tokens1 = sorted(s1.split())
    tokens2 = sorted(s2.split())
    sorted_s1 = " ".join(tokens1)
    sorted_s2 = " ".join(tokens2)
    token_sort_ratio = difflib.SequenceMatcher(None, sorted_s1, sorted_s2).ratio()

    return max(seq_ratio, token_sort_ratio)


# ==============================================================================
# MULTI-TIER ENTITY RESOLUTION LOGIC
# ==============================================================================

def match_entity_pair(
    source_entity: Entity,
    target_entity: Entity,
    source_case_id: int,
    target_case_id: int
) -> Optional[Dict[str, Any]]:
    """
    Evaluates two entities across cases and returns match dictionary if resolved:
    Tier 1: Exact identifier matches (phone, vehicle plate, digital telemetry).
    Tier 2: Exact name or location matches.
    Tier 3: Fuzzy person name (>=85%) or address matches (>=85%).
    Returns None if no match.
    """
    s_name = source_entity.name or ""
    t_name = target_entity.name or ""
    s_type = (source_entity.type or "").lower()
    t_type = (target_entity.type or "").lower()

    # -------------------------------------------------------------------------
    # TIER 1: EXACT IDENTIFIER MATCHES
    # -------------------------------------------------------------------------

    # 1A. Phone Numbers
    s_phone = normalize_phone_number(s_name)
    t_phone = normalize_phone_number(t_name)
    if s_phone and t_phone and s_phone == t_phone:
        return {
            "entity_type": "phone",
            "match_type": "exact_identifier",
            "match_value": s_phone,
            "similarity_score": 1.0,
            "confidence_reason": (
                f"Exact telephone number match ({s_phone}) identified across "
                f"Case #{source_case_id} and Case #{target_case_id}."
            )
        }

    # 1B. Vehicle Registration Plates
    s_plate = extract_vehicle_plate(s_name)
    t_plate = extract_vehicle_plate(t_name)
    if s_plate and t_plate and s_plate == t_plate:
        return {
            "entity_type": "vehicle",
            "match_type": "exact_identifier",
            "match_value": s_plate,
            "similarity_score": 1.0,
            "confidence_reason": (
                f"Exact vehicle registration plate match ({s_plate}) identified across "
                f"Case #{source_case_id} and Case #{target_case_id}."
            )
        }

    # 1C. Digital Telemetry (IP, Crypto Wallet, IMEI, Email)
    s_dig = extract_digital_identifier(s_name)
    t_dig = extract_digital_identifier(t_name)
    if s_dig and t_dig and s_dig[0] == t_dig[0] and s_dig[1] == t_dig[1]:
        return {
            "entity_type": "digital",
            "match_type": "exact_identifier",
            "match_value": s_dig[1],
            "similarity_score": 1.0,
            "confidence_reason": (
                f"Exact digital telemetry match ({s_dig[0]}: {s_dig[1]}) identified across "
                f"Case #{source_case_id} and Case #{target_case_id}."
            )
        }

    # -------------------------------------------------------------------------
    # TIER 2: EXACT NAME OR ADDRESS MATCHES
    # -------------------------------------------------------------------------

    is_s_person = s_type in PERSON_ENTITY_TYPES
    is_t_person = t_type in PERSON_ENTITY_TYPES

    if is_s_person and is_t_person:
        s_norm_person = normalize_person_name(s_name)
        t_norm_person = normalize_person_name(t_name)

        if s_norm_person and t_norm_person:
            # Exact normalized name
            if s_norm_person == t_norm_person and len(s_norm_person) >= 3:
                return {
                    "entity_type": "person",
                    "match_type": "exact_name",
                    "match_value": s_name,
                    "similarity_score": 0.95,
                    "confidence_reason": (
                        f"Exact person identity match ('{s_name}') identified across "
                        f"Case #{source_case_id} and Case #{target_case_id}."
                    )
                }

    is_s_loc = s_type in LOCATION_ENTITY_TYPES
    is_t_loc = t_type in LOCATION_ENTITY_TYPES

    if is_s_loc and is_t_loc:
        s_norm_loc = normalize_address(s_name)
        t_norm_loc = normalize_address(t_name)

        if s_norm_loc and t_norm_loc:
            if s_norm_loc == t_norm_loc and len(s_norm_loc) >= 4:
                return {
                    "entity_type": "address",
                    "match_type": "exact_name",
                    "match_value": s_name,
                    "similarity_score": 0.95,
                    "confidence_reason": (
                        f"Exact location match ('{s_name}') identified across "
                        f"Case #{source_case_id} and Case #{target_case_id}."
                    )
                }

    # -------------------------------------------------------------------------
    # TIER 3: FUZZY MATCHES (Second Priority, threshold >= 85%)
    # -------------------------------------------------------------------------

    if is_s_person and is_t_person:
        s_norm_person = normalize_person_name(s_name)
        t_norm_person = normalize_person_name(t_name)

        if s_norm_person and t_norm_person:
            # 3A. Substring / Token subset (e.g. "Yogesh Raut" in "Yogesh Ashok Raut")
            s_toks = set(s_norm_person.split())
            t_toks = set(t_norm_person.split())
            if len(s_toks) >= 2 and len(t_toks) >= 2:
                if s_toks.issubset(t_toks) or t_toks.issubset(s_toks):
                    return {
                        "entity_type": "person",
                        "match_type": "fuzzy_name",
                        "match_value": s_name,
                        "similarity_score": 0.90,
                        "confidence_reason": (
                            f"High-confidence name variation match ('{s_name}' vs '{t_name}') "
                            f"with matching forename and surname."
                        )
                    }

            # 3B. Fuzzy String Ratio
            sim = compute_string_similarity(s_norm_person, t_norm_person)
            if sim >= 0.85:
                return {
                    "entity_type": "person",
                    "match_type": "fuzzy_name",
                    "match_value": s_name,
                    "similarity_score": round(sim, 3),
                    "confidence_reason": (
                        f"Fuzzy name match ({int(sim * 100)}% lexical similarity: "
                        f"'{s_name}' vs '{t_name}')."
                    )
                }

    if is_s_loc and is_t_loc:
        s_norm_loc = normalize_address(s_name)
        t_norm_loc = normalize_address(t_name)

        if s_norm_loc and t_norm_loc:
            loc_sim = compute_string_similarity(s_norm_loc, t_norm_loc)
            if loc_sim >= 0.85:
                return {
                    "entity_type": "address",
                    "match_type": "fuzzy_address",
                    "match_value": s_name,
                    "similarity_score": round(loc_sim, 3),
                    "confidence_reason": (
                        f"Fuzzy location/corridor match ({int(loc_sim * 100)}% similarity: "
                        f"'{s_name}' vs '{t_name}')."
                    )
                }

    return None


# ==============================================================================
# RESOLUTION DISCOVERY & WORKFLOW
# ==============================================================================

def resolve_cross_case_entities(
    case_id: int,
    user: User,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Scans entities of `case_id` against all target cases accessible to `user`.
    Creates or updates `CrossCaseEntityLink` records with status='pending_review'
    if not previously reviewed.
    Respects RBAC: only queries accessible cases.
    """
    # 1. RBAC check on source case
    if not check_case_access(case_id, user, db, "read"):
        user_ident = getattr(user, "email", str(getattr(user, "id", "unknown")))
        logger.warning(f"User {user_ident} denied access to source case {case_id}")
        return []

    accessible_ids = get_user_accessible_case_ids(user, db)

    # 2. Query target cases
    target_query = db.query(Case).filter(Case.id != case_id)
    if accessible_ids is not None:
        target_query = target_query.filter(Case.id.in_(accessible_ids))

    target_cases = target_query.all()
    if not target_cases:
        return []

    target_case_ids = [c.id for c in target_cases]

    # 3. Fetch source entities
    source_entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    if not source_entities:
        return []

    # 4. Fetch target entities in accessible cases
    target_entities = db.query(Entity).filter(Entity.case_id.in_(target_case_ids)).all()

    # Pre-load existing links to prevent overwriting existing reviews
    existing_links = db.query(CrossCaseEntityLink).filter(
        or_(
            and_(CrossCaseEntityLink.source_case_id == case_id, CrossCaseEntityLink.target_case_id.in_(target_case_ids)),
            and_(CrossCaseEntityLink.target_case_id == case_id, CrossCaseEntityLink.source_case_id.in_(target_case_ids))
        )
    ).all()

    existing_pair_map = {}
    for link in existing_links:
        key1 = (link.source_case_id, link.target_case_id, link.source_entity_id, link.target_entity_id)
        key2 = (link.target_case_id, link.source_case_id, link.target_entity_id, link.source_entity_id)
        existing_pair_map[key1] = link
        existing_pair_map[key2] = link

    new_links_count = 0

    # 5. Execute Multi-Tier Resolution: Exact Identifiers first, Fuzzy second
    for se in source_entities:
        for te in target_entities:
            pair_key = (case_id, te.case_id, se.id, te.id)
            if pair_key in existing_pair_map:
                continue

            match_result = match_entity_pair(se, te, case_id, te.case_id)
            if match_result:
                new_link = CrossCaseEntityLink(
                    source_case_id=case_id,
                    source_entity_id=se.id,
                    target_case_id=te.case_id,
                    target_entity_id=te.id,
                    entity_type=match_result["entity_type"],
                    match_type=match_result["match_type"],
                    match_value=match_result["match_value"],
                    similarity_score=match_result["similarity_score"],
                    status="pending_review",
                    confidence_reason=match_result["confidence_reason"]
                )
                db.add(new_link)
                existing_pair_map[pair_key] = new_link
                new_links_count += 1

    if new_links_count > 0:
        db.commit()

    return get_cross_case_entity_links(case_id, user, db)


def get_cross_case_entity_links(
    case_id: int,
    user: User,
    db: Session,
    status_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns all cross-case entity links for `case_id` filtered strictly by RBAC.
    Users only see links where both source and target cases are accessible.
    """
    if not check_case_access(case_id, user, db, "read"):
        return []

    accessible_ids = get_user_accessible_case_ids(user, db)

    query = db.query(CrossCaseEntityLink).filter(
        or_(
            CrossCaseEntityLink.source_case_id == case_id,
            CrossCaseEntityLink.target_case_id == case_id
        )
    )

    if status_filter:
        query = query.filter(CrossCaseEntityLink.status == status_filter)

    links = query.order_by(CrossCaseEntityLink.similarity_score.desc()).all()

    results = []
    for link in links:
        other_case_id = link.target_case_id if link.source_case_id == case_id else link.source_case_id

        # RBAC Check: Ensure user has access to the other case
        if accessible_ids is not None and other_case_id not in accessible_ids:
            continue

        other_case = db.query(Case).filter(Case.id == other_case_id).first()
        other_case_title = other_case.title if other_case else f"Case #{other_case_id}"

        source_entity = db.query(Entity).filter(Entity.id == link.source_entity_id).first() if link.source_entity_id else None
        target_entity = db.query(Entity).filter(Entity.id == link.target_entity_id).first() if link.target_entity_id else None

        # Canonicalize source as current case and target as other case for frontend display
        if link.source_case_id == case_id:
            curr_entity = source_entity
            linked_entity = target_entity
        else:
            curr_entity = target_entity
            linked_entity = source_entity

        results.append({
            "id": link.id,
            "case_id": case_id,
            "linked_case_id": other_case_id,
            "linked_case_title": other_case_title,
            "entity_type": link.entity_type,
            "match_type": link.match_type,
            "match_value": link.match_value,
            "similarity_score": link.similarity_score,
            "status": link.status,
            "confidence_reason": link.confidence_reason,
            "source_entity": {
                "id": curr_entity.id if curr_entity else None,
                "name": curr_entity.name if curr_entity else "Unknown",
                "type": curr_entity.type if curr_entity else link.entity_type
            },
            "linked_entity": {
                "id": linked_entity.id if linked_entity else None,
                "name": linked_entity.name if linked_entity else "Unknown",
                "type": linked_entity.type if linked_entity else link.entity_type
            },
            "reviewed_by_user_id": link.reviewed_by_user_id,
            "reviewed_by_name": link.reviewed_by_name,
            "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
            "reviewer_notes": link.reviewer_notes,
            "created_at": link.created_at.isoformat() if link.created_at else None
        })

    return results


def confirm_or_reject_entity_link(
    link_id: int,
    status: str,
    user: User,
    notes: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """
    Reviewer/Analyst action: Confirms or rejects a cross-case entity link.
    Validates user has edit or analyze permissions on the associated case.
    Logs action to cryptographic Merkle audit trail.
    """
    if status not in {"confirmed", "rejected", "pending_review"}:
        raise ValueError("Status must be 'confirmed', 'rejected', or 'pending_review'.")

    link = db.query(CrossCaseEntityLink).filter(CrossCaseEntityLink.id == link_id).first()
    if not link:
        raise ValueError(f"CrossCaseEntityLink #{link_id} not found.")

    # Permissions check: User MUST have authorization to open BOTH cases to review cross-case linkages
    can_read_src = check_case_access(link.source_case_id, user, db, "read")
    can_read_tgt = check_case_access(link.target_case_id, user, db, "read")
    if not (can_read_src and can_read_tgt):
        raise PermissionError("Access denied: You must have authorization to access both cases to review cross-case linkages.")

    can_edit_src = check_case_access(link.source_case_id, user, db, "analyze")
    can_edit_tgt = check_case_access(link.target_case_id, user, db, "analyze")

    if not (can_edit_src or can_edit_tgt or user.role in {"admin", "lead_investigator"}):
        raise PermissionError("Insufficient permissions to review this cross-case entity link.")

    old_status = link.status
    link.status = status
    link.reviewed_by_user_id = user.id
    user_ident = getattr(user, "full_name", None) or getattr(user, "email", str(getattr(user, "id", "reviewer")))
    link.reviewed_by_name = user_ident
    link.reviewed_at = datetime.now(timezone.utc)
    link.reviewer_notes = notes
    db.commit()
    db.refresh(link)

    # Log to Merkle Audit Chain
    log_audit_event(
        db=db,
        action_type="CROSS_CASE_ENTITY_LINK_REVIEWED",
        target_type="cross_case_entity_link",
        target_id=str(link.id),
        description=(
            f"Cross-case link #{link.id} ({link.match_value}) updated from {old_status} "
            f"to {status} by {user_ident}. Notes: {notes or 'None'}"
        ),
        user_id=user.id,
        user_name=user_ident,
        user_role=getattr(user, "role", "analyst"),
        case_id=link.source_case_id,
        before_value=old_status,
        after_value=status
    )

    return {
        "id": link.id,
        "status": link.status,
        "reviewed_by_name": link.reviewed_by_name,
        "reviewed_at": link.reviewed_at.isoformat() if link.reviewed_at else None,
        "reviewer_notes": link.reviewer_notes,
        "message": f"Link #{link.id} successfully marked as {status}."
    }


# ==============================================================================
# CROSS-CASE MO SIMILARITY ENGINE
# ==============================================================================

def extract_case_mo_profile(case: Case, db: Session) -> Dict[str, Any]:
    """
    Synthesizes the Modus Operandi (MO) profile for a case from:
    1. SuspectProfileFactor and PriorRecord entries.
    2. Case title, description, hypotheses, evidence exhibits, and statutory offence narrative.
    """
    from models import Hypothesis

    profile: Dict[str, Any] = {
        "weapon_used": "",
        "entry_method": "",
        "victim_type": "",
        "location_type": "",
        "time_pattern": "",
        "mo_description": f"{case.title or ''}. {case.description or ''}"
    }

    # 1. Check PriorRecords in the case
    prior = db.query(PriorRecord).filter(PriorRecord.case_id == case.id).first()
    if prior:
        profile["weapon_used"] = getattr(prior, "weapon_used", "") or ""
        profile["entry_method"] = getattr(prior, "entry_method", "") or ""
        profile["victim_type"] = getattr(prior, "victim_type", "") or ""
        profile["location_type"] = getattr(prior, "location_type", "") or ""
        profile["time_pattern"] = getattr(prior, "time_pattern", "") or ""

    # 2. Check SuspectProfileFactor in the case
    factors = db.query(SuspectProfileFactor).filter(SuspectProfileFactor.case_id == case.id).all()
    for f in factors:
        ftype = (f.factor_type or "").lower()
        fval = f.factor_value or ""
        if "weapon" in ftype and not profile["weapon_used"]:
            profile["weapon_used"] = fval
        elif ("entry" in ftype or "vehicle" in ftype) and not profile["entry_method"]:
            profile["entry_method"] = fval
        elif "victim" in ftype and not profile["victim_type"]:
            profile["victim_type"] = fval
        elif ("location" in ftype or "vicinity" in ftype) and not profile["location_type"]:
            profile["location_type"] = fval

    # 3. Aggregate full case context (title, description, hypotheses, evidence exhibits)
    hyps = db.query(Hypothesis).filter(Hypothesis.case_id == case.id).all()
    evs = db.query(Evidence).filter(Evidence.case_id == case.id).all()

    hyp_text = " ".join((h.title or "") + " " + (h.description or "") for h in hyps)
    ev_text = " ".join(
        (getattr(e, "file_name", "") or "") + " " + (getattr(e, "evidence_type", "") or "") + " " + (e.extracted_text[:600] if e.extracted_text else "")
        for e in evs
    )
    full_narrative = f"{case.title or ''} {case.description or ''} {case.offence_section or ''} {hyp_text} {ev_text}".lower()

    if not profile["weapon_used"] or profile["weapon_used"].lower() in {"direct_physical_access", "limited_capacity"}:
        if any(w in full_narrative for w in ["jack", "rod", "iron", "metallic", "blunt", "wrench", "pipe"]):
            profile["weapon_used"] = "Iron jack rod and blunt tool"
        elif any(w in full_narrative for w in ["knife", "blade", "sharp", "cutter", "dagger"]):
            profile["weapon_used"] = "Sharp edged blade / knife"
        elif any(w in full_narrative for w in ["gun", "pistol", "revolver", "firearm", "bullet"]):
            profile["weapon_used"] = "Firearm / handgun"

    if not profile["entry_method"] or profile["entry_method"].lower() in {"direct_physical_access", "none"}:
        if any(w in full_narrative for w in ["qualis", "cab", "taxi", "ambush", "decoy", "boarding"]):
            profile["entry_method"] = "Cab / vehicle transport decoy ambush"
        elif any(w in full_narrative for w in ["bus", "charter", "transit", "van"]):
            profile["entry_method"] = "Chartered bus transit decoy intercept"
        elif any(w in full_narrative for w in ["door", "window", "lock", "trespass", "breach"]):
            profile["entry_method"] = "Forced entry / structural trespass"

    if not profile["victim_type"]:
        if any(w in full_narrative for w in ["techie", "female", "woman", "commuter", "bpo", "lone", "intern"]):
            profile["victim_type"] = "Lone female commuter / tech employee"
        elif any(w in full_narrative for w in ["passengers", "couple", "travelers", "companion"]):
            profile["victim_type"] = "Transit passengers / commuters"
        elif any(w in full_narrative for w in ["elderly", "pedestrian"]):
            profile["victim_type"] = "Pedestrian / vulnerable civilian"

    if not profile["location_type"]:
        if any(w in full_narrative for w in ["bypass", "highway", "expressway", "arterial", "outskirts", "desolate", "toll"]):
            profile["location_type"] = "Transit bypass / arterial highway corridor"
        elif any(w in full_narrative for w in ["apartment", "residence", "house", "bungalow"]):
            profile["location_type"] = "Residential premises"
        elif any(w in full_narrative for w in ["atm", "bank", "substation", "facility"]):
            profile["location_type"] = "Commercial / utility facility"

    if not profile["time_pattern"]:
        if any(w in full_narrative for w in ["night", "21:00", "20:00", "22:00", "23:00", "midnight", "shift", "dark", "evening"]):
            profile["time_pattern"] = "Late night shift hours"
        elif any(w in full_narrative for w in ["morning", "day", "afternoon"]):
            profile["time_pattern"] = "Daylight hours"

    return profile


def find_mo_similar_cases(
    case_id: int,
    user: User,
    db: Session,
    min_similarity: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Reuses `compute_mo_similarity` to compare `case_id` against all stored cases.
    Respects case permissions: strictly limits candidates to user-accessible cases.
    Returns ranked similar cases with matched tradecraft feature tags.
    """
    if not check_case_access(case_id, user, db, "read"):
        user_ident = getattr(user, "email", str(getattr(user, "id", "unknown")))
        logger.warning(f"User {user_ident} denied access to source case {case_id}")
        return []

    source_case = db.query(Case).filter(Case.id == case_id).first()
    if not source_case:
        return []

    accessible_ids = get_user_accessible_case_ids(user, db)

    # Query target cases
    target_query = db.query(Case).filter(Case.id != case_id)
    if accessible_ids is not None:
        target_query = target_query.filter(Case.id.in_(accessible_ids))

    target_cases = target_query.all()
    if not target_cases:
        return []

    # Synthesize source MO profile
    source_mo_profile = extract_case_mo_profile(source_case, db)

    similar_cases = []

    for tgt in target_cases:
        tgt_mo_profile = extract_case_mo_profile(tgt, db)

        # Execute relevance engine comparison
        mo_res = compute_mo_similarity(tgt_mo_profile, source_mo_profile)

        overall_sim = mo_res.get("overall_similarity", 0.0)
        if overall_sim >= min_similarity:
            field_scores = mo_res.get("field_scores", {})
            matching_tradecraft = mo_res.get("matching_tradecraft", [])

            similar_cases.append({
                "case_id": tgt.id,
                "title": tgt.title,
                "fir_number": tgt.fir_number or f"FIR-CASE-{tgt.id}",
                "status": tgt.status,
                "offence_section": tgt.offence_section or "N/A",
                "similarity_score": overall_sim,
                "similarity_percentage": round(overall_sim * 100.0, 1),
                "matched_features": matching_tradecraft,
                "field_scores": field_scores,
                "description_snippet": (tgt.description[:180] + "...") if tgt.description and len(tgt.description) > 180 else (tgt.description or "")
            })

    # Sort descending by similarity score
    similar_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
    return similar_cases


# ==============================================================================
# REAL-TIME CROSS-CASE MATCHING ENGINE ON EXHIBIT INGESTION
# ==============================================================================

def match_exhibit_cross_case_realtime(
    evidence_id: Optional[int],
    user: User,
    db: Session,
    case_id: Optional[int] = None,
    file_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Real-Time Cross-Case Matcher:
    Executed automatically on every newly ingested or processed exhibit.
    Extracts phone numbers, vehicle registration plates, addresses/locations,
    and person names from the exhibit and checks them against all other cases
    the user is permitted to access.

    CRITICAL JUDICIAL SAFEGUARDS:
    1. Candidate links are strictly created with status='pending_review'.
       Cases and entities are NEVER merged automatically without human confirmation.
    2. Strict RBAC: only searches cases accessible to the user, and links are only visible
       to individuals authorized to open both cases.
    3. Raises high-priority alerts with deduplication keys.
    4. Broadcasts real-time events to connected clients.
    """
    evidence = None
    if evidence_id:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()

    source_case_id = (evidence.case_id if evidence else None) or case_id
    if not source_case_id:
        return []

    if not check_case_access(source_case_id, user, db, "read"):
        logger.warning(f"[CrossCase] Access denied to source case {source_case_id} for user {user.id}")
        return []

    accessible_ids = get_user_accessible_case_ids(user, db)
    if accessible_ids is not None and source_case_id not in accessible_ids:
        return []

    # Query target cases accessible to the user
    target_query = db.query(Case).filter(Case.id != source_case_id)
    if accessible_ids is not None:
        target_query = target_query.filter(Case.id.in_(accessible_ids))
    target_cases = target_query.all()
    if not target_cases:
        return []

    target_case_ids = [c.id for c in target_cases]

    # 1. GATHER CANDIDATE FEATURES FROM THIS EXHIBIT
    exhibit_phones: Set[str] = set()
    exhibit_plates: Set[str] = set()
    exhibit_locations: Set[str] = set()
    exhibit_names: Set[str] = set()
    exhibit_digital: Set[Tuple[str, str]] = set()

    corpus_parts = []
    if evidence:
        if evidence.file_name:
            corpus_parts.append(evidence.file_name)
        if evidence.extracted_text:
            corpus_parts.append(evidence.extracted_text)
        if evidence.source:
            corpus_parts.append(evidence.source)
    if file_name:
        corpus_parts.append(file_name)
    corpus = "\n".join(corpus_parts)

    # Phone numbers extraction (including hyphenated/spaced variations)
    phone_candidates = re.findall(r'(?:\+?91[\s\-]?)?(?:[6-9][0-9\s\-]{8,12}[0-9])', corpus)
    for p in phone_candidates:
        p_norm = normalize_phone_number(p)
        if p_norm:
            exhibit_phones.add(p_norm)
    for match in PHONE_REGEX.finditer(corpus):
        p_norm = normalize_phone_number(match.group(0))
        if p_norm:
            exhibit_phones.add(p_norm)

    # Vehicle registration plates extraction
    for match in VEHICLE_PLATE_REGEX.finditer(corpus):
        pl_norm = extract_vehicle_plate(match.group(0))
        if pl_norm:
            exhibit_plates.add(pl_norm)

    # Digital telemetry extraction
    dig = extract_digital_identifier(corpus)
    if dig:
        exhibit_digital.add(dig)

    # If CDR records exist for this evidence or case
    if evidence:
        cdr_rows = db.query(CDRRecord).filter(CDRRecord.evidence_id == evidence.id).limit(300).all()
        for r in cdr_rows:
            if r.calling_number:
                cn = normalize_phone_number(r.calling_number)
                if cn:
                    exhibit_phones.add(cn)
            if r.called_number:
                cbn = normalize_phone_number(r.called_number)
                if cbn:
                    exhibit_phones.add(cbn)
            if r.site_name and len(r.site_name.strip()) >= 4:
                exhibit_locations.add(r.site_name.strip())

        # If Bank transactions exist
        bank_rows = db.query(BankTransaction).filter(BankTransaction.evidence_id == evidence.id).limit(200).all()
        for b in bank_rows:
            if b.counterparty_name and len(b.counterparty_name.strip()) >= 3:
                exhibit_names.add(b.counterparty_name.strip())
            if b.counterparty_account:
                exhibit_digital.add(("bank_account", b.counterparty_account.strip().upper()))

    # Gather entities linked to this exhibit or case
    source_entities = db.query(Entity).filter(
        or_(
            Entity.evidence_id == (evidence.id if evidence else -1),
            Entity.case_id == source_case_id
        )
    ).all()

    for se in source_entities:
        se_type = (se.type or "").lower()
        se_name = se.name or ""
        if se_type in PERSON_ENTITY_TYPES:
            norm_p = normalize_person_name(se_name)
            if len(norm_p) >= 3:
                exhibit_names.add(se_name)
        elif se_type in LOCATION_ENTITY_TYPES:
            norm_l = normalize_address(se_name)
            if len(norm_l) >= 4:
                exhibit_locations.add(se_name)
        elif se_type in VEHICLE_ENTITY_TYPES or extract_vehicle_plate(se_name):
            norm_v = extract_vehicle_plate(se_name)
            if norm_v:
                exhibit_plates.add(norm_v)
        else:
            norm_ph = normalize_phone_number(se_name)
            if norm_ph:
                exhibit_phones.add(norm_ph)

    # 2. QUERY TARGET ACCESSIBLE CASES
    target_entities = db.query(Entity).filter(Entity.case_id.in_(target_case_ids)).all()
    target_cdrs = db.query(CDRRecord).filter(CDRRecord.case_id.in_(target_case_ids)).limit(600).all()
    target_banks = db.query(BankTransaction).filter(BankTransaction.case_id.in_(target_case_ids)).limit(400).all()

    # Pre-load existing links to prevent creating duplicates
    existing_links = db.query(CrossCaseEntityLink).filter(
        or_(
            and_(CrossCaseEntityLink.source_case_id == source_case_id, CrossCaseEntityLink.target_case_id.in_(target_case_ids)),
            and_(CrossCaseEntityLink.target_case_id == source_case_id, CrossCaseEntityLink.source_case_id.in_(target_case_ids))
        )
    ).all()
    existing_link_values = {
        (min(l.source_case_id, l.target_case_id), max(l.source_case_id, l.target_case_id), l.match_value)
        for l in existing_links
    }

    newly_created_links: List[CrossCaseEntityLink] = []
    exhibit_label = evidence.file_name if evidence else (file_name or "New Exhibit")

    def record_candidate_link(tgt_case_id: int, src_ent: Optional[Entity], tgt_ent: Optional[Entity],
                              e_type: str, m_type: str, m_val: str, score: float, reason: str):
        pair_key = (min(source_case_id, tgt_case_id), max(source_case_id, tgt_case_id), m_val)
        if pair_key in existing_link_values:
            return None

        link = CrossCaseEntityLink(
            source_case_id=source_case_id,
            source_entity_id=src_ent.id if src_ent else None,
            target_case_id=tgt_case_id,
            target_entity_id=tgt_ent.id if tgt_ent else None,
            entity_type=e_type,
            match_type=m_type,
            match_value=m_val,
            similarity_score=score,
            status="pending_review",  # STRICTLY candidate link; never merged without confirmation
            confidence_reason=reason
        )
        db.add(link)
        db.flush()
        existing_link_values.add(pair_key)
        newly_created_links.append(link)

        # Lookup target case title
        tgt_case = db.query(Case).filter(Case.id == tgt_case_id).first()
        tgt_title = tgt_case.title if tgt_case else f"Case #{tgt_case_id}"

        # Raise high-priority deduplicated alert
        dedup_key = f"cross_case_hit_{min(source_case_id, tgt_case_id)}_{max(source_case_id, tgt_case_id)}_{e_type}_{m_val}"
        create_or_update_alert(
            db=db,
            case_id=source_case_id,
            rule_type="cross_case_match",
            title=f"Possibly Connected Case: Case #{tgt_case_id} ({tgt_title})",
            message=(
                f"New exhibit '{exhibit_label}' in Case #{source_case_id} matched {e_type} '{m_val}' "
                f"with Case #{tgt_case_id} ('{tgt_title}'). Flagged for investigator confirmation."
            ),
            severity="high",
            dedup_key=dedup_key,
            linked_item_type="cross_case_entity_link",
            linked_item_id=link.id
        )

        # Broadcast SSE stream event
        try:
            publish_collaboration_event(
                db=db,
                case_id=source_case_id,
                event_type="cross_case_candidate_flagged",
                item_type="cross_case_link",
                item_id=str(link.id),
                summary=f"Possibly connected case flagged: #{tgt_case_id} via matching {e_type} '{m_val}'",
                payload={
                    "case_id": source_case_id,
                    "linked_case_id": tgt_case_id,
                    "linked_case_title": tgt_title,
                    "entity_type": e_type,
                    "match_value": m_val,
                    "evidence_id": evidence.id if evidence else None,
                    "evidence_file_name": exhibit_label
                },
                commit=False
            )
        except Exception as se:
            logger.debug(f"[CrossCase] SSE notice: {se}")

        return link

    # A. Check Phone Numbers
    for phone in exhibit_phones:
        for te in target_entities:
            te_phone = normalize_phone_number(te.name)
            if te_phone and te_phone == phone:
                src_ent = next((se for se in source_entities if normalize_phone_number(se.name) == phone), None)
                record_candidate_link(
                    te.case_id, src_ent, te, "phone", "exact_identifier", phone, 1.0,
                    f"Exact telephone match ({phone}) discovered in exhibit '{exhibit_label}' matching entity '{te.name}' in Case #{te.case_id}."
                )
        for c in target_cdrs:
            c_calling = normalize_phone_number(c.calling_number)
            c_called = normalize_phone_number(c.called_number)
            if (c_calling and c_calling == phone) or (c_called and c_called == phone):
                src_ent = next((se for se in source_entities if normalize_phone_number(se.name) == phone), None)
                record_candidate_link(
                    c.case_id, src_ent, None, "phone", "exact_identifier", phone, 1.0,
                    f"Exact telephone match ({phone}) discovered in exhibit '{exhibit_label}' matching CDR tower ping in Case #{c.case_id}."
                )

    # B. Check Vehicle Registration Plates
    for plate in exhibit_plates:
        for te in target_entities:
            te_plate = extract_vehicle_plate(te.name)
            if te_plate and te_plate == plate:
                src_ent = next((se for se in source_entities if extract_vehicle_plate(se.name) == plate), None)
                record_candidate_link(
                    te.case_id, src_ent, te, "vehicle", "exact_identifier", plate, 1.0,
                    f"Exact vehicle registration plate match ({plate}) discovered in exhibit '{exhibit_label}' matching vehicle in Case #{te.case_id}."
                )

    # C. Check Person Names
    for name in exhibit_names:
        norm_name = normalize_person_name(name)
        if len(norm_name) < 3:
            continue
        for te in target_entities:
            if (te.type or "").lower() in PERSON_ENTITY_TYPES:
                te_norm = normalize_person_name(te.name)
                if not te_norm:
                    continue
                src_ent = next((se for se in source_entities if normalize_person_name(se.name) == norm_name), None)
                if norm_name == te_norm:
                    record_candidate_link(
                        te.case_id, src_ent, te, "person", "exact_name", name, 0.95,
                        f"Exact person identity match ('{name}') discovered in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                    )
                else:
                    toks1 = set(norm_name.split())
                    toks2 = set(te_norm.split())
                    if len(toks1) >= 2 and len(toks2) >= 2 and (toks1.issubset(toks2) or toks2.issubset(toks1)):
                        record_candidate_link(
                            te.case_id, src_ent, te, "person", "fuzzy_name", name, 0.90,
                            f"Name variation match ('{name}' vs '{te.name}') discovered in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                        )
                    else:
                        sim = compute_string_similarity(norm_name, te_norm)
                        if sim >= 0.85:
                            record_candidate_link(
                                te.case_id, src_ent, te, "person", "fuzzy_name", name, round(sim, 3),
                                f"Fuzzy person match ({int(sim*100)}% similarity: '{name}' vs '{te.name}') in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                            )

    # D. Check Addresses / Locations
    for loc in exhibit_locations:
        norm_loc = normalize_address(loc)
        if len(norm_loc) < 4:
            continue
        for te in target_entities:
            if (te.type or "").lower() in LOCATION_ENTITY_TYPES:
                te_norm = normalize_address(te.name)
                if not te_norm:
                    continue
                src_ent = next((se for se in source_entities if normalize_address(se.name) == norm_loc), None)
                if norm_loc == te_norm:
                    record_candidate_link(
                        te.case_id, src_ent, te, "address", "exact_name", loc, 0.95,
                        f"Exact location match ('{loc}') discovered in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                    )
                else:
                    sim = compute_string_similarity(norm_loc, te_norm)
                    if sim >= 0.85:
                        record_candidate_link(
                            te.case_id, src_ent, te, "address", "fuzzy_address", loc, round(sim, 3),
                            f"Fuzzy location match ({int(sim*100)}% similarity: '{loc}' vs '{te.name}') in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                        )

    # E. Check Digital Telemetry
    for dig_type, dig_val in exhibit_digital:
        for te in target_entities:
            te_dig = extract_digital_identifier(te.name)
            if te_dig and te_dig[0] == dig_type and te_dig[1].lower() == dig_val.lower():
                src_ent = next((se for se in source_entities if extract_digital_identifier(se.name) == te_dig), None)
                record_candidate_link(
                    te.case_id, src_ent, te, "digital", "exact_identifier", dig_val, 1.0,
                    f"Exact digital identifier match ({dig_type}: {dig_val}) discovered in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                )

    # F. Direct Text-Corpus Cross Matching against Known Target Entities (Pre-Entity Extraction)
    norm_corpus_person = normalize_person_name(corpus)
    norm_corpus_address = normalize_address(corpus)

    for te in target_entities:
        te_type = (te.type or "").lower()
        if te_type in PERSON_ENTITY_TYPES:
            te_norm = normalize_person_name(te.name)
            if len(te_norm) >= 3 and (te_norm in norm_corpus_person or te.name.lower() in corpus.lower()):
                record_candidate_link(
                    te.case_id, None, te, "person", "exact_name", te.name, 0.95,
                    f"Person identity '{te.name}' mentioned in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                )
        elif te_type in LOCATION_ENTITY_TYPES:
            te_norm = normalize_address(te.name)
            # Check full or main locality (e.g. before comma)
            te_base = normalize_address(te.name.split(',')[0]) if ',' in te.name else te_norm
            if len(te_base) >= 4 and (te_base in norm_corpus_address or te.name.lower() in corpus.lower()):
                record_candidate_link(
                    te.case_id, None, te, "address", "exact_name", te.name, 0.95,
                    f"Location '{te.name}' mentioned in exhibit '{exhibit_label}' matching Case #{te.case_id}."
                )

    if newly_created_links:
        db.commit()
        logger.info(f"[CrossCase] Real-time matching for exhibit '{exhibit_label}' flagged {len(newly_created_links)} candidate links.")

    return [
        {
            "id": l.id,
            "source_case_id": l.source_case_id,
            "target_case_id": l.target_case_id,
            "entity_type": l.entity_type,
            "match_value": l.match_value,
            "similarity_score": l.similarity_score,
            "status": l.status
        }
        for l in newly_created_links
    ]


def get_connected_cases_summary(
    case_id: int,
    user: User,
    db: Session
) -> Dict[str, Any]:
    """
    Returns an aggregated overview of all possibly connected and confirmed cases for `case_id`.

    STRICT RBAC ENFORCEMENT:
    Show that a link exists only to people who can open both cases.
    If the requesting user does not have permission to open the linked case,
    that link is completely omitted.
    """
    if not check_case_access(case_id, user, db, "read"):
        raise PermissionError("Access denied: You are not authorized to view this case.")

    accessible_ids = get_user_accessible_case_ids(user, db)

    # Query all links involving case_id
    links = db.query(CrossCaseEntityLink).filter(
        or_(
            CrossCaseEntityLink.source_case_id == case_id,
            CrossCaseEntityLink.target_case_id == case_id
        )
    ).all()

    # Group links by linked_case_id
    grouped_by_case: Dict[int, Dict[str, Any]] = {}
    for link in links:
        other_case_id = link.target_case_id if link.source_case_id == case_id else link.source_case_id

        # STRICT RBAC CHECK: User must be able to open the other case
        if accessible_ids is not None and other_case_id not in accessible_ids:
            continue

        if other_case_id not in grouped_by_case:
            other_case = db.query(Case).filter(Case.id == other_case_id).first()
            grouped_by_case[other_case_id] = {
                "linked_case_id": other_case_id,
                "linked_case_title": other_case.title if other_case else f"Case #{other_case_id}",
                "status": "confirmed",
                "has_pending_review": False,
                "highest_similarity_score": 0.0,
                "feature_types": set(),
                "matching_features": []
            }

        grp = grouped_by_case[other_case_id]
        if link.status == "pending_review":
            grp["has_pending_review"] = True
            grp["status"] = "pending_review"
        elif link.status == "rejected" and not grp["has_pending_review"] and grp["status"] != "confirmed":
            grp["status"] = "rejected"

        if link.similarity_score > grp["highest_similarity_score"]:
            grp["highest_similarity_score"] = link.similarity_score

        grp["feature_types"].add(link.entity_type)
        grp["matching_features"].append({
            "link_id": link.id,
            "entity_type": link.entity_type,
            "match_type": link.match_type,
            "match_value": link.match_value,
            "similarity_score": link.similarity_score,
            "confidence_reason": link.confidence_reason,
            "status": link.status
        })

    connected_cases_list = []
    pending_count = 0
    confirmed_count = 0

    for grp in grouped_by_case.values():
        grp["feature_types"] = sorted(list(grp["feature_types"]))
        if grp["has_pending_review"]:
            pending_count += 1
        elif grp["status"] == "confirmed":
            confirmed_count += 1
        connected_cases_list.append(grp)

    # Sort so cases with pending candidate reviews appear first
    connected_cases_list.sort(key=lambda x: (not x["has_pending_review"], -x["highest_similarity_score"]))

    return {
        "case_id": case_id,
        "total_connected_cases": len(connected_cases_list),
        "pending_candidates_count": pending_count,
        "confirmed_connections_count": confirmed_count,
        "connected_cases": connected_cases_list
    }

