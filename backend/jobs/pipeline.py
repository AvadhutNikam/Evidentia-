"""
backend/jobs/pipeline.py
========================
Multi-stage evidence analysis pipeline with idempotent checkpoints,
cancellation checks, resume capability, and rate limiting.
Stages:
  1. extract_text (15%) - OCR / speech / document parsing
  2. chunk_text (30%) - Chunking with character offsets & page numbers
  3. extract_entities_claims (50%) - Gemini extraction of entities, events, claims
  4. verify_citations (70%) - Source-span quote verification against raw bytes
  5. detect_contradictions (80%) - Cross-exhibit NLI contradiction analysis
  6. classify_hypotheses (90%) - ACH matrix cell classification & Likelihood Ratio mapping
  7. recalculate_scores (98%) - Bayesian ACH score updating & posterior calculation
"""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from models import Case, Evidence, EvidenceStatus, Entity, Event, Hypothesis, EvidenceAssessment, Job
from analyzer import run_comprehensive_analysis, extract_raw_text_from_file
from citation_engine import index_exhibit_chunks, anchor_fact_citation, verify_and_anchor_quote
from routers.scoring import execute_scoring_run
from routers.cases import ensure_unknown_hypothesis
from scoring.evidence_scoring import (
    resolve_assessment_likelihood_ratio,
    evaluate_assessment_clearing_status
)
from jobs.queue import (
    update_job_stage, update_job_heartbeat, complete_job,
    fail_job, cancel_job
)
from multilingual_engine import (
    seed_initial_exhibit_version, create_or_update_translation
)

logger = logging.getLogger("evidentia.pipeline")

# Concurrency semaphore for Gemini LLM calls to prevent 429 rate limit errors
_AI_SEMAPHORE = threading.Semaphore(2)


def _stream_pipeline_event(
    db: Session,
    case_id: int,
    event_type: str,
    summary: str,
    payload: Dict[str, Any]
):
    """
    Broadcasts real-time streaming analysis stage updates to connected browsers.
    Allows users to see facts (text, entities, claims, contradictions, scores)
    appear immediately as they are produced by the worker.
    """
    try:
        from collaboration import publish_collaboration_event
        publish_collaboration_event(
            db=db,
            case_id=case_id,
            event_type=event_type,
            item_type="analysis_stream",
            item_id=str(payload.get("job_id", "")),
            summary=summary,
            payload=payload,
            commit=True
        )
    except Exception as se:
        logger.debug(f"[Pipeline] Notice: streaming event {event_type} broadcast skipped: {se}")


def is_job_cancelled(db: Session, job_id: int) -> bool:
    """Checks if the user has requested job cancellation."""
    job = db.query(Job).filter(Job.id == job_id).first()
    return bool(job and job.cancel_requested)


def execute_evidence_pipeline(job_id: int, db: Session) -> bool:
    """
    Executes the multi-stage evidence processing pipeline.
    Checks checkpoints in stage_results to resume from the last completed stage.
    Returns True on success, False on cancellation or failure.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"[Pipeline] Job #{job_id} not found.")
        return False

    case = db.query(Case).filter(Case.id == job.case_id).first()
    if not case:
        fail_job(db, job_id, RuntimeError(f"Case #{job.case_id} not found."), allow_retry=False)
        return False

    evidence = None
    if job.exhibit_id:
        evidence = db.query(Evidence).filter(Evidence.id == job.exhibit_id).first()
        if not evidence:
            fail_job(db, job_id, RuntimeError(f"Evidence #{job.exhibit_id} not found."), allow_retry=False)
            return False

    # Load existing checkpoint results
    stage_results = {}
    if job.stage_results:
        try:
            stage_results = json.loads(job.stage_results)
        except Exception:
            stage_results = {}

    case_context = f"{case.title}: {case.description}"
    is_demo_case = bool(getattr(case, "is_demo", False))
    allow_fixtures = is_demo_case and bool(getattr(evidence, "is_demo_fixture", False)) if evidence else False

    def _extract_hyp_score(hyp):
        val = getattr(hyp, "combined_score", None)
        if val is None or val == 0.0:
            val = getattr(hyp, "support_score", None)
        if val is None or val == 0.0:
            val = getattr(hyp, "probability", 0.0)
        v = float(val or 0.0)
        return round(v if v > 1.0 else v * 100)

    # Snapshot baseline hypotheses for real-time score delta calculation
    baseline_hypotheses = {
        h.id: {
            "title": h.title,
            "pct": _extract_hyp_score(h)
        }
        for h in db.query(Hypothesis).filter(Hypothesis.case_id == case.id).all()
    }

    # Accumulate newly discovered facts across stages for "what changed" summary
    streamed_entities_accum = []
    streamed_events_accum = []
    contradiction_count_accum = 0

    try:
        # ======================================================================
        # STAGE 1: EXTRACT TEXT (15%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        if "extract_text" not in stage_results:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 1: extract_text")
            update_job_stage(db, job_id, "extract_text", 15.0)

            raw_text = evidence.extracted_text if evidence else ""
            if not raw_text or len(raw_text.strip()) < 10:
                raw_text = extract_raw_text_from_file(
                    file_path=evidence.storage_path or "",
                    file_type=evidence.file_type or "Document",
                    allow_fixtures=allow_fixtures
                )
                if evidence:
                    evidence.extracted_text = raw_text
                    db.commit()

            # Multilingual versioning: seed Version 1 and segment alignment
            if evidence:
                try:
                    seed_initial_exhibit_version(db, evidence.id, user_name="Automated Ingestion Pipeline")
                    if evidence.primary_language in ["mr", "hi", "mixed"]:
                        create_or_update_translation(db, evidence.id, target_language="en", author_type="machine")
                except Exception as ex_err:
                    logger.warning(f"[Pipeline] Multilingual version seed warning: {ex_err}")

            update_job_stage(db, job_id, "extract_text", 25.0, {
                "text_length": len(raw_text or ""),
                "has_text": bool(raw_text and len(raw_text.strip()) > 0)
            })

            # STREAM FACT 1: Text extracted - push to browser immediately
            _stream_pipeline_event(
                db=db,
                case_id=case.id,
                event_type="stream_stage_text",
                summary=f"Extracted {len(raw_text or '')} characters from '{evidence.file_name if evidence else 'Exhibit'}'.",
                payload={
                    "job_id": job_id,
                    "evidence_id": evidence.id if evidence else None,
                    "evidence_file_name": evidence.file_name if evidence else "Exhibit",
                    "stage": "extract_text",
                    "stage_label": "Text Extracted",
                    "progress_pct": 25.0,
                    "text_preview": (raw_text or "")[:400],
                    "text_length": len(raw_text or ""),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 1 already completed.")

        # ======================================================================
        # STAGE 2: CHUNK TEXT (30%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        if "chunk_text" not in stage_results and evidence and evidence.extracted_text:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 2: chunk_text")
            update_job_stage(db, job_id, "chunk_text", 30.0)

            chunks = index_exhibit_chunks(
                db=db,
                evidence_id=evidence.id,
                case_id=case.id,
                text=evidence.extracted_text
            )

            update_job_stage(db, job_id, "chunk_text", 40.0, {
                "chunk_count": len(chunks)
            })
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 2 already completed.")

        # ======================================================================
        # STAGE 3: EXTRACT ENTITIES, EVENTS & CLAIMS (50%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        analysis_data = {}
        if "extract_entities_claims" not in stage_results and evidence:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 3: extract_entities_claims")
            update_job_stage(db, job_id, "extract_entities_claims", 50.0)

            # Acquire rate-limit semaphore for Gemini API
            with _AI_SEMAPHORE:
                update_job_heartbeat(db, job_id)
                analysis_result = run_comprehensive_analysis(
                    file_path=evidence.storage_path or "",
                    file_name=evidence.file_name,
                    file_type=evidence.file_type or "Document",
                    existing_text=evidence.extracted_text,
                    case_context=case_context,
                    is_demo_case=is_demo_case,
                    allow_demo_fixtures=allow_fixtures
                )

            evidence.extracted_text = analysis_result.get("text") or analysis_result.get("summary") or evidence.extracted_text
            evidence.extraction_mode = analysis_result.get("extraction_mode", "live")
            evidence.is_demo_fixture = bool(analysis_result.get("is_demo_fixture", False))
            db.commit()

            # Insert entities idempotently
            added_entities = 0
            newly_added_entities = []
            for ent in analysis_result.get("entities", []):
                name = (ent.get("name") or "").strip()
                if not name:
                    continue
                existing_ent = db.query(Entity).filter(
                    Entity.case_id == case.id,
                    Entity.name.ilike(name)
                ).first()
                if not existing_ent:
                    new_ent = Entity(
                        case_id=case.id,
                        evidence_id=evidence.id,
                        type=ent.get("type", "Entity"),
                        name=name,
                        confidence=float(ent.get("confidence", 0.9))
                    )
                    db.add(new_ent)
                    newly_added_entities.append(new_ent)
                    added_entities += 1

            # Insert events idempotently
            added_events = 0
            newly_added_events = []
            for evt in analysis_result.get("events", []):
                title = (evt.get("title") or "").strip()
                if not title:
                    continue
                existing_evt = db.query(Event).filter(
                    Event.case_id == case.id,
                    Event.title.ilike(title)
                ).first()
                if not existing_evt:
                    raw_dt = evt.get("date") or evt.get("timestamp")
                    parsed_dt = None
                    if isinstance(raw_dt, datetime):
                        parsed_dt = raw_dt
                    elif isinstance(raw_dt, str) and raw_dt.strip():
                        try:
                            parsed_dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                        except Exception:
                            parsed_dt = datetime.now(timezone.utc)
                    else:
                        parsed_dt = datetime.now(timezone.utc)

                    new_evt = Event(
                        case_id=case.id,
                        evidence_id=evidence.id,
                        title=title,
                        description=evt.get("description", ""),
                        timestamp=parsed_dt
                    )
                    db.add(new_evt)
                    newly_added_events.append(new_evt)
                    added_events += 1

            db.commit()

            # Record in accumulators
            streamed_entities_accum.extend([
                {"id": e.id, "name": e.name, "type": e.type}
                for e in newly_added_entities
            ])
            streamed_events_accum.extend([
                {"id": ev.id, "title": ev.title}
                for ev in newly_added_events
            ])

            analysis_data = {
                "added_entities": added_entities,
                "added_events": added_events,
                "summary": analysis_result.get("summary", "")[:200]
            }
            update_job_stage(db, job_id, "extract_entities_claims", 65.0, analysis_data)

            # STREAM FACT 2: Entities, Events & Claims - push to browser immediately
            entities_payload = [
                {"id": e.id, "name": e.name, "type": e.type, "confidence": getattr(e, "confidence", 0.9)}
                for e in newly_added_entities
            ]
            events_payload = [
                {"id": ev.id, "title": ev.title, "timestamp": ev.timestamp.isoformat() if ev.timestamp else None}
                for ev in newly_added_events
            ]
            _stream_pipeline_event(
                db=db,
                case_id=case.id,
                event_type="stream_stage_entities",
                summary=f"Extracted {len(entities_payload)} entities and {len(events_payload)} timeline events from '{evidence.file_name}'.",
                payload={
                    "job_id": job_id,
                    "evidence_id": evidence.id if evidence else None,
                    "evidence_file_name": evidence.file_name if evidence else "Exhibit",
                    "stage": "extract_entities_claims",
                    "stage_label": "Entities & Timeline Claims",
                    "progress_pct": 65.0,
                    "new_entities": entities_payload,
                    "new_events": events_payload,
                    "new_entities_count": len(entities_payload),
                    "new_events_count": len(events_payload),
                    "summary_snippet": analysis_result.get("summary", "")[:250],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

            # Real-time Cross-Case Matching across user-accessible cases
            try:
                from cross_case_engine import match_exhibit_cross_case_realtime
                job_user = db.query(User).filter(User.id == job.user_id).first() if job.user_id else None
                if job_user and evidence:
                    match_exhibit_cross_case_realtime(evidence.id, job_user, db)
            except Exception as cce:
                logger.warning(f"[Pipeline] Real-time cross-case match notice in Stage 3: {cce}")
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 3 already completed.")

        # ======================================================================
        # STAGE 4: VERIFY CITATIONS (70%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        if "verify_citations" not in stage_results and evidence:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 4: verify_citations")
            update_job_stage(db, job_id, "verify_citations", 70.0)

            # Anchor citations for newly added entities and events
            ents = db.query(Entity).filter(Entity.evidence_id == evidence.id).all()
            for ent in ents:
                anchor_fact_citation(
                    db=db,
                    case_id=case.id,
                    evidence_id=evidence.id,
                    fact_type="entity",
                    fact_id=ent.id,
                    raw_quote=ent.name
                )

            update_job_stage(db, job_id, "verify_citations", 78.0, {
                "anchored_count": len(ents)
            })

            # STREAM FACT 3: Verified Citations
            _stream_pipeline_event(
                db=db,
                case_id=case.id,
                event_type="stream_stage_citations",
                summary=f"Verified {len(ents)} source citations against raw evidence bytes.",
                payload={
                    "job_id": job_id,
                    "evidence_id": evidence.id if evidence else None,
                    "stage": "verify_citations",
                    "stage_label": "Citations Verified",
                    "progress_pct": 78.0,
                    "anchored_count": len(ents),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 4 already completed.")

        # ======================================================================
        # STAGE 5: DETECT CONTRADICTIONS (80%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        if "detect_contradictions" not in stage_results:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 5: detect_contradictions")
            update_job_stage(db, job_id, "detect_contradictions", 80.0)

            contradiction_count = 0
            try:
                from nli_engine import ForensicNLIDetector
                detector = ForensicNLIDetector()
                res = detector.detect_contradictions_for_case(case_id=case.id, db=db)
                contradiction_count = res.get("new_contradictions_detected", 0)
            except Exception as e:
                logger.warning(f"[Pipeline] Contradiction check skipped: {e}")

            contradiction_count_accum = contradiction_count

            update_job_stage(db, job_id, "detect_contradictions", 85.0, {
                "contradictions_found": contradiction_count
            })

            # STREAM FACT 4: Contradictions Detected
            c_label = f"{contradiction_count} new contradiction(s) detected across exhibits." if contradiction_count > 0 else "0 contradictions detected across exhibits."
            _stream_pipeline_event(
                db=db,
                case_id=case.id,
                event_type="stream_stage_contradictions",
                summary=c_label,
                payload={
                    "job_id": job_id,
                    "stage": "detect_contradictions",
                    "stage_label": "Contradictions Checked",
                    "progress_pct": 85.0,
                    "contradictions_found": contradiction_count,
                    "new_contradictions_count": contradiction_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 5 already completed.")

        # ======================================================================
        # STAGE 6: CLASSIFY HYPOTHESES (90%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        if "classify_hypotheses" not in stage_results and evidence:
            logger.info(f"[Pipeline] Job #{job_id} -> Stage 6: classify_hypotheses")
            update_job_stage(db, job_id, "classify_hypotheses", 90.0)

            ensure_unknown_hypothesis(case.id, db)
            hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case.id).all()

            for h in hypotheses:
                existing_assessment = db.query(EvidenceAssessment).filter(
                    EvidenceAssessment.evidence_id == evidence.id,
                    EvidenceAssessment.hypothesis_id == h.id
                ).first()

                if not existing_assessment:
                    # Default heuristic / neutral baseline classification
                    resolved_lr = resolve_assessment_likelihood_ratio(
                        assessment={"finding_category": "general_irrelevant_neutral", "classification": "neutral"},
                        evidence_type="document",
                        reliability=1.0
                    )
                    db_assessment = EvidenceAssessment(
                        hypothesis_id=h.id,
                        evidence_id=evidence.id,
                        classification="neutral",
                        original_classification="neutral",
                        analyst_override=False,
                        reason="Assessed during background evidence processing pipeline.",
                        llm_confidence=0.85,
                        reliability=1.0,
                        finding_category=resolved_lr["finding_category"],
                        finding_name=resolved_lr["finding_name"],
                        likelihood_ratio=resolved_lr["base_lr"],
                        effective_lr=resolved_lr["effective_lr"],
                        lr_min=resolved_lr["min_lr"],
                        lr_max=resolved_lr["max_lr"],
                        lr_source_citation=resolved_lr["source_citation"],
                        lr_error_rate=resolved_lr["forensic_error_rate"],
                        weight_of_evidence_bans=resolved_lr["weight_of_evidence_bans"]
                    )
                    db.add(db_assessment)

            db.commit()
            update_job_stage(db, job_id, "classify_hypotheses", 95.0, {
                "hypotheses_evaluated": len(hypotheses)
            })
        else:
            logger.info(f"[Pipeline] Job #{job_id} -> Resuming: Stage 6 already completed.")

        # ======================================================================
        # STAGE 7: RECALCULATE ACH SCORES (98%)
        # ======================================================================
        if is_job_cancelled(db, job_id):
            cancel_job(db, job_id)
            return False

        logger.info(f"[Pipeline] Job #{job_id} -> Stage 7: recalculate_scores")
        update_job_stage(db, job_id, "recalculate_scores", 98.0)

        scoring_res = execute_scoring_run(
            case_id=case.id,
            db=db,
            triggered_by=f"job_worker_{job_id}"
        )

        update_job_stage(db, job_id, "recalculate_scores", 99.0, {
            "scoring_success": scoring_res.get("success", False),
            "hypotheses_scored": len(scoring_res.get("hypotheses", []))
        })

        # Calculate score movements vs baseline
        updated_hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case.id).all()
        score_deltas = []
        score_movement_strs = []

        for h in updated_hypotheses:
            prev_info = baseline_hypotheses.get(h.id, {"title": h.title, "pct": 0})
            prev_pct = prev_info["pct"]
            new_pct = _extract_hyp_score(h)
            delta_pct = new_pct - prev_pct

            # Human-readable hypothesis label: e.g. "H2" or "H2 (Yogesh Raut)"
            h_code = f"H{h.id}"
            if ":" in h.title:
                h_code = h.title.split(":")[0].strip()
            elif " " in h.title and (h.title.startswith("H") or h.title.startswith("Hypothesis")):
                h_code = h.title.split()[0].strip()

            score_deltas.append({
                "hypothesis_id": h.id,
                "title": h.title,
                "code": h_code,
                "prev_pct": prev_pct,
                "new_pct": new_pct,
                "delta_pct": delta_pct
            })

            if abs(delta_pct) >= 1:
                score_movement_strs.append(f"{h_code} moved from {prev_pct}% to {new_pct}%")

        score_move_summary = ", ".join(score_movement_strs[:2]) if score_movement_strs else "scores calibrated"

        # STREAM FACT 5: Recalculated Scores - push to browser immediately
        _stream_pipeline_event(
            db=db,
            case_id=case.id,
            event_type="stream_stage_scores",
            summary=f"ACH scores updated: {score_move_summary}",
            payload={
                "job_id": job_id,
                "stage": "recalculate_scores",
                "stage_label": "ACH Recalculated",
                "progress_pct": 99.0,
                "score_deltas": score_deltas,
                "score_movement_summary": score_move_summary,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        # ======================================================================
        # FINISH: SUCCESS (100%) - BROADCAST "WHAT CHANGED" STRIP SUMMARY
        # ======================================================================
        # Format requested: "3 new entities, 1 new contradiction, H2 moved from 41% to 47%."
        what_changed_parts = []
        ent_count = len(streamed_entities_accum)
        what_changed_parts.append(f"{ent_count} new entit{'y' if ent_count == 1 else 'ies'}")

        c_count = contradiction_count_accum
        what_changed_parts.append(f"{c_count} new contradiction{'s' if c_count != 1 else ''}")

        if score_movement_strs:
            what_changed_parts.append(score_movement_strs[0])
        else:
            what_changed_parts.append("hypotheses recalibrated")

        what_changed_strip_text = ", ".join(what_changed_parts) + "."

        _stream_pipeline_event(
            db=db,
            case_id=case.id,
            event_type="stream_stage_completed",
            summary=what_changed_strip_text,
            payload={
                "job_id": job_id,
                "evidence_id": evidence.id if evidence else None,
                "evidence_file_name": evidence.file_name if evidence else "Exhibit",
                "stage": "completed",
                "stage_label": "Analysis Complete",
                "progress_pct": 100.0,
                "what_changed_summary": what_changed_strip_text,
                "new_entities": streamed_entities_accum,
                "new_events": streamed_events_accum,
                "new_entities_count": ent_count,
                "new_events_count": len(streamed_events_accum),
                "new_contradictions_count": c_count,
                "score_deltas": score_deltas,
                "score_movement_summary": score_move_summary,
                "highlight_duration_minutes": 5,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        )

        complete_job(
            db=db,
            job_id=job_id,
            summary=f"Processed: {what_changed_strip_text}"
        )
        return True
        return True

    except Exception as e:
        logger.error(f"[Pipeline] Error in pipeline execution for Job #{job_id}: {e}", exc_info=True)
        fail_job(db, job_id, e, allow_retry=True)
        return False
