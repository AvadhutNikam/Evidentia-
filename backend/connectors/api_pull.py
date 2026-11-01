"""
backend/connectors/api_pull.py
==============================
Style 2: Scheduled API Pull Connector (Case-Management & Laboratory Portal Ingestion).

Polls external authorized forensic laboratory portals or agency case management systems (CMS)
on a scheduled interval. Fetches newly released exhibit manifests and evidence payloads.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from connectors.base import BaseConnector, IncomingEvidenceItem

logger = logging.getLogger("evidentia.connectors.api")


class ApiPullConnector(BaseConnector):
    """
    Polls a designated REST API endpoint for newly certified evidence artifacts.
    """

    def fetch_new_items(self, db: Session) -> List[IncomingEvidenceItem]:
        """
        Polls the remote API endpoint for pending evidence items.
        """
        endpoint_url = self.source_identifier
        headers = self.config.get("headers", {})
        if "api_key" in self.config:
            headers["X-API-Key"] = self.config["api_key"]
        elif "token" in self.config:
            headers["Authorization"] = f"Bearer {self.config['token']}"

        items = []

        # If endpoint is a mock or local simulator
        if "mock" in endpoint_url.lower() or "local" in endpoint_url.lower():
            mock_items = self.config.get("mock_artifacts", [])
            for m in mock_items:
                items.append(self.normalize(m))
            return items

        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(endpoint_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_items = data if isinstance(data, list) else data.get("artifacts", data.get("exhibits", []))
                    for item_data in raw_items:
                        items.append(self.normalize(item_data))
                else:
                    logger.warning(f"API pull returned HTTP {resp.status_code} from {endpoint_url}")
        except Exception as e:
            logger.error(f"Failed to poll remote API connector '{self.name}': {e}")

        return items

    def normalize(self, raw_data: Dict[str, Any]) -> IncomingEvidenceItem:
        """
        Normalizes a remote API JSON exhibit object into standard IncomingEvidenceItem.
        """
        filename = raw_data.get("filename", "api_evidence.bin")
        content_b64 = raw_data.get("content_base64", "")
        if content_b64:
            raw_bytes = base64.b64decode(content_b64)
        elif "text" in raw_data:
            raw_bytes = raw_data["text"].encode("utf-8")
        else:
            raw_bytes = raw_data.get("raw_bytes", b"")

        ext_id = raw_data.get("artifact_id", raw_data.get("id"))
        receipt_time = datetime.now(timezone.utc)
        if "created_at" in raw_data:
            try:
                receipt_time = datetime.fromisoformat(raw_data["created_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        source_sys = f"api_pull:{self.source_identifier}"

        return IncomingEvidenceItem(
            raw_bytes=raw_bytes,
            filename=filename,
            evidence_type=raw_data.get("evidence_type", "document"),
            source_system=source_sys,
            receipt_time=receipt_time,
            metadata={
                "api_endpoint": self.source_identifier,
                "external_artifact_id": ext_id,
                "api_metadata": raw_data.get("metadata", {})
            },
            custody_notes=(
                f"Pulled from external system API '{self.source_identifier}'. "
                f"External Artifact Reference: {ext_id or 'N/A'}."
            ),
            collected_by=f"API Pull Worker [{self.name}]"
        )

