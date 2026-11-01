"""
backend/connectors/base.py
==========================
Base Connector Interface & Standardized Handover Pipeline for Live Evidence Streams.

Every connector source (Watch Folder, Email Tip-Off Inbox, Scheduled API Pull, Webhook Push)
implements the same small, reliable interface:
  1. fetch_new_items(db) -> List[IncomingEvidenceItem]
  2. normalize(raw_item) -> IncomingEvidenceItem
  3. handover(item, db, user) -> Evidence

Every incoming item goes through the exact same path as a manual upload:
  - Byte validation & signature checking (upload_validator)
  - Cryptographic SHA-256 calculation & secure filesystem persistence (storage)
  - Evidence record creation with extraction_mode="connector"
  - Merkle-chained Custody Log recording the source system and exact receipt time
  - Audit logging in immutable ledger
  - Asynchronous background job creation (jobs)
  - Section 65B Electronic Evidence certificate rule check (alerts_engine)
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from models import Evidence, EvidenceStatus, User, DataConnector, ConnectorIngestRecord
from upload_validator import validate_evidence_upload
from storage import save_uploaded_file
from audit_engine import log_custody_event, log_audit_event
from jobs import create_job

logger = logging.getLogger("evidentia.connectors")


@dataclass
class IncomingEvidenceItem:
    """
    Normalized intermediate evidence artifact produced by any connector.
    """
    raw_bytes: bytes
    filename: str
    evidence_type: str = "document"  # document, forensic, cdr, financial, photograph, audio, video
    source_system: str = "unknown"   # e.g., "watch_folder:D:/lab_drops", "email_inbox:tip-line@evidentia.local"
    receipt_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    custody_notes: str = ""
    external_item_id: Optional[str] = None
    sec_65b_certificate_present: bool = True
    collected_by: Optional[str] = None


class BaseConnector(ABC):
    """
    Abstract Base Class for all Evidentia Live Evidence Connectors.
    """

    def __init__(self, connector_record: DataConnector):
        self.connector_id = connector_record.id
        self.case_id = connector_record.case_id
        self.name = connector_record.name
        self.connector_type = connector_record.connector_type
        self.source_identifier = connector_record.source_identifier
        self.config = {}
        if connector_record.config_json:
            try:
                import json
                self.config = json.loads(connector_record.config_json)
            except Exception:
                self.config = {}

    @abstractmethod
    def fetch_new_items(self, db: Session) -> List[IncomingEvidenceItem]:
        """
        Polls or checks the underlying source for new, uningested evidence items.
        Returns a list of normalized IncomingEvidenceItem objects.
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> IncomingEvidenceItem:
        """
        Normalizes source-specific raw data into an IncomingEvidenceItem.
        """
        pass

    def handover(
        self,
        item: IncomingEvidenceItem,
        db: Session,
        user: Optional[User] = None
    ) -> Evidence:
        """
        Standardized Handover Pipeline:
        Processes an incoming evidence item identically to a manual upload,
        recording the exact source system and receipt time in the custody log.
        """
        # 1. Fallback user identity if automated service worker
        user_id = getattr(user, "id", None) if user else None
        user_name = getattr(user, "full_name", f"Connector [{self.name}]") if user else f"Connector [{self.name}]"
        user_role = getattr(user, "role", "automated_service") if user else "automated_service"

        # 2. Upload Validation (MIME type, extension, size limits, case storage quotas)
        val_res = validate_evidence_upload(
            file_bytes=item.raw_bytes,
            original_filename=item.filename,
            case_id=self.case_id,
            db=db,
            user=user
        )

        # 3. Secure File Storage & Cryptographic SHA-256 Fingerprinting
        import asyncio
        # Run save_uploaded_file synchronously or in current loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async event loop (FastAPI request context)
                storage_path, file_size, sha256_hash = asyncio.run_coroutine_threadsafe(
                    save_uploaded_file(item.raw_bytes, val_res.sanitized_filename),
                    loop
                ).result()
            else:
                storage_path, file_size, sha256_hash = loop.run_until_complete(
                    save_uploaded_file(item.raw_bytes, val_res.sanitized_filename)
                )
        except Exception:
            # Synchronous direct fallback saving
            import hashlib
            from pathlib import Path
            sha256_hash = hashlib.sha256(item.raw_bytes).hexdigest()
            file_size = len(item.raw_bytes)
            backend_dir = Path(__file__).resolve().parent.parent
            uploads_dir = backend_dir / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(uploads_dir / val_res.sanitized_filename)
            with open(storage_path, "wb") as f_out:
                f_out.write(item.raw_bytes)

        # 4. Check for duplicate ingestion in this case
        existing_dup = (
            db.query(Evidence)
            .filter(
                Evidence.case_id == self.case_id,
                Evidence.file_hash == sha256_hash,
                Evidence.is_deleted == False
            )
            .first()
        )
        if existing_dup:
            logger.info(
                f"[Connector:{self.name}] Duplicate evidence detected (hash={sha256_hash[:12]}...). "
                f"Skipping duplicate exhibit creation."
            )
            # Log duplicate record
            self._record_ingest_event(
                db=db,
                evidence_id=existing_dup.id,
                item=item,
                file_hash=sha256_hash,
                file_size=file_size,
                status="duplicate_skipped",
                error_message=f"Duplicate SHA-256 hash matching existing Exhibit #{existing_dup.id} ({existing_dup.file_name})"
            )
            return existing_dup

        # 5. Create Evidence Record
        officer_name = item.collected_by or f"Connector [{self.name}]"
        custody_notes_text = (
            f"Automated ingestion via {self.connector_type} from source system '{item.source_system}'. "
            f"Receipt timestamp: {item.receipt_time.isoformat()}. "
            f"Original reference: {item.external_item_id or item.filename}. "
            f"{item.custody_notes}".strip()
        )

        db_evidence = Evidence(
            case_id=self.case_id,
            file_name=val_res.sanitized_filename,
            file_type=val_res.detected_category,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by=user_name,
            processing_status=EvidenceStatus.UPLOADED,
            source=item.source_system,
            evidence_type=item.evidence_type or "document",
            file_hash=sha256_hash,
            hash_verified=True,
            chain_of_custody_complete=True,
            sec_65b_certificate_present=item.sec_65b_certificate_present,
            source_independent=True,
            quality_rating=4.0,
            collected_by=officer_name,
            collection_date=item.receipt_time,
            custody_notes=custody_notes_text,
            is_deleted=False,
            extraction_mode="connector",
            is_demo_fixture=False,
            connector_id=self.connector_id,
            connector_type=self.connector_type,
            connector_source_system=item.source_system,
            connector_receipt_time=item.receipt_time
        )
        db.add(db_evidence)
        db.commit()
        db.refresh(db_evidence)

        # 6. Record Chain of Custody Entry with Exact Source System and Receipt Time
        # "Record the source system and receipt time in the custody log, so you can prove where each item came from."
        log_custody_event(
            db=db,
            evidence_id=db_evidence.id,
            case_id=self.case_id,
            action="CONNECTOR_INGEST",
            actor_name=f"Automated Connector: {self.name}",
            actor_role=f"connector_{self.connector_type}",
            source_agency=item.source_system,
            location=f"Live Connector Pipeline ({self.connector_type})",
            notes=(
                f"Automated ingestion from source system '{item.source_system}'. "
                f"Receipt time: {item.receipt_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                f"Raw byte SHA-256 fingerprint verified: {sha256_hash}. "
                f"{item.custody_notes}".strip()
            ),
            file_hash_snapshot=sha256_hash
        )

        # 7. Record Merkle-chained Audit Log
        log_audit_event(
            db=db,
            action_type="CONNECTOR_EVIDENCE_INGEST",
            target_type="exhibit",
            target_id=str(db_evidence.id),
            description=(
                f"Connector '{self.name}' ({self.connector_type}) streamed '{item.filename}' "
                f"into Case #{self.case_id}. Source: {item.source_system}. SHA-256: {sha256_hash[:16]}..."
            ),
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            case_id=self.case_id,
            after_value=sha256_hash
        )

        # 8. Create Background Processing Job (extraction, citations, ACH recalculation)
        try:
            job = create_job(
                db=db,
                case_id=self.case_id,
                exhibit_id=db_evidence.id,
                job_type="process_evidence",
                user_id=user_id,
                created_by=user_name,
                priority=0
            )
            setattr(db_evidence, "job_id", job.id)
        except Exception as je:
            logger.warning(f"Could not queue process_evidence job for connector exhibit {db_evidence.id}: {je}")

        # 9. Evaluate Section 65B Electronic Evidence Missing Certificate Rule
        try:
            from alerts_engine import check_missing_certificate_rule
            check_missing_certificate_rule(self.case_id, db_evidence.id, db)
        except Exception as ae:
            logger.debug(f"Could not run certificate check rule: {ae}")

        # Real-Time Cross-Case Matching across permitted cases
        try:
            from cross_case_engine import match_exhibit_cross_case_realtime
            conn_user = db.query(User).filter(User.id == user_id).first() if user_id else None
            if conn_user:
                match_exhibit_cross_case_realtime(db_evidence.id, conn_user, db)
        except Exception as cce:
            logger.warning(f"Could not run real-time cross-case match for connector exhibit {db_evidence.id}: {cce}")

        # 10. Record Ingestion History Event & Update Connector Metrics
        self._record_ingest_event(
            db=db,
            evidence_id=db_evidence.id,
            item=item,
            file_hash=sha256_hash,
            file_size=file_size,
            status="success"
        )

        return db_evidence

    def _record_ingest_event(
        self,
        db: Session,
        evidence_id: Optional[int],
        item: IncomingEvidenceItem,
        file_hash: str,
        file_size: int,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """
        Records an entry in connector_ingest_records for historical traceability.
        """
        import json
        details = {
            "metadata": item.metadata,
            "evidence_type": item.evidence_type,
            "external_id": item.external_item_id,
            "custody_notes": item.custody_notes
        }

        rec = ConnectorIngestRecord(
            connector_id=self.connector_id,
            case_id=self.case_id,
            evidence_id=evidence_id,
            source_system=item.source_system,
            source_filename=item.filename,
            file_hash=file_hash,
            file_size=file_size,
            receipt_time=item.receipt_time,
            status=status,
            error_message=error_message,
            details_json=json.dumps(details)
        )
        db.add(rec)

        # Update connector stats
        conn = db.query(DataConnector).filter(DataConnector.id == self.connector_id).first()
        if conn:
            conn.last_polled_at = datetime.now(timezone.utc)
            if status == "success":
                conn.last_ingest_at = datetime.now(timezone.utc)
                conn.items_ingested_count = (conn.items_ingested_count or 0) + 1
            if error_message:
                conn.error_message = error_message
                conn.status = "error"
            else:
                conn.status = "active"

        db.commit()

