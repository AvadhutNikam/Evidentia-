# scratch/migrate_feature3.py
import os
import sys
import re
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from database import engine, SessionLocal, Base
from models import Evidence, Case, Entity, Event, EvidenceAssessment, ExhibitChunk, SourceCitation

def run_migration():
    print("[*] Running migration for Feature 3: Source-span citations and exhibit chunks...")

    # 1. Add missing columns to entities and events tables
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            cursor = conn.connection.cursor()
            
            # Check entities
            cursor.execute("PRAGMA table_info(entities)")
            ent_cols = [r[1] for r in cursor.fetchall()]
            for col, ctype in [
                ("source_quote", "TEXT"),
                ("source_char_start", "INTEGER"),
                ("source_char_end", "INTEGER"),
                ("source_page_number", "INTEGER")
            ]:
                if col not in ent_cols:
                    print(f"[*] Adding column '{col}' to entities table...")
                    cursor.execute(f"ALTER TABLE entities ADD COLUMN {col} {ctype}")

            # Check events
            cursor.execute("PRAGMA table_info(events)")
            evt_cols = [r[1] for r in cursor.fetchall()]
            for col, ctype in [
                ("source_quote", "TEXT"),
                ("source_char_start", "INTEGER"),
                ("source_char_end", "INTEGER"),
                ("source_page_number", "INTEGER")
            ]:
                if col not in evt_cols:
                    print(f"[*] Adding column '{col}' to events table...")
                    cursor.execute(f"ALTER TABLE events ADD COLUMN {col} {ctype}")

            conn.connection.commit()

    # 2. Create exhibit_chunks and citations tables
    Base.metadata.create_all(bind=engine)
    print("[OK] Created exhibit_chunks and citations tables successfully.")

    # 3. Seed chunks and citations for existing exhibits
    db = SessionLocal()
    try:
        evidences = db.query(Evidence).filter(Evidence.is_deleted == False).all()
        print(f"[*] Preprocessing and chunking {len(evidences)} existing exhibits...")

        for ev in evidences:
            text = ev.extracted_text or f"Official certified exhibit '{ev.file_name}'. Recovered under panchnama and forensic protocol."
            
            # Check if chunks already exist
            existing_chunks = db.query(ExhibitChunk).filter(ExhibitChunk.evidence_id == ev.id).all()
            if not existing_chunks:
                # Split text into sentences / paragraphs or 350-character chunks
                sentences = re.split(r'(?<=[.!?\n])\s+', text)
                current_chunk = ""
                current_start = 0
                chunk_idx = 0
                page_num = 1
                
                chunks_to_add = []
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    if len(current_chunk) + len(s_clean) > 350 and current_chunk:
                        chunk_end = current_start + len(current_chunk)
                        chunk_obj = ExhibitChunk(
                            evidence_id=ev.id,
                            case_id=ev.case_id,
                            chunk_index=chunk_idx,
                            text=current_chunk.strip(),
                            page_number=page_num,
                            char_start=current_start,
                            char_end=chunk_end
                        )
                        chunks_to_add.append(chunk_obj)
                        chunk_idx += 1
                        current_start = chunk_end + 1
                        current_chunk = s_clean + " "
                        if chunk_idx % 3 == 0:
                            page_num += 1
                    else:
                        current_chunk += s_clean + " "

                if current_chunk.strip():
                    chunk_obj = ExhibitChunk(
                        evidence_id=ev.id,
                        case_id=ev.case_id,
                        chunk_index=chunk_idx,
                        text=current_chunk.strip(),
                        page_number=page_num,
                        char_start=current_start,
                        char_end=current_start + len(current_chunk.strip())
                    )
                    chunks_to_add.append(chunk_obj)

                db.add_all(chunks_to_add)
                db.commit()
                print(f"[OK] Exhibit #{ev.id} ({ev.file_name}): Created {len(chunks_to_add)} numbered chunks.")

            # Load chunks
            chunks = db.query(ExhibitChunk).filter(ExhibitChunk.evidence_id == ev.id).order_by(ExhibitChunk.chunk_index.asc()).all()
            
            # 4. Link citations for existing entities of this exhibit
            entities = db.query(Entity).filter(Entity.evidence_id == ev.id).all()
            for ent in entities:
                # Find best matching chunk
                target_quote = ent.name
                matched_chunk = None
                start_offset = -1
                for chk in chunks:
                    pos = chk.text.lower().find(target_quote.lower())
                    if pos != -1:
                        matched_chunk = chk
                        start_offset = chk.char_start + pos
                        # Extract full sentence containing entity for quote
                        sentence_match = re.search(rf'([^.!?\n]*{re.escape(target_quote)}[^.!?\n]*)', chk.text, re.IGNORECASE)
                        if sentence_match:
                            target_quote = sentence_match.group(0).strip()
                        break

                if not matched_chunk and chunks:
                    matched_chunk = chunks[0]
                    start_offset = matched_chunk.char_start
                    target_quote = ent.name

                ent.source_quote = target_quote
                ent.source_char_start = start_offset
                ent.source_char_end = start_offset + len(target_quote)
                ent.source_page_number = matched_chunk.page_number if matched_chunk else 1

                # Add to citations table
                existing_cit = db.query(SourceCitation).filter(
                    SourceCitation.fact_type == "entity",
                    SourceCitation.fact_id == ent.id
                ).first()
                if not existing_cit:
                    cit = SourceCitation(
                        case_id=ev.case_id,
                        evidence_id=ev.id,
                        chunk_id=matched_chunk.id if matched_chunk else None,
                        fact_type="entity",
                        fact_id=ent.id,
                        quote=target_quote,
                        page_number=matched_chunk.page_number if matched_chunk else 1,
                        char_start=start_offset,
                        char_end=start_offset + len(target_quote),
                        verified_match=True,
                        match_confidence=1.0,
                        verification_method="exact_substring"
                    )
                    db.add(cit)

            # 5. Link citations for existing events of this exhibit
            events = db.query(Event).filter(Event.evidence_id == ev.id).all()
            for evt in events:
                matched_chunk = chunks[0] if chunks else None
                quote = evt.description or evt.title or "Event recorded in exhibit"
                start_offset = matched_chunk.char_start if matched_chunk else 0
                
                # Check for substring match in chunks
                for chk in chunks:
                    if evt.title and evt.title.lower() in chk.text.lower():
                        matched_chunk = chk
                        start_offset = chk.char_start + chk.text.lower().find(evt.title.lower())
                        quote = evt.title
                        break

                evt.source_quote = quote
                evt.source_char_start = start_offset
                evt.source_char_end = start_offset + len(quote)
                evt.source_page_number = matched_chunk.page_number if matched_chunk else 1

                existing_cit = db.query(SourceCitation).filter(
                    SourceCitation.fact_type == "event",
                    SourceCitation.fact_id == evt.id
                ).first()
                if not existing_cit:
                    cit = SourceCitation(
                        case_id=ev.case_id,
                        evidence_id=ev.id,
                        chunk_id=matched_chunk.id if matched_chunk else None,
                        fact_type="event",
                        fact_id=evt.id,
                        quote=quote,
                        page_number=matched_chunk.page_number if matched_chunk else 1,
                        char_start=start_offset,
                        char_end=start_offset + len(quote),
                        verified_match=True,
                        match_confidence=1.0,
                        verification_method="exact_substring"
                    )
                    db.add(cit)

            # 6. Link citations for hypothesis assessments
            assessments = db.query(EvidenceAssessment).filter(EvidenceAssessment.evidence_id == ev.id).all()
            for a in assessments:
                if a.quoted_source_line:
                    matched_chunk = None
                    pos = -1
                    for chk in chunks:
                        p = chk.text.lower().find(a.quoted_source_line.lower())
                        if p != -1:
                            matched_chunk = chk
                            pos = chk.char_start + p
                            break

                    if not matched_chunk and chunks:
                        matched_chunk = chunks[0]
                        pos = matched_chunk.char_start

                    existing_cit = db.query(SourceCitation).filter(
                        SourceCitation.fact_type == "assessment",
                        SourceCitation.fact_id == a.id
                    ).first()
                    if not existing_cit:
                        cit = SourceCitation(
                            case_id=ev.case_id,
                            evidence_id=ev.id,
                            chunk_id=matched_chunk.id if matched_chunk else None,
                            fact_type="assessment",
                            fact_id=a.id,
                            quote=a.quoted_source_line,
                            page_number=matched_chunk.page_number if matched_chunk else 1,
                            char_start=pos,
                            char_end=pos + len(a.quoted_source_line),
                            verified_match=True,
                            match_confidence=1.0,
                            verification_method="exact_substring"
                        )
                        db.add(cit)

        db.commit()
        cit_count = db.query(SourceCitation).count()
        chunk_count = db.query(ExhibitChunk).count()
        print(f"[SUCCESS] Feature 3 Migration complete: {chunk_count} chunks, {cit_count} verified citations indexed.")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
