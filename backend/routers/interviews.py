"""
backend/routers/interviews.py
Interview & Deposition Analysis Router.
Provides:
- Suggested interrogation questions synthesized from contradictions, gaps, and unverified alibis.
- Storage of answers per interview session.
- Real-time claim comparison against earlier statements and case exhibits.
- Immediate flagging of new contradictions with dual-quote linking.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from sqlalchemy.orm import Session

from database import get_db
from models import Case, User, Interview, InterviewStatement, InterviewContradiction
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from schemas import (
    InterviewOut, InterviewDetailOut, InterviewCreateRequest,
    InterviewStatementOut, InterviewStatementCreateRequest,
    InterviewContradictionOut, SuggestedQuestionOut,
    StatementAnalysisResponse
)
from interview_engine import (
    suggest_interview_questions,
    ensure_case_interviews,
    record_and_analyze_statement
)
from audit_engine import log_audit_event
from collaboration import publish_collaboration_event

router = APIRouter(tags=["Interviews & Depositions"])
logger = logging.getLogger("evidentia.interviews")


def _format_interview_out(interview: Interview, db: Session) -> Dict[str, Any]:
    stmt_count = db.query(InterviewStatement).filter(InterviewStatement.interview_id == interview.id).count()
    contra_count = db.query(InterviewContradiction).filter(InterviewContradiction.interview_id == interview.id).count()
    return {
        "id": interview.id,
        "case_id": interview.case_id,
        "session_code": interview.session_code,
        "interviewee_name": interview.interviewee_name,
        "interviewee_role": interview.interviewee_role,
        "interviewer_name": interview.interviewer_name,
        "interview_date": interview.interview_date,
        "duration": interview.duration,
        "status": interview.status,
        "audio_url": interview.audio_url,
        "notes": interview.notes,
        "created_at": interview.created_at,
        "updated_at": interview.updated_at,
        "statement_count": stmt_count,
        "contradiction_count": contra_count
    }


@router.get("/cases/{case_id}/interviews", response_model=List[InterviewOut])
def get_case_interviews(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all interview and deposition recordings for the case.
    Initializes case interview seeds if none exist yet.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    # Ensure interviews exist for this case
    interviews = ensure_case_interviews(real_case_id, db)
    return [_format_interview_out(i, db) for i in interviews]


@router.post("/cases/{case_id}/interviews", response_model=InterviewOut)
def create_case_interview(
    case_id: str,
    payload: InterviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new interview or deposition recording session for a witness/suspect.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied: Read-only accounts cannot create interviews.")

    existing_count = db.query(Interview).filter(Interview.case_id == real_case_id).count()
    session_code = f"REC-{real_case_id}-{existing_count + 1:03d}"

    interview = Interview(
        case_id=real_case_id,
        session_code=session_code,
        interviewee_name=payload.interviewee_name.strip(),
        interviewee_role=payload.interviewee_role or "suspect",
        interviewer_name=payload.interviewer_name.strip(),
        interview_date=payload.interview_date or datetime.now(timezone.utc).strftime("%b %d, %Y"),
        duration=payload.duration or "00:00 mins",
        status=payload.status or "Active",
        notes=payload.notes
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    log_audit_event(
        db=db,
        action_type="INTERVIEW_CREATED",
        target_type="interview",
        target_id=str(interview.id),
        description=f"Created interview session {session_code} for {interview.interviewee_name} ({interview.interviewee_role})",
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        case_id=real_case_id
    )

    return _format_interview_out(interview, db)


@router.get("/cases/{case_id}/interviews/suggested-questions", response_model=List[SuggestedQuestionOut])
def get_suggested_interview_questions(
    case_id: str,
    interviewee_name: Optional[str] = Query(None, description="Filter suggestions by subject name"),
    interview_id: Optional[int] = Query(None, description="Interview session ID context"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggests high-yield interrogation questions dynamically synthesized from:
    1. Contradictions between witness statements, alibis, and case exhibits.
    2. Case investigative gaps (unverified timeline windows, uncorroborated claims).
    3. Unverified alibis and suspect prior record conflicts.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    questions = suggest_interview_questions(
        case_id=real_case_id,
        interviewee_name=interviewee_name,
        interview_id=interview_id,
        db=db
    )
    return questions


@router.get("/cases/{case_id}/interviews/{interview_id}", response_model=InterviewDetailOut)
def get_interview_detail(
    case_id: str,
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves complete interview transcript, statements, and flagged contradictions.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.case_id == real_case_id
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview recording not found.")

    statements = (
        db.query(InterviewStatement)
        .filter(InterviewStatement.interview_id == interview_id)
        .order_by(InterviewStatement.sequence_order.asc())
        .all()
    )

    contradictions = (
        db.query(InterviewContradiction)
        .filter(InterviewContradiction.interview_id == interview_id)
        .order_by(InterviewContradiction.created_at.asc())
        .all()
    )

    out_data = _format_interview_out(interview, db)
    out_data["statements"] = statements
    out_data["contradictions"] = contradictions
    return out_data


@router.post("/cases/{case_id}/interviews/{interview_id}/statements", response_model=StatementAnalysisResponse)
def add_statement_and_analyze(
    case_id: str,
    interview_id: int,
    payload: InterviewStatementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records an answer or statement for the interview session.
    Immediately executes claim comparison against prior statements in the case and forensic exhibits.
    Flags any contradiction immediately, linking both quotes and storing forensic reasoning.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied: Read-only accounts cannot record interview statements.")

    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.case_id == real_case_id
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview recording not found.")

    try:
        result = record_and_analyze_statement(
            interview_id=interview_id,
            payload=payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
            db=db,
            user=current_user
        )

        # Broadcast live statement and any detected contradiction over SSE
        try:
            publish_collaboration_event(
                db=db,
                case_id=real_case_id,
                event_type="interview.statement_contradiction" if result.get("has_contradiction") else "interview.live_statement",
                item_type="interview_statement",
                item_id=str(result["statement"]["id"]),
                user_id=current_user.id,
                user_name=current_user.full_name,
                summary=f"{result['statement']['speaker']}: {result['statement']['text'][:80]}" + (" [CONTRADICTION FLAG]" if result.get("has_contradiction") else ""),
                payload={
                    "interview_id": interview_id,
                    "statement": result["statement"],
                    "has_contradiction": result.get("has_contradiction", False),
                    "new_contradictions": result.get("new_contradictions", [])
                }
            )
        except Exception as b_err:
            logger.debug(f"Interview statement SSE broadcast non-fatal exception: {b_err}")

        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to record and analyze interview statement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.post("/cases/{case_id}/interviews/{interview_id}/live-stream-chunk", response_model=StatementAnalysisResponse)
async def stream_live_interview_chunk(
    case_id: str,
    interview_id: int,
    transcript_text: str = Form(...),
    speaker: Optional[str] = Form(None),
    role: Optional[str] = Form("interviewee"),
    timestamp_marker: Optional[str] = Form("00:00"),
    seconds: Optional[int] = Form(0),
    question: Optional[str] = Form(None),
    question_source_type: Optional[str] = Form(None),
    question_source_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Live Interview Streaming & Continuous Transcription Ingestion:
    Accepts rolling speech chunks as words are spoken during an ongoing interview.
    Executes real-time claim comparison against prior statements, case alibis, and forensic exhibits.
    Immediately flags any contradictions while the interview is actively taking place.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied: Read-only accounts cannot stream live interview statements.")

    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.case_id == real_case_id
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview recording not found.")

    clean_text = transcript_text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Transcript text cannot be empty.")

    payload_dict = {
        "speaker": speaker or interview.interviewee_name,
        "role": role or "interviewee",
        "timestamp_marker": timestamp_marker or "00:00",
        "seconds": seconds or 0,
        "question": question,
        "question_source_type": question_source_type,
        "question_source_id": question_source_id,
        "text": clean_text,
        "tag": "Live Audio Stream"
    }

    try:
        result = record_and_analyze_statement(
            interview_id=interview_id,
            payload=payload_dict,
            db=db,
            user=current_user
        )

        try:
            publish_collaboration_event(
                db=db,
                case_id=real_case_id,
                event_type="interview.statement_contradiction" if result.get("has_contradiction") else "interview.live_statement",
                item_type="interview_statement",
                item_id=str(result["statement"]["id"]),
                user_id=current_user.id,
                user_name=current_user.full_name,
                summary=f"Live Interview Stream: {result['statement']['speaker']} @ {timestamp_marker}: {clean_text[:60]}" + (" [CONTRADICTION DETECTED!]" if result.get("has_contradiction") else ""),
                payload={
                    "interview_id": interview_id,
                    "statement": result["statement"],
                    "has_contradiction": result.get("has_contradiction", False),
                    "new_contradictions": result.get("new_contradictions", [])
                }
            )
        except Exception as b_err:
            logger.debug(f"Interview live stream SSE broadcast non-fatal exception: {b_err}")

        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Live interview streaming analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Streaming analysis error: {str(e)}")


@router.get("/cases/{case_id}/interviews/{interview_id}/contradictions", response_model=List[InterviewContradictionOut])
def get_interview_contradictions(
    case_id: str,
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all contradictions flagged during this interview session with linked quotes.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    contradictions = (
        db.query(InterviewContradiction)
        .filter(
            InterviewContradiction.interview_id == interview_id,
            InterviewContradiction.case_id == real_case_id
        )
        .order_by(InterviewContradiction.created_at.desc())
        .all()
    )
    return contradictions

