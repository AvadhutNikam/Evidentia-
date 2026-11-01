"""
backend/routers/voice_notes.py
Investigator Quick Voice Notes & Judicial Source-Span Citation Router.
"""

import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from schemas import VoiceNoteOut
from voice_notes_engine import create_voice_note, get_case_voice_notes

logger = logging.getLogger("evidentia.voice_notes")
router = APIRouter(tags=["Quick Voice Notes & Citations"])


@router.post("/cases/{case_id}/voice-notes", response_model=VoiceNoteOut)
async def create_case_voice_note(
    case_id: str,
    note_text: str = Form(...),
    category: Optional[str] = Form("field_observation"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    accuracy_meters: Optional[float] = Form(None),
    location_name: Optional[str] = Form(None),
    recorded_at: Optional[str] = Form(None),
    source_device: Optional[str] = Form("Mobile Field Unit"),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingests a quick investigator voice memo or field dictation.
    Anchors source-span citations, records GPS and timestamp, logs Chain of Custody (FIELD_VOICE_NOTE),
    runs real-time cross-case matching on dictated entities/plates/numbers,
    and returns a cited case note handle [Voice Note #XX, Para 1].
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(
            status_code=403,
            detail=f"User role '{current_user.role}' is not authorized to record field voice notes."
        )

    audio_bytes = None
    audio_name = None
    if audio_file:
        try:
            audio_bytes = await audio_file.read()
            audio_name = audio_file.filename
        except Exception as e:
            logger.warning(f"Could not read audio file bytes: {e}")

    try:
        note_out = await create_voice_note(
            case_id=real_case_id,
            note_text=note_text,
            current_user=current_user,
            db=db,
            category=category or "field_observation",
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
            location_name=location_name,
            recorded_at=recorded_at,
            audio_bytes=audio_bytes,
            audio_filename=audio_name,
            source_device=source_device
        )
        return note_out
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record voice note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record voice note: {str(e)}")


@router.get("/cases/{case_id}/voice-notes", response_model=List[VoiceNoteOut])
def get_case_voice_notes_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all cited voice notes for this case docket.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return get_case_voice_notes(real_case_id, db)

