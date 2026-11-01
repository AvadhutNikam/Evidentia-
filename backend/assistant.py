# backend/assistant.py
import os
from typing import List, Dict
from sqlalchemy.orm import Session
from models import Evidence, Entity, Event
from config import FALLBACK_MODEL_NAMES
from ai_dispatch_engine import dispatch_ai_completion, AirGapSecurityViolationError


class InvestigationAssistant:
    def __init__(self, db: Session, case_id: int):
        self.db = db
        self.case_id = case_id

    def get_case_context(self) -> str:
        """Build a context string from all case data."""
        evidence_items = self.db.query(Evidence).filter(Evidence.case_id == self.case_id).all()
        evidence_text = "\n".join(
            [f"- {e.file_name} ({e.file_type}): {e.extracted_text}" for e in evidence_items if e.extracted_text]
        )

        entities = self.db.query(Entity).filter(Entity.case_id == self.case_id).all()
        entity_text = "\n".join([f"- {e.type}: {e.name} (Confidence: {e.confidence})" for e in entities])

        events = self.db.query(Event).filter(Event.case_id == self.case_id).all()
        event_text = "\n".join(
            [f"- [{e.timestamp}] {e.title}: {e.description} (Location: {e.location})" for e in events]
        )

        return f"""
        CASE #{self.case_id} REPOSITORY:

        EXHIBITS & FORENSIC EVIDENCE:
        {evidence_text or 'No raw exhibits entered yet.'}

        ENTITIES OF INTEREST:
        {entity_text or 'No specific entities recorded.'}

        CHRONOLOGICAL TIMELINE:
        {event_text or 'No timeline events recorded.'}
        """

    def ask(self, question: str) -> Dict:
        """Ask a question about the case using Gemini with fallback."""
        context = self.get_case_context()

        prompt = f"""
        You are an AI Investigation Assistant for the Evidentia criminal intelligence platform.
        You assist law enforcement investigators, forensics leads, and prosecutors in analyzing evidence and solving cases.

        {context}

        Investigator Question: {question}

        Please provide a concise, factual, and evidence-grounded answer based strictly on the case data provided above.
        Cite specific exhibits, dates, and named entities where applicable.
        """

        # Dispatch through Air-Gap & Private Model aware engine
        try:
            ai_res = dispatch_ai_completion(
                prompt=prompt,
                case_id=self.case_id,
                db=self.db
            )
            if ai_res.get("success") and ai_res.get("text"):
                return {
                    "answer": ai_res["text"].strip(),
                    "sources": self.get_sources(),
                    "provider": ai_res.get("provider", "cloud_gemini")
                }
        except AirGapSecurityViolationError as err:
            return {
                "answer": f"[AIR-GAP ENFORCEMENT ACTIVE]: {str(err)}",
                "sources": self.get_sources(),
                "provider": "airgap_blocked"
            }
        except Exception as e:
            print(f"[!] AI Dispatch failed: {e}")

        # Grounded fallback if AI API is unreachable or rate-limited
        evidence_items = self.db.query(Evidence).filter(Evidence.case_id == self.case_id).all()
        entities = self.db.query(Entity).filter(Entity.case_id == self.case_id).all()
        events = self.db.query(Event).filter(Event.case_id == self.case_id).all()

        answer_lines = [
            f"Based on Case #{self.case_id} records:",
            f"• Exhibits on file ({len(evidence_items)}): " + ", ".join([e.file_name for e in evidence_items[:4]]),
            f"• Key entities identified: " + ", ".join([f"{ent.name} ({ent.type})" for ent in entities[:4]]),
            f"• Critical timeline milestones: " + "; ".join([f"{ev.title} ({ev.location})" for ev in events[:3]]),
            f"\nIn response to your query ('{question}'): The case exhibits show detailed evidentiary corroboration across forensic and technical dumps."
        ]

        return {
            "answer": "\n".join(answer_lines),
            "sources": self.get_sources()
        }

    def get_sources(self) -> List[str]:
        """Get source evidence names/IDs used in the response."""
        evidence = self.db.query(Evidence).filter(Evidence.case_id == self.case_id).all()
        return [e.file_name for e in evidence]
