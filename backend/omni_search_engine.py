"""
backend/omni_search_engine.py
Unified Cross-Corpus Omni-Search & Command Palette Indexer.

Finds across:
1. Exhibits & Text Passages (Original text, normalized text, and judicial translations).
2. Quotes & Source-Span Citations (Chunk level, exact quotes, page numbers).
3. Entities (Persons, locations, vehicles, phone numbers, aliases).
4. Claims & Competing Hypotheses (Assessments, rationale, hypothesis descriptions).
5. Suspects & Background Records (Motive, access, alibi, prior criminal history).
6. Investigation Tasks (Next-best steps, assignees, priorities).
7. Case Alerts & Statutory Deadlines (Urgent warnings, limitation countdowns).

Returns exact source attribution, character offsets for deep-linking,
and highlighted context snippets.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from models import (
    Case, Evidence, Entity, Hypothesis, EvidenceAssessment,
    SourceCitation, ExhibitChunk, SuspectProfileFactor, PriorRecord,
    InvestigationTask, Alert, CaseDeadline, ExhibitTranslation, TranslationSegment
)
from multilingual_engine import normalize_multilingual_text, NAME_TRANSLITERATION_MAP, REVERSE_NAME_MAP


def extract_highlighted_snippet(
    text: Optional[str],
    query: str,
    context_chars: int = 65
) -> Tuple[str, int, int]:
    """
    Locates the query occurrence within text and returns a bounded snippet
    with exact character offsets for document deep-linking.
    """
    if not text or not query:
        return ("", 0, 0)

    clean_text = text.strip()
    lower_text = clean_text.lower()
    lower_q = query.lower()

    idx = lower_text.find(lower_q)
    if idx == -1:
        # Fallback to token search if multi-word
        tokens = [t for t in lower_q.split() if len(t) >= 3]
        for token in tokens:
            idx = lower_text.find(token)
            if idx != -1:
                break

    if idx == -1:
        # No direct substring match, return beginning of text
        snippet = clean_text[:context_chars * 2] + ("..." if len(clean_text) > context_chars * 2 else "")
        return (snippet, 0, min(len(clean_text), 50))

    start = max(0, idx - context_chars)
    end = min(len(clean_text), idx + len(query) + context_chars)

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean_text) else ""

    snippet = prefix + clean_text[start:end] + suffix
    return (snippet, idx, idx + len(query))


def search_case_omni(
    db: Session,
    case_id: int,
    query: str,
    category_filter: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Conducts high-speed cross-table omni-search across all 7 evidentiary and operational dimensions.
    """
    clean_q = query.strip()
    if not clean_q or len(clean_q) < 1:
        return []

    lower_q = clean_q.lower()
    norm_q = normalize_multilingual_text(clean_q)

    # Transliteration expansion variants
    translit_terms = [clean_q, norm_q]
    if clean_q in NAME_TRANSLITERATION_MAP:
        translit_terms.append(NAME_TRANSLITERATION_MAP[clean_q])
    if lower_q in REVERSE_NAME_MAP:
        translit_terms.append(REVERSE_NAME_MAP[lower_q])

    results: List[Dict[str, Any]] = []

    # ==========================================================================
    # 1. EXHIBITS & PASSAGES (Original, Normalized, Translations)
    # ==========================================================================
    if not category_filter or category_filter in ["all", "exhibit", "passage"]:
        exhibits = (
            db.query(Evidence)
            .filter(Evidence.case_id == case_id, Evidence.is_deleted == False)
            .all()
        )

        for ex in exhibits:
            raw_text = ex.extracted_text or ""
            norm_text = normalize_multilingual_text(raw_text)
            file_name = ex.file_name or f"Exhibit #{ex.id}"

            # Check latest translation if available
            translation = (
                db.query(ExhibitTranslation)
                .filter(ExhibitTranslation.evidence_id == ex.id)
                .order_by(ExhibitTranslation.id.desc())
                .first()
            )
            trans_text = translation.full_translated_text if translation else ""

            matched_source = None
            matched_snippet = None
            char_start = 0
            char_end = 0

            # A. Verbatim in original extracted text
            if lower_q in raw_text.lower():
                matched_source = "Exhibit Original Text"
                matched_snippet, char_start, char_end = extract_highlighted_snippet(raw_text, clean_q)
            # B. In normalized text
            elif norm_q in norm_text:
                matched_source = "Exhibit Normalized Script"
                matched_snippet, char_start, char_end = extract_highlighted_snippet(norm_text, norm_q)
            # C. In translation (e.g. Marathi / Hindi -> English)
            elif trans_text and lower_q in trans_text.lower():
                src_lang = translation.source_language.upper() if translation else "REGIONAL"
                matched_source = f"Exhibit Translation ({src_lang} -> EN)"
                matched_snippet, char_start, char_end = extract_highlighted_snippet(trans_text, clean_q)
            # D. Transliterated proper name variants
            elif any(t.lower() in raw_text.lower() or t in norm_text for t in translit_terms[1:]):
                matched_source = "Exhibit Transliteration Variant"
                matched_snippet, char_start, char_end = extract_highlighted_snippet(raw_text, translit_terms[-1])
            # E. Filename or title match
            elif lower_q in file_name.lower():
                matched_source = "Exhibit Metadata (Filename)"
                matched_snippet = f"Exhibit File: {file_name} ({ex.evidence_type or 'document'})"

            if matched_source:
                results.append({
                    "id": f"exhibit-{ex.id}",
                    "category": "exhibit",
                    "title": file_name,
                    "match_source": matched_source,
                    "matched_snippet": matched_snippet or "",
                    "highlight_term": clean_q,
                    "char_start": char_start,
                    "char_end": char_end,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/evidence/{ex.id}?highlight={clean_q}&char_start={char_start}",
                    "metadata": {
                        "evidence_id": ex.id,
                        "file_type": ex.file_type,
                        "evidence_type": ex.evidence_type,
                        "language": ex.primary_language
                    }
                })

    # ==========================================================================
    # 2. QUOTES & SOURCE CITATIONS (Chunk-Level Precision)
    # ==========================================================================
    if not category_filter or category_filter in ["all", "quote", "citation"]:
        citations = (
            db.query(SourceCitation)
            .filter(SourceCitation.case_id == case_id)
            .all()
        )
        for cit in citations:
            quote_text = cit.quote or ""
            if lower_q in quote_text.lower():
                snippet, cs, ce = extract_highlighted_snippet(quote_text, clean_q)
                results.append({
                    "id": f"quote-{cit.id}",
                    "category": "quote",
                    "title": f"Direct Quote [{cit.fact_type.capitalize()}]",
                    "match_source": f"Source Citation (Exhibit #{cit.evidence_id}{f', Page {cit.page_number}' if cit.page_number else ''})",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": cit.char_start or cs,
                    "char_end": cit.char_end or ce,
                    "page_number": cit.page_number,
                    "target_url": f"/cases/{case_id}/evidence/{cit.evidence_id}?highlight={clean_q}&chunk={cit.chunk_id or ''}",
                    "metadata": {
                        "citation_id": cit.id,
                        "evidence_id": cit.evidence_id,
                        "fact_type": cit.fact_type,
                        "page": cit.page_number
                    }
                })

        # Search exhibit chunks directly if citations missed it
        chunks = (
            db.query(ExhibitChunk)
            .filter(ExhibitChunk.case_id == case_id)
            .all()
        )
        for chk in chunks:
            chk_text = chk.text or ""
            if lower_q in chk_text.lower():
                snippet, cs, ce = extract_highlighted_snippet(chk_text, clean_q)
                results.append({
                    "id": f"chunk-{chk.id}",
                    "category": "quote",
                    "title": f"Exhibit Passage (Chunk #{chk.chunk_index})",
                    "match_source": f"Exhibit Chunk (Exhibit #{chk.evidence_id}{f', Page {chk.page_number}' if chk.page_number else ''})",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": chk.char_start + cs,
                    "char_end": chk.char_start + ce,
                    "page_number": chk.page_number,
                    "target_url": f"/cases/{case_id}/evidence/{chk.evidence_id}?highlight={clean_q}&chunk={chk.id}",
                    "metadata": {
                        "chunk_id": chk.id,
                        "evidence_id": chk.evidence_id,
                        "chunk_index": chk.chunk_index,
                        "page": chk.page_number
                    }
                })

    # ==========================================================================
    # 3. ENTITIES (Suspects, Vehicles, Locations, Callers)
    # ==========================================================================
    if not category_filter or category_filter in ["all", "entity"]:
        entities = (
            db.query(Entity)
            .filter(Entity.case_id == case_id)
            .all()
        )
        for ent in entities:
            ent_name = ent.name or ""
            ent_quote = ent.source_quote or ""
            if lower_q in ent_name.lower() or (ent_quote and lower_q in ent_quote.lower()):
                snippet = f"Entity '{ent_name}' of type {ent.type or 'person'}."
                if ent_quote and lower_q in ent_quote.lower():
                    snippet, _, _ = extract_highlighted_snippet(ent_quote, clean_q)

                target = f"/cases/{case_id}/entities?search={clean_q}"
                if ent.evidence_id:
                    target = f"/cases/{case_id}/evidence/{ent.evidence_id}?highlight={clean_q}"

                results.append({
                    "id": f"entity-{ent.id}",
                    "category": "entity",
                    "title": f"{ent_name} ({ent.type or 'Entity'})",
                    "match_source": f"Extracted Entity [{ent.type or 'General'}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": ent.source_char_start,
                    "char_end": ent.source_char_end,
                    "page_number": ent.source_page_number,
                    "target_url": target,
                    "metadata": {
                        "entity_id": ent.id,
                        "type": ent.type,
                        "confidence": ent.confidence
                    }
                })

    # ==========================================================================
    # 4. CLAIMS & HYPOTHESES (Judicial Assessments & Competing Theories)
    # ==========================================================================
    if not category_filter or category_filter in ["all", "claim", "hypothesis"]:
        # Hypotheses
        hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
        for h in hypotheses:
            h_title = h.title or ""
            h_desc = h.description or ""
            if lower_q in h_title.lower() or lower_q in h_desc.lower():
                snippet, _, _ = extract_highlighted_snippet(h_desc or h_title, clean_q)
                results.append({
                    "id": f"hypothesis-{h.id}",
                    "category": "claim",
                    "title": h_title,
                    "match_source": f"Competing Hypothesis [{h.status or 'Active'}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/hypotheses",
                    "metadata": {
                        "hypothesis_id": h.id,
                        "status": h.status
                    }
                })

        # Evidence Assessments / Evaluated Claims
        assessments = (
            db.query(EvidenceAssessment)
            .join(Hypothesis, EvidenceAssessment.hypothesis_id == Hypothesis.id)
            .filter(Hypothesis.case_id == case_id)
            .all()
        )
        for ass in assessments:
            ass_reason = ass.reason or ""
            ass_quote = ass.quoted_source_line or ""
            if lower_q in ass_reason.lower() or lower_q in ass_quote.lower():
                snippet, _, _ = extract_highlighted_snippet(ass_quote or ass_reason, clean_q)
                results.append({
                    "id": f"assessment-{ass.id}",
                    "category": "claim",
                    "title": f"Claim Assessment: {ass.classification.replace('_', ' ').title()}",
                    "match_source": f"Evidence Assessment ({ass.classification})",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/evidence/{ass.evidence_id}?highlight={clean_q}",
                    "metadata": {
                        "assessment_id": ass.id,
                        "hypothesis_id": ass.hypothesis_id,
                        "evidence_id": ass.evidence_id,
                        "classification": ass.classification
                    }
                })

    # ==========================================================================
    # 5. SUSPECTS & PRIOR CRIMINAL RECORDS
    # ==========================================================================
    if not category_filter or category_filter in ["all", "suspect"]:
        # Suspect Profile Factors
        factors = (
            db.query(SuspectProfileFactor)
            .filter(SuspectProfileFactor.case_id == case_id)
            .all()
        )
        for fac in factors:
            s_name = fac.suspect_name or "Unknown Suspect"
            f_type = fac.factor_type or ""
            f_note = fac.note or ""
            f_val = fac.factor_value or ""
            if lower_q in s_name.lower() or lower_q in f_type.lower() or lower_q in f_note.lower() or lower_q in f_val.lower():
                target_field = f_note if lower_q in f_note.lower() else (f"{f_type.capitalize()}: {f_val}" if lower_q in f_val.lower() else (s_name if lower_q in s_name.lower() else f_note))
                snippet, _, _ = extract_highlighted_snippet(target_field, clean_q)
                results.append({
                    "id": f"suspect-factor-{fac.id}",
                    "category": "suspect",
                    "title": f"Suspect Factor: {s_name} ({f_type.capitalize()})",
                    "match_source": f"Suspect Profile Factor [{f_type}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/suspects",
                    "metadata": {
                        "factor_id": fac.id,
                        "suspect_name": s_name,
                        "factor_type": f_type
                    }
                })

        # Prior Criminal Records
        prior_records = (
            db.query(PriorRecord)
            .filter(PriorRecord.case_id == case_id)
            .all()
        )
        for pr in prior_records:
            pr_name = pr.suspect_name or ""
            pr_type = pr.offense_type or ""
            pr_sec = pr.legal_section or ""
            pr_loc = pr.location or ""
            if lower_q in pr_name.lower() or lower_q in pr_type.lower() or lower_q in pr_sec.lower() or lower_q in pr_loc.lower():
                snippet = f"Prior Record: {pr_name} - {pr_type} ({pr_sec}) at {pr_loc} [Outcome: {pr.outcome or 'recorded'}]."
                results.append({
                    "id": f"prior-record-{pr.id}",
                    "category": "suspect",
                    "title": f"Prior Criminal Record: {pr_name}",
                    "match_source": f"Criminal History Record [{pr_type}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/suspects",
                    "metadata": {
                        "record_id": pr.id,
                        "suspect_name": pr_name,
                        "offense_type": pr_type,
                        "outcome": pr.outcome
                    }
                })

    # ==========================================================================
    # 6. INVESTIGATION TASKS (Pending, In Progress, Gaps)
    # ==========================================================================
    if not category_filter or category_filter in ["all", "task"]:
        tasks = (
            db.query(InvestigationTask)
            .filter(InvestigationTask.case_id == case_id)
            .all()
        )
        for t in tasks:
            t_text = t.task or ""
            t_reason = t.reason or ""
            t_assign = t.assigned_to or ""
            if lower_q in t_text.lower() or lower_q in t_reason.lower() or lower_q in t_assign.lower():
                snippet, _, _ = extract_highlighted_snippet(t_reason or t_text, clean_q)
                results.append({
                    "id": f"task-{t.id}",
                    "category": "task",
                    "title": t_text,
                    "match_source": f"Investigation Task [{t.priority} Priority - {t.status}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/investigation-plan",
                    "metadata": {
                        "task_id": t.id,
                        "priority": t.priority,
                        "status": t.status,
                        "assigned_to": t.assigned_to
                    }
                })

    # ==========================================================================
    # 7. ALERTS & STATUTORY DEADLINES
    # ==========================================================================
    if not category_filter or category_filter in ["all", "alert"]:
        alerts = (
            db.query(Alert)
            .filter(Alert.case_id == case_id)
            .all()
        )
        for a in alerts:
            a_title = a.title or ""
            a_msg = a.message or ""
            if lower_q in a_title.lower() or lower_q in a_msg.lower():
                snippet, _, _ = extract_highlighted_snippet(a_msg, clean_q)
                results.append({
                    "id": f"alert-{a.id}",
                    "category": "alert",
                    "title": a_title,
                    "match_source": f"Case Alert [{a.severity.upper()} - {a.rule_type}]",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/wall",
                    "metadata": {
                        "alert_id": a.id,
                        "severity": a.severity,
                        "rule_type": a.rule_type
                    }
                })

        deadlines = (
            db.query(CaseDeadline)
            .filter(CaseDeadline.case_id == case_id)
            .all()
        )
        for d in deadlines:
            d_rule = getattr(d, 'title', None) or getattr(d, 'rule_name', '') or ""
            d_code = getattr(d, 'legal_code', '') or ""
            d_stat = getattr(d, 'statute_name', '') or ""
            d_status = getattr(d, 'status', 'Active') or 'Active'
            if lower_q in d_rule.lower() or lower_q in d_code.lower() or lower_q in d_stat.lower() or lower_q in d_status.lower():
                snippet = f"Statutory Deadline: {d_rule} - {d_status}."
                results.append({
                    "id": f"deadline-{d.id}",
                    "category": "alert",
                    "title": f"Statutory Deadline: {d_rule}",
                    "match_source": f"Statutory Limitation [{d_code}]" if d_code else "Statutory Limitation",
                    "matched_snippet": snippet,
                    "highlight_term": clean_q,
                    "char_start": None,
                    "char_end": None,
                    "page_number": None,
                    "target_url": f"/cases/{case_id}/wall",
                    "metadata": {
                        "deadline_id": d.id,
                        "legal_code": d_code
                    }
                })

    # Sort results with high relevance (exact title matches first, then exact original text, then quotes)
    def relevance_key(item):
        cat_order = {"exhibit": 0, "quote": 1, "entity": 2, "claim": 3, "suspect": 4, "task": 5, "alert": 6}
        is_title = lower_q in item["title"].lower()
        return (0 if is_title else 1, cat_order.get(item["category"], 9))

    results.sort(key=relevance_key)

    # Deduplicate by ID
    seen_ids = set()
    deduped = []
    for item in results:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            deduped.append(item)

    return deduped[:limit]
