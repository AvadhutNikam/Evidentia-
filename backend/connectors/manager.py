"""
backend/connectors/manager.py
=============================
Connector Lifecycle Manager & Stream Dispatcher.

Coordinates connector instantiation, scheduled polling, drop simulation,
and webhook routing. Ensures all ingested artifacts conform to forensic chain of custody.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models import DataConnector, ConnectorIngestRecord, Evidence, User
from connectors.base import BaseConnector, IncomingEvidenceItem
from connectors.folder_watch import FolderWatchConnector
from connectors.email_inbox import EmailInboxConnector
from connectors.webhook import WebhookConnector
from connectors.api_pull import ApiPullConnector

logger = logging.getLogger("evidentia.connectors.manager")


class ConnectorManager:
    """
    Central manager for data connectors.
    """

    @staticmethod
    def get_connector(connector_record: DataConnector) -> BaseConnector:
        """
        Factory method instantiating the appropriate connector driver.
        """
        c_type = connector_record.connector_type.lower()
        if c_type == "folder_watch":
            return FolderWatchConnector(connector_record)
        elif c_type == "email_inbox":
            return EmailInboxConnector(connector_record)
        elif c_type == "webhook":
            return WebhookConnector(connector_record)
        elif c_type == "api_pull":
            return ApiPullConnector(connector_record)
        else:
            raise ValueError(f"Unsupported connector type: '{c_type}'")

    @classmethod
    def poll_connector(
        cls,
        connector_id: int,
        db: Session,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Executes a poll pass for the specified connector.
        Fetches pending items, runs them through the standardized handover pipeline,
        and updates connector telemetry.
        """
        conn = db.query(DataConnector).filter(DataConnector.id == connector_id).first()
        if not conn:
            raise ValueError(f"Connector #{connector_id} not found.")

        if not conn.is_active:
            return {
                "success": False,
                "connector_id": connector_id,
                "connector_name": conn.name,
                "items_fetched": 0,
                "items_ingested": 0,
                "duplicates_skipped": 0,
                "errors_count": 0,
                "message": f"Connector '{conn.name}' is currently paused / inactive.",
                "ingested_evidence_ids": []
            }

        conn.status = "polling"
        conn.last_polled_at = datetime.now(timezone.utc)
        db.commit()

        try:
            connector = cls.get_connector(conn)
            items = connector.fetch_new_items(db)

            ingested_ids: List[int] = []
            duplicates_count = 0
            errors_count = 0

            # Record initial count before this pass to detect duplicates
            for item in items:
                try:
                    prior_ingest_records = (
                        db.query(ConnectorIngestRecord)
                        .filter(
                            ConnectorIngestRecord.connector_id == conn.id,
                            ConnectorIngestRecord.source_filename == item.filename
                        )
                        .count()
                    )

                    evidence = connector.handover(item, db, user)

                    # Check if latest record for this file was duplicate_skipped
                    latest_rec = (
                        db.query(ConnectorIngestRecord)
                        .filter(
                            ConnectorIngestRecord.connector_id == conn.id,
                            ConnectorIngestRecord.source_filename == item.filename
                        )
                        .order_by(ConnectorIngestRecord.id.desc())
                        .first()
                    )

                    if latest_rec and latest_rec.status == "duplicate_skipped":
                        duplicates_count += 1
                    else:
                        ingested_ids.append(evidence.id)
                except Exception as ie:
                    logger.error(f"[ConnectorManager] Error handing over item '{item.filename}': {ie}")
                    errors_count += 1

            conn.status = "active" if errors_count == 0 else "error"
            if errors_count > 0:
                conn.error_message = f"Encountered {errors_count} error(s) during last poll."
            else:
                conn.error_message = None
            db.commit()

            return {
                "success": True,
                "connector_id": conn.id,
                "connector_name": conn.name,
                "items_fetched": len(items),
                "items_ingested": len(ingested_ids),
                "duplicates_skipped": duplicates_count,
                "errors_count": errors_count,
                "message": (
                    f"Poll complete for '{conn.name}'. {len(items)} items processed: "
                    f"{len(ingested_ids)} ingested into evidence docket, "
                    f"{duplicates_count} duplicates skipped."
                ),
                "ingested_evidence_ids": ingested_ids
            }

        except Exception as e:
            logger.exception(f"[ConnectorManager] Poll failure on connector #{conn.id}: {e}")
            conn.status = "error"
            conn.error_message = str(e)
            db.commit()
            return {
                "success": False,
                "connector_id": conn.id,
                "connector_name": conn.name,
                "items_fetched": 0,
                "items_ingested": 0,
                "duplicates_skipped": 0,
                "errors_count": 1,
                "message": f"Poll failed: {str(e)}",
                "ingested_evidence_ids": []
            }

    @classmethod
    def simulate_drop(
        cls,
        connector_id: int,
        sample_type: str,
        db: Session,
        user: Optional[User] = None,
        custom_filename: Optional[str] = None,
        custom_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates an incoming evidence drop from an external source system.
        Allows instant testing and verification of watch folders, email inboxes,
        and webhook pipelines without requiring external server dependencies.
        """
        conn = db.query(DataConnector).filter(DataConnector.id == connector_id).first()
        if not conn:
            raise ValueError(f"Connector #{connector_id} not found.")

        filename, file_bytes, evidence_cat = cls._generate_sample_artifact(
            sample_type, custom_filename, custom_content
        )

        c_type = conn.connector_type.lower()

        if c_type == "folder_watch":
            watch_dir = Path(conn.source_identifier).resolve()
            watch_dir.mkdir(parents=True, exist_ok=True)
            target_file = watch_dir / filename
            with open(target_file, "wb") as f_out:
                f_out.write(file_bytes)
            # Immediately poll the watch folder to ingest the dropped file
            return cls.poll_connector(connector_id, db, user)

        elif c_type == "email_inbox":
            inbox_dir = Path(conn.source_identifier).resolve()
            inbox_dir.mkdir(parents=True, exist_ok=True)
            eml_filename = f"drop_{filename}.eml"
            eml_content = (
                f"From: whistleblower.portal@evidence-secure.org\r\n"
                f"To: {conn.source_identifier}\r\n"
                f"Subject: Live Exhibit Submission: {filename}\r\n"
                f"Date: {datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"Simulated live tip-off transmission.\r\n"
                f"Extracted payload: {file_bytes.decode('utf-8', errors='ignore')[:300]}...\r\n"
            ).encode("utf-8")

            with open(inbox_dir / eml_filename, "wb") as f_eml:
                f_eml.write(eml_content)
            return cls.poll_connector(connector_id, db, user)

        elif c_type in ("webhook", "api_pull"):
            # Direct injection via handover
            connector = cls.get_connector(conn)
            item = IncomingEvidenceItem(
                raw_bytes=file_bytes,
                filename=filename,
                evidence_type=evidence_cat,
                source_system=f"{c_type}:{conn.source_identifier}",
                receipt_time=datetime.now(timezone.utc),
                metadata={"simulation": True, "sample_type": sample_type},
                custody_notes=f"Simulated {sample_type} delivery via {c_type} connector."
            )
            evidence = connector.handover(item, db, user)
            return {
                "success": True,
                "connector_id": conn.id,
                "connector_name": conn.name,
                "items_fetched": 1,
                "items_ingested": 1,
                "duplicates_skipped": 0,
                "errors_count": 0,
                "message": f"Successfully simulated {sample_type} drop into Exhibit #{evidence.id}.",
                "ingested_evidence_ids": [evidence.id]
            }

        else:
            raise ValueError(f"Unknown connector type: {c_type}")

    @staticmethod
    def _generate_sample_artifact(
        sample_type: str,
        custom_filename: Optional[str] = None,
        custom_content: Optional[str] = None
    ) -> tuple[str, bytes, str]:
        """
        Generates realistic sample evidence files for demonstration and testing.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if custom_content:
            fn = custom_filename or f"custom_evidence_{ts}.txt"
            return fn, custom_content.encode("utf-8"), "document"

        if sample_type == "cdr_export":
            filename = custom_filename or f"telco_cdr_dump_cell_tower_{ts}.csv"
            content = (
                "call_id,calling_number,called_number,timestamp,duration_sec,cell_tower_id,azimuth,imei,imsi\n"
                f"CDR-{ts}-001,9823014589,9890123456,2026-10-30 20:14:12,145,TWR-PUNE-KATRAJ-04,120,356789012345678,404450123456789\n"
                f"CDR-{ts}-002,9890123456,9823014589,2026-10-30 20:22:05,38,TWR-PUNE-KATRAJ-04,120,356789012345678,404450123456789\n"
                f"CDR-{ts}-003,9823014589,9822998877,2026-10-30 21:05:44,210,TWR-PUNE-HADAPSAR-02,240,356789012345678,404450123456789\n"
                f"CDR-{ts}-004,9822998877,9823014589,2026-10-30 21:30:19,89,TWR-PUNE-HADAPSAR-02,240,356789012345678,404450123456789\n"
            )
            return filename, content.encode("utf-8"), "forensic"

        elif sample_type == "lab_toxicology":
            filename = custom_filename or f"cfsl_chemical_forensics_report_{ts}.txt"
            content = (
                "GOVERNMENT OF MAHARASHTRA - FORENSIC SCIENCE LABORATORY\n"
                "CHEMICAL & TOXICOLOGY ANALYSIS REPORT\n"
                f"Reference No: CFSL/TOX/{ts}/EXP-09\n"
                f"Date of Receipt: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                "Subject: Chemical examination of cloth fibers and chemical residue.\n"
                "Findings: Traces of organophosphorus compound detected on Exhibit B.\n"
                "Chain of Custody Seal: CFSL-SEAL-88942-INTACT.\n"
                "Certified by: Senior Scientific Officer, State FSL.\n"
            )
            return filename, content.encode("utf-8"), "forensic"

        elif sample_type == "bank_statement":
            filename = custom_filename or f"bank_statement_neft_ledger_{ts}.csv"
            content = (
                "txn_id,account_number,date,description,debit,credit,balance,ref_terminal\n"
                f"TXN-{ts}-01,0094101004523,2026-10-29 18:30:00,ATM CASH WITHDRAWAL,10000.00,0.00,45320.00,ATM-KOTH-04\n"
                f"TXN-{ts}-02,0094101004523,2026-10-29 22:15:00,NEFT IMPS TRANSFER,50000.00,0.00,5320.00,MOB-BNK-99\n"
            )
            return filename, content.encode("utf-8"), "financial"

        elif sample_type == "cctv_metadata":
            filename = custom_filename or f"toll_plaza_cctv_log_{ts}.json"
            content = json.dumps({
                "camera_id": "PUNE-EXP-TOLL-04-NORTH",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "vehicle_registration": "MH-12-DE-4491",
                "confidence_score": 0.984,
                "lane_number": 3,
                "speed_kmh": 48.2,
                "anpr_verified": True
            }, indent=2)
            return filename, content.encode("utf-8"), "forensic"

        else:
            # General document
            filename = custom_filename or f"investigative_dispatch_memo_{ts}.txt"
            content = (
                f"POLICE HEADQUARTERS - INVESTIGATION DISPATCH\n"
                f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                f"Automated transmission received via live data connector.\n"
                f"Summary: Verified field telemetry and officer reports entered into case file.\n"
            )
            return filename, content.encode("utf-8"), "document"

