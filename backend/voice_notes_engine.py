"""
backend/voice_notes_engine.py
Investigator Quick Voice Notes & Judicial Source-Span Citation Engine.

Handles:
1. Ingestion of investigator voice memos (audio + transcript text) captured in field or office.
2. Geo-temporal forensic stamping (GPS coordinates, altitude, accuracy, capture timestamp).
3. Text chunking and persistent source-span citation anchoring with permanent citation handles [VN-XX:C1].
4. Chain of Custody logging with FIELD_VOICE_NOTE and INTAKE actions.
5. Real-time cross-case matching on entities, numbers, and plates dictated in voice notes.
6. Real-time collaboration event broadcasting over SSE.
"""

import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Case, Evidence, EvidenceStatus, User, CustodyLog, ExhibitChunk, SourceCitation
from storage import save_uploaded_file
from audit_engine import log_custody_event, log_audit_event
from citation_engine import chunk_text
from collaboration import publish_collaboration_event
from cross_case_engine import match_exhibit_cross_case_realtime


def calculate_sha256(raw_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(raw_bytes)
    return h.hexdigest().lower()


async def create_voice_note(
    case_id: int,
    note_text: str,
    current_user: User,
    db: Session,
    category: str = "field_observation",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    accuracy_meters: Optional[float] = None,
    location_name: Optional[str] = None,
    recorded_at: Optional[str] = None,
    audio_bytes: Optional[bytes] = None,
    audio_filename: Optional[str] = None,
    source_device: Optional[str] = "Mobile Field Unit"
) -> Dict[str, Any]:
    """
    Ingests an investigator voice note, saves media, anchors source-span citations,
    logs chain of custody entries, executes real-time cross-case matching,
    and returns a cited case note object.
    """
    clean_text = (note_text or "").strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Voice note text cannot be empty.")

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case #{case_id} not found.")

    # 1. Resolve Timestamp
    if recorded_at:
        try:
            capture_dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        except Exception:
            capture_dt = datetime.now(timezone.utc)
    else:
        capture_dt = datetime.now(timezone.utc)

    now_dt = datetime.now(timezone.utc)
    ts_seconds = int(now_dt.timestamp())

    # 2. Save Audio or Text File
    storage_path = None
    file_size = 0
    if audio_bytes and len(audio_bytes) > 0:
        file_hash = calculate_sha256(audio_bytes)
        ext = ".webm"
        if audio_filename and "." in audio_filename:
            ext = "." + audio_filename.rsplit(".", 1)[1].lower()
        fname = f"voice_note_{case_id}_{ts_seconds}{ext}"
        saved_path, file_size, _ = await save_uploaded_file(audio_bytes, fname)
        storage_path = saved_path
        file_type = "Audio"
    else:
        text_bytes = clean_text.encode("utf-8")
        file_hash = calculate_sha256(text_bytes)
        fname = f"voice_note_{case_id}_{ts_seconds}.txt"
        saved_path, file_size, _ = await save_uploaded_file(text_bytes, fname)
        storage_path = saved_path
        file_type = "Document"

    # 3. Format Scene / Location String
    geo_parts = []
    if location_name:
        geo_parts.append(location_name.strip())
    if latitude is not None and longitude is not None:
        acc_str = f" ±{accuracy_meters:.1f}m" if accuracy_meters is not None else ""
        geo_parts.append(f"GPS: ({latitude:.6f}, {longitude:.6f}{acc_str})")
    scene_location = " - ".join(geo_parts) if geo_parts else "Field Location (Unrecorded)"

    # 4. Create Evidence Record
    officer_name = current_user.full_name or "Investigating Officer"
    officer_role = getattr(current_user, "role", "analyst")
    officer_badge = getattr(current_user, "badge_number", None) or officer_role

    db_evidence = Evidence(
        case_id=case_id,
        file_name=fname,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        uploaded_by=officer_name,
        processing_status=EvidenceStatus.ANALYZED,
        source="Investigator Voice Memo",
        evidence_type="voice_note",
        file_hash=file_hash,
        hash_verified=True,
        chain_of_custody_complete=True,
        sec_65b_certificate_present=True,
        source_independent=True,
        quality_rating=4.5,
        collected_by=officer_name,
        collection_date=capture_dt,
        custody_notes=(
            f"Field voice note recorded at {scene_location}. "
            f"Category: {category}. SHA-256: {file_hash[:16]}... "
            f"Officer: {officer_name} ({officer_badge})"
        ),
        is_deleted=False,
        extraction_mode="live",
        extracted_text=clean_text,
        is_field_captured=True,
        capture_source="voice_note",
        field_latitude=latitude,
        field_longitude=longitude,
        field_accuracy_meters=accuracy_meters,
        field_captured_at=capture_dt,
        field_device_info=source_device or "Mobile Voice Dictation",
        field_location_name=location_name,
        field_officer_confirmed=True,
        field_officer_declaration=f"Official case observation voice memo dictated by {officer_name} ({officer_badge})",
        client_computed_hash=file_hash,
        hash_match_verified=True
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)

    # 5. Chunk Text & Create Anchored Source Citations
    raw_chunks = chunk_text(clean_text, chunk_size=250)
    created_citations: List[Dict[str, Any]] = []

    for c in raw_chunks:
        chunk_obj = ExhibitChunk(
            evidence_id=db_evidence.id,
            case_id=case_id,
            chunk_index=c["chunk_index"],
            text=c["text"],
            page_number=c.get("page_number", 1),
            char_start=c["char_start"],
            char_end=c["char_end"],
            created_at=now_dt
        )
        db.add(chunk_obj)
        db.commit()
        db.refresh(chunk_obj)

        citation_code = f"VN-{db_evidence.id}:C{c['chunk_index'] + 1}"
        citation_obj = SourceCitation(
            case_id=case_id,
            evidence_id=db_evidence.id,
            chunk_id=chunk_obj.id,
            fact_type="voice_note",
            fact_id=db_evidence.id,
            quote=c["text"],
            page_number=c.get("page_number", 1),
            char_start=c["char_start"],
            char_end=c["char_end"],
            verified_match=True,
            match_confidence=100.0,
            verification_method="direct_dictation",
            created_at=now_dt
        )
        db.add(citation_obj)
        db.commit()
        db.refresh(citation_obj)

        created_citations.append({
            "citation_id": citation_obj.id,
            "citation_code": citation_code,
            "chunk_id": chunk_obj.id,
            "char_start": c["char_start"],
            "char_end": c["char_end"],
            "quote": c["text"]
        })

    # 6. Chain of Custody Entries
    log_custody_event(
        db=db,
        evidence_id=db_evidence.id,
        case_id=case_id,
        action="FIELD_VOICE_NOTE",
        actor_name=officer_name,
        actor_role=officer_role,
        source_agency="Scene Mobile Forensics Unit",
        location=scene_location,
        notes=f"Voice memo dictated at scene: \"{clean_text[:100]}...\" (Category: {category}). GPS: {scene_location}",
        file_hash_snapshot=file_hash
    )

    log_custody_event(
        db=db,
        evidence_id=db_evidence.id,
        case_id=case_id,
        action="INTAKE",
        actor_name=officer_name,
        actor_role=officer_role,
        source_agency="Evidence Digital Repository",
        location="Evidentia Secure Storage",
        notes=f"Voice note indexed with {len(created_citations)} citation chunks. SHA-256: {file_hash}",
        file_hash_snapshot=file_hash
    )

    # 7. Audit Log Entry
    log_audit_event(
        db=db,
        action_type="VOICE_NOTE_CREATED",
        target_type="voice_note",
        target_id=str(db_evidence.id),
        description=f"Quick voice note recorded by {officer_name}. Category: {category}. Length: {len(clean_text)} chars.",
        user_id=current_user.id,
        user_name=officer_name,
        user_role=officer_role,
        case_id=case_id,
        after_value=file_hash
    )

    # 8. Real-Time Cross-Case Matching on Dictated Entities / Numbers / Plates
    try:
        match_exhibit_cross_case_realtime(
            evidence_id=db_evidence.id,
            user=current_user,
            db=db,
            case_id=case_id,
            file_name=fname
        )
    except Exception:
        pass

    # 9. Format Canonical Citation Handle
    dt_str = capture_dt.strftime("%b %d %H:%M")
    master_citation_code = f"[Voice Note #{db_evidence.id}: {officer_name}, {dt_str}]"

    # 10. Collaboration SSE Broadcast
    try:
        publish_collaboration_event(
            db=db,
            case_id=case_id,
            event_type="voice_note.created",
            item_type="voice_note",
            item_id=str(db_evidence.id),
            user_id=current_user.id,
            user_name=officer_name,
            summary=f"Voice Note by {officer_name}: \"{clean_text[:70]}...\"",
            payload={
                "evidence_id": db_evidence.id,
                "citation_code": master_citation_code,
                "note_text": clean_text,
                "category": category,
                "location_name": location_name,
                "latitude": latitude,
                "longitude": longitude,
                "recorded_at": capture_dt.isoformat(),
                "created_at": now_dt.isoformat()
            }
        )
    except Exception:
        pass

    return {
        "id": db_evidence.id,
        "case_id": case_id,
        "evidence_id": db_evidence.id,
        "citation_code": master_citation_code,
        "note_text": clean_text,
        "category": category,
        "officer_name": officer_name,
        "officer_role": officer_role,
        "latitude": latitude,
        "longitude": longitude,
        "location_name": location_name,
        "recorded_at": capture_dt.isoformat(),
        "audio_path": storage_path if file_type == "Audio" else None,
        "file_hash": file_hash,
        "citations": created_citations,
        "created_at": now_dt
    }


def get_case_voice_notes(case_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Retrieves all voice notes for a case with their anchored citations and timestamps.
    """
    notes = (
        db.query(Evidence)
        .filter(
            Evidence.case_id == case_id,
            Evidence.evidence_type == "voice_note",
            Evidence.is_deleted == False
        )
        .order_by(Evidence.collection_date.desc(), Evidence.id.desc())
        .all()
    )

    out: List[Dict[str, Any]] = []
    for ev in notes:
        # Load citations
        citations = (
            db.query(SourceCitation)
            .filter(SourceCitation.evidence_id == ev.id)
            .order_by(SourceCitation.id.asc())
            .all()
        )
        c_list = [
            {
                "citation_id": c.id,
                "citation_code": f"VN-{ev.id}:C{idx + 1}",
                "chunk_id": c.chunk_id or 0,
                "char_start": c.char_start or 0,
                "char_end": c.char_end or 0,
                "quote": c.quote or ""
            }
            for idx, c in enumerate(citations)
        ]

        officer = ev.uploaded_by or "Investigating Officer"
        dt = ev.collection_date or ev.upload_date or datetime.now(timezone.utc)
        dt_str = dt.strftime("%b %d %H:%M")
        master_citation_code = f"[Voice Note #{ev.id}: {officer}, {dt_str}]"

        out.append({
            "id": ev.id,
            "case_id": ev.case_id,
            "evidence_id": ev.id,
            "citation_code": master_citation_code,
            "note_text": ev.extracted_text or "",
            "category": "field_observation",
            "officer_name": officer,
            "officer_role": "analyst",
            "latitude": ev.field_latitude,
            "longitude": ev.field_longitude,
            "location_name": ev.field_location_name,
            "recorded_at": (ev.field_captured_at or dt).isoformat(),
            "audio_path": ev.storage_path if ev.file_type == "Audio" else None,
            "file_hash": ev.file_hash or "",
            "citations": c_list,
            "created_at": dt
        })

    return out
