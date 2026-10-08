# backend/nli_engine.py
"""
Evidentia AI - Real Contradiction Detection Engine via Natural Language Inference (NLI)

Pipeline Architecture:
Evidence A                         Evidence B
     ↓                                  ↓
 extracted claims                   extracted claims
     └──────────────► Compare ◄─────────┘
                         ↓
              Classify (NLI):
              - ENTAILMENT
              - CONTRADICTION
              - NEUTRAL

Implementation:
1. Claims Extraction: Decomposes unstructured forensic exhibits into atomic factual propositions.
2. Pairwise Cross-Comparison: Compares extracted claims across exhibits.
3. NLI Classification:
   - Gemini Structured Output (Active default)
   - Dedicated Local NLI Transformer Model (Pluggable: DeBERTa-v3 / RoBERTa-large-MNLI)
4. Forensic Contradiction Persistence: Stores identified conflicts in PostgreSQL contradictions table.
"""

import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from models import Evidence, Contradiction

logger = logging.getLogger("evidentia.nli")

# ============================================================
# DATA STRUCTURES
# ============================================================

class NLIResult:
    def __init__(
        self,
        claim_a: str,
        source_a_id: str,
        claim_b: str,
        source_b_id: str,
        classification: str,  # ENTAILMENT, CONTRADICTION, NEUTRAL
        confidence: float,
        conflict_type: Optional[str] = None,
        reasoning: Optional[str] = None
    ):
        self.claim_a = claim_a
        self.source_a_id = source_a_id
        self.claim_b = claim_b
        self.source_b_id = source_b_id
        self.classification = classification.upper()
        self.confidence = confidence
        self.conflict_type = conflict_type or "Forensic Inconsistency"
        self.reasoning = reasoning or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_a": self.claim_a,
            "source_a_id": self.source_a_id,
            "claim_b": self.claim_b,
            "source_b_id": self.source_b_id,
            "classification": self.classification,
            "confidence": self.confidence,
            "conflict_type": self.conflict_type,
            "reasoning": self.reasoning,
        }


# ============================================================
# BASE NLI CLASSIFIER INTERFACE
# ============================================================

class AbstractNLIClassifier(ABC):
    """Abstract interface supporting both Gemini LLM and Dedicated Local NLI models."""

    @abstractmethod
    def extract_claims(self, text: str, exhibit_meta: Dict[str, Any]) -> List[str]:
        """Extract atomic factual claims from evidence exhibit text."""
        pass

    @abstractmethod
    def compare_claims_nli(
        self,
        claims_a: List[str],
        source_a_meta: Dict[str, Any],
        claims_b: List[str],
        source_b_meta: Dict[str, Any]
    ) -> List[NLIResult]:
        """Compare two sets of claims and classify relationships into ENTAILMENT, CONTRADICTION, or NEUTRAL."""
        pass


# ============================================================
# GEMINI STRUCTURED OUTPUT NLI IMPLEMENTATION
# ============================================================

class GeminiStructuredNLI(AbstractNLIClassifier):
    """
    Production-grade NLI engine using Gemini 2.5/Flash-Lite structured outputs.
    Executes the two-stage claim extraction and NLI inference pipeline.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}")

    def _get_client(self):
        if not self._client and os.getenv("GEMINI_API_KEY"):
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def extract_claims(self, text: str, exhibit_meta: Dict[str, Any]) -> List[str]:
        """Extracts atomic, verifiable claims from evidence exhibit text."""
        if not text or len(text.strip()) < 10:
            return []

        client = self._get_client()
        if not client:
            return self._fallback_extract_claims(text)

        prompt = f"""You are a Forensic Claim Extraction Engine for criminal investigations.
Extract 3 to 7 atomic, verifiable factual claims from the following forensic exhibit.
Each claim must state a specific assertion regarding time, location, suspect identity, actions, physical/digital telemetry, or forensic lab measurements.

Exhibit: {exhibit_meta.get('file_name', 'Unknown Exhibit')} ({exhibit_meta.get('file_type', 'Document')})
Content:
\"\"\"{text[:2500]}\"\"\"

Return ONLY a valid JSON array of strings:
[
  "Specific factual claim 1...",
  "Specific factual claim 2..."
]"""

        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
            raw = self._clean_json(resp.text)
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(c).strip() for c in data if str(c).strip()]
        except Exception as e:
            logger.warning(f"Gemini claim extraction failed: {e}. Falling back to rule-based chunking.")

        return self._fallback_extract_claims(text)

    def compare_claims_nli(
        self,
        claims_a: List[str],
        source_a_meta: Dict[str, Any],
        claims_b: List[str],
        source_b_meta: Dict[str, Any]
    ) -> List[NLIResult]:
        """
        Cross-compares claims from Exhibit A with claims from Exhibit B.
        Classifies each candidate relationship into:
        - ENTAILMENT: Claims mutually reinforce or imply each other.
        - CONTRADICTION: Claims cannot both be true simultaneously (alibi clashes, timeline discrepancy, forensic mismatch).
        - NEUTRAL: Claims describe independent or unrelated facts.
        """
        if not claims_a or not claims_b:
            return []

        client = self._get_client()
        source_a_label = f"Exhibit #{source_a_meta.get('id', 'A')} ({source_a_meta.get('file_name', 'Source A')})"
        source_b_label = f"Exhibit #{source_b_meta.get('id', 'B')} ({source_b_meta.get('file_name', 'Source B')})"

        if not client:
            return self._fallback_nli_comparison(claims_a, source_a_label, claims_b, source_b_label)

        claims_a_formatted = "\n".join([f"  [Claim A{i+1}]: {c}" for i, c in enumerate(claims_a)])
        claims_b_formatted = "\n".join([f"  [Claim B{j+1}]: {c}" for j, c in enumerate(claims_b)])

        prompt = f"""You are a specialized Forensic Natural Language Inference (NLI) Classifier for legal and criminal intelligence.

You are comparing factual claims extracted from two distinct evidentiary sources:
SOURCE A: {source_a_label}
Claims from Source A:
{claims_a_formatted}

SOURCE B: {source_b_label}
Claims from Source B:
{claims_b_formatted}

Analyze the pairwise relationships between the claims of Source A and Source B.
For any pair that meaningfully interacts or directly conflicts, classify the logical relationship into one of:
1. "CONTRADICTION": The two claims cannot both be true simultaneously (e.g. alibi vs camera detection, conflicting times for the same person, mutually exclusive forensic readings, conflicting vehicle models or locations).
2. "ENTAILMENT": One claim entails or confirms the other.
3. "NEUTRAL": The claims describe independent, non-conflicting facts.

Focus especially on detecting all genuine CONTRADICTIONS.

Return ONLY a valid JSON array of objects with the following schema:
[
  {{
    "claim_a": "Exact claim from Source A",
    "claim_b": "Exact claim from Source B",
    "classification": "CONTRADICTION",
    "confidence": 95.0,
    "conflict_type": "Alibi Discrepancy | Timeline Conflict | Forensic Inconsistency | Digital Telemetry Mismatch | Identity Conflict",
    "reasoning": "Clear 1-sentence legal/forensic rationale for why these two claims contradict each other."
  }}
]
Include any pairs classified as CONTRADICTION, and any key ENTAILMENT pairs.
If no meaningful interactions exist, return []."""

        results: List[NLIResult] = []
        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
            raw = self._clean_json(resp.text)
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    cls = str(item.get("classification", "NEUTRAL")).upper().strip()
                    results.append(
                        NLIResult(
                            claim_a=str(item.get("claim_a", "")).strip(),
                            source_a_id=source_a_label,
                            claim_b=str(item.get("claim_b", "")).strip(),
                            source_b_id=source_b_label,
                            classification=cls,
                            confidence=float(item.get("confidence", 90.0)),
                            conflict_type=item.get("conflict_type") or ("Forensic Inconsistency" if cls == "CONTRADICTION" else "Fact Alignment"),
                            reasoning=item.get("reasoning", "")
                        )
                    )
        except Exception as e:
            logger.warning(f"Gemini pairwise NLI comparison failed: {e}. Running fallback NLI classifier.")
            return self._fallback_nli_comparison(claims_a, source_a_label, claims_b, source_b_label)

        return results

    def compare_case_claims_batch(
        self,
        exhibit_items: List[Dict[str, Any]]
    ) -> List[NLIResult]:
        """
        Efficient multi-exhibit claims comparison in a single structured Gemini call.
        Compares all pairwise claims and classifies into ENTAILMENT, CONTRADICTION, NEUTRAL.
        """
        client = self._get_client()
        if not client or len(exhibit_items) < 2:
            fallback_results = []
            for i in range(len(exhibit_items)):
                for j in range(i + 1, len(exhibit_items)):
                    a = exhibit_items[i]
                    b = exhibit_items[j]
                    fallback_results.extend(self._fallback_nli_comparison(
                        a["claims"], a["source_label"], b["claims"], b["source_label"]
                    ))
            return fallback_results

        dossier_lines = []
        for item in exhibit_items:
            lines = [f"SOURCE: {item['source_label']}"]
            for idx, c in enumerate(item["claims"]):
                lines.append(f"  [Claim {idx+1}]: {c}")
            dossier_lines.append("\n".join(lines))
        dossier_text = "\n\n---\n\n".join(dossier_lines)

        prompt = f"""You are a specialized Forensic Natural Language Inference (NLI) Classifier for legal and criminal intelligence.

You are analyzing claims extracted from distinct evidentiary exhibits in a criminal case:
{dossier_text}

Analyze pairwise cross-exhibit relationships between claims from different exhibits.
For any two claims from different exhibits that meaningfully interact:
Classify their relationship into:
1. "CONTRADICTION": The two claims cannot both be true simultaneously (e.g. alibi vs camera telemetry, conflicting times for suspect, contradictory forensic lab results, conflicting vehicle or transaction details).
2. "ENTAILMENT": One claim entails, confirms, or directly substantiates the other.
3. "NEUTRAL": The claims describe independent, non-conflicting facts.

Focus especially on detecting all genuine CONTRADICTIONS.

Return ONLY a valid JSON array of objects with the following schema:
[
  {{
    "claim_a": "Specific claim from Exhibit A",
    "source_a_id": "Exhibit #X (FileName)",
    "claim_b": "Conflicting claim from Exhibit B",
    "source_b_id": "Exhibit #Y (FileName)",
    "classification": "CONTRADICTION",
    "confidence": 95.0,
    "conflict_type": "Alibi Discrepancy | Timeline Conflict | Forensic Inconsistency | Digital Telemetry Mismatch | Identity Conflict",
    "reasoning": "Clear 1-sentence legal/forensic rationale for why these two claims contradict each other."
  }}
]
Include any pairs classified as CONTRADICTION and key ENTAILMENT pairs.
If no contradictions exist, return []."""

        results: List[NLIResult] = []
        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
            raw = self._clean_json(resp.text)
            data = json.loads(raw)
            if isinstance(data, list):
                for obj in data:
                    cls = str(obj.get("classification", "NEUTRAL")).upper().strip()
                    results.append(
                        NLIResult(
                            claim_a=str(obj.get("claim_a", "")).strip(),
                            source_a_id=str(obj.get("source_a_id", "Exhibit A")).strip(),
                            claim_b=str(obj.get("claim_b", "")).strip(),
                            source_b_id=str(obj.get("source_b_id", "Exhibit B")).strip(),
                            classification=cls,
                            confidence=float(obj.get("confidence", 90.0)),
                            conflict_type=obj.get("conflict_type") or ("Forensic Inconsistency" if cls == "CONTRADICTION" else "Fact Alignment"),
                            reasoning=obj.get("reasoning", "")
                        )
                    )
        except Exception as e:
            logger.warning(f"Batch case claims NLI comparison failed: {e}. Running fallback.")
            for i in range(len(exhibit_items)):
                for j in range(i + 1, len(exhibit_items)):
                    a = exhibit_items[i]
                    b = exhibit_items[j]
                    results.extend(self._fallback_nli_comparison(
                        a["claims"], a["source_label"], b["claims"], b["source_label"]
                    ))
        return results


    def _fallback_extract_claims(self, text: str) -> List[str]:
        """Rule-based sentence chunking for offline/fallback claim extraction."""
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 20]
        # Keep sentences containing key indicators
        keywords = ["at", "on", "seen", "claimed", "withdrew", "located", "found", "dna", "blood", "camera", "call", "tower", "vehicle", "time", "ist"]
        relevant = [s for s in sentences if any(k in s.lower() for k in keywords)]
        return relevant[:5] if relevant else sentences[:4]

    def _fallback_nli_comparison(
        self,
        claims_a: List[str],
        source_a_label: str,
        claims_b: List[str],
        source_b_label: str
    ) -> List[NLIResult]:
        """Heuristic NLI comparison when AI API is unavailable."""
        results = []
        for ca in claims_a:
            for cb in claims_b:
                # Look for temporal/alibi conflict markers
                is_alibi_claim = "residence" in ca.lower() or "home" in ca.lower() or "claimed" in ca.lower()
                is_location_evidence = "cctv" in cb.lower() or "atm" in cb.lower() or "tower" in cb.lower() or "seen" in cb.lower()
                if is_alibi_claim and is_location_evidence:
                    results.append(
                        NLIResult(
                            claim_a=ca,
                            source_a_id=source_a_label,
                            claim_b=cb,
                            source_b_id=source_b_label,
                            classification="CONTRADICTION",
                            confidence=88.0,
                            conflict_type="Alibi Discrepancy",
                            reasoning="Claimed physical presence at residence conflicts with surveillance / digital telemetry at scene."
                        )
                    )
        return results

    @staticmethod
    def _clean_json(text: str) -> str:
        t = text.strip()
        if t.startswith("```json"):
            t = t[7:]
        elif t.startswith("```"):
            t = t[3:]
        if t.endswith("```"):
            t = t[:-3]
        return t.strip()


# ============================================================
# DEDICATED TRANSFORMER NLI CLASSIFIER (PLUGGABLE EXTENSION)
# ============================================================

class DedicatedTransformerNLI(AbstractNLIClassifier):
    """
    Pluggable dedicated Natural Language Inference classifier.
    Supports HuggingFace cross-encoders such as:
    - cross-encoder/nli-deberta-v3-base
    - roberta-large-mnli
    - facebook/bart-large-mnli
    """

    def __init__(self, model_name_or_path: Optional[str] = None):
        self.model_name = model_name_or_path or os.getenv("NLI_MODEL_NAME_OR_PATH", "cross-encoder/nli-deberta-v3-base")
        self.pipeline = None
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        try:
            from transformers import pipeline
            self.pipeline = pipeline("text-classification", model=self.model_name)
            logger.info(f"Loaded dedicated NLI transformer model: {self.model_name}")
        except Exception as e:
            logger.info(f"Dedicated NLI transformer not active ({e}). Defaulting to GeminiStructuredNLI.")
            self.pipeline = None

    def extract_claims(self, text: str, exhibit_meta: Dict[str, Any]) -> List[str]:
        # Uses sentence tokenizer for claims
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 25]
        return sentences[:6]

    def compare_claims_nli(
        self,
        claims_a: List[str],
        source_a_meta: Dict[str, Any],
        claims_b: List[str],
        source_b_meta: Dict[str, Any]
    ) -> List[NLIResult]:
        if not self.pipeline:
            # Fallback to Gemini Structured NLI if transformer weights are not locally downloaded
            gemini_fallback = GeminiStructuredNLI()
            return gemini_fallback.compare_claims_nli(claims_a, source_a_meta, claims_b, source_b_meta)

        results = []
        source_a_label = f"Exhibit #{source_a_meta.get('id', 'A')} ({source_a_meta.get('file_name', 'Source A')})"
        source_b_label = f"Exhibit #{source_b_meta.get('id', 'B')} ({source_b_meta.get('file_name', 'Source B')})"

        # Cross-encoder inference
        for ca in claims_a:
            for cb in claims_b:
                try:
                    # Model outputs: [ {label: 'contradiction', score: 0.94}, ... ]
                    res = self.pipeline({"text": ca, "text_pair": cb})
                    label = res.get("label", "neutral").upper()
                    score = float(res.get("score", 0.5)) * 100.0

                    if label == "CONTRADICTION" and score > 70.0:
                        results.append(
                            NLIResult(
                                claim_a=ca,
                                source_a_id=source_a_label,
                                claim_b=cb,
                                source_b_id=source_b_label,
                                classification="CONTRADICTION",
                                confidence=round(score, 1),
                                conflict_type="Forensic Inconsistency",
                                reasoning=f"Dedicated NLI Transformer ({self.model_name}) scored cross-claim contradiction at {round(score, 1)}% confidence."
                            )
                        )
                except Exception as e:
                    logger.debug(f"Transformer inference step error: {e}")

        return results


# ============================================================
# MASTER FORENSIC NLI CONTRADICTION DETECTOR
# ============================================================

class ForensicNLIDetector:
    """
    Coordinates end-to-end contradiction detection across case evidence exhibits:
    1. Exhibits Retrieval
    2. Atomic Claim Extraction (Evidence A & Evidence B)
    3. Pairwise Claim Cross-Comparison
    4. NLI Classification (ENTAILMENT, CONTRADICTION, NEUTRAL)
    5. Storage into PostgreSQL database
    """

    def __init__(self, classifier: Optional[AbstractNLIClassifier] = None):
        # Uses Gemini Structured NLI by default; if dedicated transformer is installed/configured, can use that
        if classifier:
            self.classifier = classifier
        elif os.getenv("USE_DEDICATED_NLI_MODEL", "false").lower() in ("true", "1"):
            self.classifier = DedicatedTransformerNLI()
        else:
            self.classifier = GeminiStructuredNLI()

    def detect_contradictions_between_exhibits(
        self,
        ev_a: Evidence,
        ev_b: Evidence,
        db: Session
    ) -> List[Contradiction]:
        """
        Executes the exact pipeline:
        Evidence A  ->  extracted claims
        Evidence B  ->  extracted claims
        Compare pairwise -> Classify: ENTAILMENT | CONTRADICTION | NEUTRAL
        Saves CONTRADICTION results to PostgreSQL.
        """
        text_a = ev_a.extracted_text or ev_a.file_name or ""
        text_b = ev_b.extracted_text or ev_b.file_name or ""

        meta_a = {"id": ev_a.id, "file_name": ev_a.file_name, "file_type": ev_a.file_type}
        meta_b = {"id": ev_b.id, "file_name": ev_b.file_name, "file_type": ev_b.file_type}

        # Step 1: Extract claims from Evidence A & Evidence B
        claims_a = self.classifier.extract_claims(text_a, meta_a)
        claims_b = self.classifier.extract_claims(text_b, meta_b)

        if not claims_a or not claims_b:
            return []

        # Step 2: Compare claims and classify via NLI
        nli_results = self.classifier.compare_claims_nli(claims_a, meta_a, claims_b, meta_b)

        # Step 3: Filter for CONTRADICTION and persist in PostgreSQL
        saved_contradictions: List[Contradiction] = []
        for item in nli_results:
            if item.classification == "CONTRADICTION" and item.claim_a and item.claim_b:
                # Check for existing duplicate in DB
                exists = db.query(Contradiction).filter(
                    Contradiction.case_id == ev_a.case_id,
                    Contradiction.statement_a == item.claim_a,
                    Contradiction.statement_b == item.claim_b
                ).first()

                if not exists:
                    # Also check reverse statement pair
                    exists_reverse = db.query(Contradiction).filter(
                        Contradiction.case_id == ev_a.case_id,
                        Contradiction.statement_a == item.claim_b,
                        Contradiction.statement_b == item.claim_a
                    ).first()
                    if exists_reverse:
                        continue

                    c_record = Contradiction(
                        case_id=ev_a.case_id,
                        statement_a=item.claim_a,
                        source_a_id=item.source_a_id,
                        statement_b=item.claim_b,
                        source_b_id=item.source_b_id,
                        conflict_type=item.conflict_type,
                        confidence=item.confidence,
                        status="Detected"
                    )
                    db.add(c_record)
                    saved_contradictions.append(c_record)

        if saved_contradictions:
            db.commit()
            for sc in saved_contradictions:
                db.refresh(sc)

        return saved_contradictions

    def detect_contradictions_for_case(
        self,
        case_id: int,
        db: Session,
        focus_evidence_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scans all exhibits for a case or compares a newly added exhibit against all existing exhibits.
        Returns newly detected contradictions and audit statistics.
        """
        all_exhibits = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        if len(all_exhibits) < 2:
            return {
                "case_id": case_id,
                "status": "skipped",
                "message": "At least two evidence exhibits are required to detect contradictions.",
                "contradictions_found": 0,
                "contradictions": []
            }

        # Step 1: Extract claims for all relevant exhibits
        exhibit_items = []
        for ev in all_exhibits:
            txt = ev.extracted_text or ev.file_name or ""
            meta = {"id": ev.id, "file_name": ev.file_name, "file_type": ev.file_type}
            claims = self.classifier.extract_claims(txt, meta)
            if claims:
                exhibit_items.append({
                    "evidence_id": ev.id,
                    "source_label": f"Exhibit #{ev.id} ({ev.file_name})",
                    "claims": claims
                })

        if len(exhibit_items) < 2:
            all_case_contradictions = db.query(Contradiction).filter(Contradiction.case_id == case_id).all()
            return {
                "case_id": case_id,
                "status": "success",
                "pairs_evaluated": 0,
                "new_contradictions_detected": 0,
                "total_contradictions": len(all_case_contradictions),
                "contradictions": all_case_contradictions
            }

        # Step 2: Run batch NLI comparison across exhibit claims
        if hasattr(self.classifier, "compare_case_claims_batch"):
            nli_results = self.classifier.compare_case_claims_batch(exhibit_items)
        else:
            nli_results = []
            for i in range(len(all_exhibits)):
                for j in range(i + 1, len(all_exhibits)):
                    cs = self.detect_contradictions_between_exhibits(all_exhibits[i], all_exhibits[j], db)
                    # already saved in detect_contradictions_between_exhibits

        total_new_contradictions: List[Contradiction] = []
        if nli_results:
            for item in nli_results:
                if item.classification == "CONTRADICTION" and item.claim_a and item.claim_b:
                    exists = db.query(Contradiction).filter(
                        Contradiction.case_id == case_id,
                        Contradiction.statement_a == item.claim_a,
                        Contradiction.statement_b == item.claim_b
                    ).first()
                    if not exists:
                        exists_rev = db.query(Contradiction).filter(
                            Contradiction.case_id == case_id,
                            Contradiction.statement_a == item.claim_b,
                            Contradiction.statement_b == item.claim_a
                        ).first()
                        if not exists_rev:
                            c_record = Contradiction(
                                case_id=case_id,
                                statement_a=item.claim_a,
                                source_a_id=item.source_a_id,
                                statement_b=item.claim_b,
                                source_b_id=item.source_b_id,
                                conflict_type=item.conflict_type,
                                confidence=item.confidence,
                                status="Detected"
                            )
                            db.add(c_record)
                            total_new_contradictions.append(c_record)

            if total_new_contradictions:
                db.commit()
                for c in total_new_contradictions:
                    db.refresh(c)

        all_case_contradictions = db.query(Contradiction).filter(Contradiction.case_id == case_id).all()

        return {
            "case_id": case_id,
            "status": "success",
            "pairs_evaluated": len(exhibit_items) * (len(exhibit_items) - 1) // 2,
            "new_contradictions_detected": len(total_new_contradictions),
            "total_contradictions": len(all_case_contradictions),
            "contradictions": all_case_contradictions
        }
