"""
backend/routers/common.py
Shared router utility functions and entity resolvers.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from models import Case, Evidence


def resolve_case_id(case_id_val, db: Session) -> int:
    """Resolves an integer ID, slug, or alias to a database Case ID."""
    try:
        return int(case_id_val)
    except (ValueError, TypeError):
        pass
    s = str(case_id_val).lower().strip()
    alias_map = {
        "fir-2009-mh-pun-534": 1,
        "cr-2024-mh-pun-0042": 2,
        "fir-2023-ka-blr-0891": 3,
        "op-blackout-2024-w": 4,
        "cbi-2008-up-noi-001": 5,
        "bpd-2013-ma-bos-0415": 6,
    }
    if s in alias_map:
        return alias_map[s]
    for c in db.query(Case).all():
        if s in c.title.lower() or (c.description and s in c.description.lower()):
            return c.id
    return -1


def resolve_evidence_obj(evidence_id: str, db: Session) -> Optional[Evidence]:
    """Finds evidence by integer ID or filename/code match."""
    str_id = str(evidence_id).strip()
    try:
        num = int(str_id)
        ev = db.query(Evidence).filter(Evidence.id == num).first()
        if ev:
            return ev
    except ValueError:
        pass
    
    # Try exact or partial filename match
    ev = db.query(Evidence).filter(Evidence.file_name.ilike(f"%{str_id}%")).first()
    if ev:
        return ev
    return None


def parse_date_safely(date_val) -> datetime:
    """Safely converts ISO string or timestamp to UTC datetime object."""
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        try:
            return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(date_val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
    return datetime.now(timezone.utc)

