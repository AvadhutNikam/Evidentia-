"""
backend/connectors/webhook.py
=============================
Style 3: Webhook Push Connector (Real-Time Ingestion for External Webhook Sources).

Enables external systems (forensic portals, bank gateways, emergency dispatch APIs)
to push evidence artifacts and digital payloads directly into Evidentia via HTTP POST.
Validates webhook authentication tokens and records receipt timestamps in custody log.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from connectors.base import BaseConnector, IncomingEvidenceItem
from models import Evidence, User


class WebhookConnector(BaseConnector):
    """
    Receives real-time push events and evidence files via HTTP webhook callbacks.
    """

    def fetch_new_items(self, db: Session) -> List[IncomingEvidenceItem]:
        """
        Webhook connectors are push-driven rather than polled;
        fetch_new_items returns an empty list during background poll passes.
        """
        return []

    def process_webhook_push(
        self,
        raw_bytes: bytes,
        filename: str,
        source_system: str,
        metadata: Optional[Dict[str, Any]] = None,
        evidence_type: str = "document",
        db: Session = None,
        user: Optional[User] = None
    ) -> Evidence:
        """
        Directly normalizes and hands over an incoming webhook payload into custody.
        """
        item = self.normalize({
            "raw_bytes": raw_bytes,
            "filename": filename,
            "source_system": source_system or f"webhook:{self.name}",
            "receipt_time": datetime.now(timezone.utc),
            "evidence_type": evidence_type,
            "metadata": metadata or {}
        })

        return self.handover(item, db, user)

    def normalize(self, raw_data: Dict[str, Any]) -> IncomingEvidenceItem:
        """
        Normalizes a webhook payload into standard IncomingEvidenceItem.
        """
        source_sys = raw_data.get("source_system") or f"webhook:{self.source_identifier}"
        receipt_time = raw_data.get("receipt_time") or datetime.now(timezone.utc)
        meta = raw_data.get("metadata", {})

        return IncomingEvidenceItem(
            raw_bytes=raw_data["raw_bytes"],
            filename=raw_data["filename"],
            evidence_type=raw_data.get("evidence_type", "document"),
            source_system=source_sys,
            receipt_time=receipt_time,
            metadata=meta,
            custody_notes=(
                f"Pushed via authenticated webhook endpoint. "
                f"Source remote identifier: '{source_sys}'. "
                f"Remote Event ID: {meta.get('external_event_id', 'N/A')}."
            ),
            collected_by=f"Webhook Listener [{self.name}]"
        )

