"""
backend/connectors/__init__.py
==============================
Live Evidence Connectors for Automated Evidence Ingestion.

Supports:
  1. Folder Watch (Drop-Box / Shared directory ingestion)
  2. Email Inbox (.eml parsing & whistleblower submissions)
  3. Webhook Push (Real-time HTTP push events)
  4. Scheduled API Pull (Authorized laboratory/CMS polling)
"""

from connectors.base import BaseConnector, IncomingEvidenceItem
from connectors.folder_watch import FolderWatchConnector
from connectors.email_inbox import EmailInboxConnector
from connectors.webhook import WebhookConnector
from connectors.api_pull import ApiPullConnector
from connectors.manager import ConnectorManager

__all__ = [
    "BaseConnector",
    "IncomingEvidenceItem",
    "FolderWatchConnector",
    "EmailInboxConnector",
    "WebhookConnector",
    "ApiPullConnector",
    "ConnectorManager",
]

