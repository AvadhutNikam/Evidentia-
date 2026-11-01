"""
backend/connectors/email_inbox.py
=================================
Email Tip-Off & Whistleblower Inbox Connector.

Parses standard RFC 822 / MIME (.eml) email deposits or tip-off inbox feeds.
Extracts email metadata (sender, subject, timestamp, body) and attached forensic exhibits
(photos, documents, audio clips, leak archives).
Requires no outside API credentials or external permissions.
"""

import os
import shutil
import email
from email import policy
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from connectors.base import BaseConnector, IncomingEvidenceItem


class EmailInboxConnector(BaseConnector):
    """
    Monitors an email inbox drop folder for .eml messages sent by informants,
    whistleblowers, or automated alert gateways.
    """

    def __init__(self, connector_record):
        super().__init__(connector_record)
        self.inbox_path = Path(self.source_identifier).resolve()
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.archive_folder = self.inbox_path / ".ingested"
        self.archive_folder.mkdir(parents=True, exist_ok=True)

    def fetch_new_items(self, db: Session) -> List[IncomingEvidenceItem]:
        """
        Scans the inbox folder for .eml files and extracts evidence items.
        """
        items = []
        if not self.inbox_path.exists():
            return []

        for entry in self.inbox_path.iterdir():
            if entry.is_dir() or entry.name.startswith("."):
                continue

            if not entry.name.lower().endswith((".eml", ".msg", ".email")):
                continue

            try:
                with open(entry, "rb") as f_in:
                    raw_email_bytes = f_in.read()

                extracted_items = self.parse_eml_bytes(raw_email_bytes, entry.name)
                items.extend(extracted_items)

                # Move parsed email to .ingested
                archive_dest = self.archive_folder / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{entry.name}"
                try:
                    shutil.move(str(entry), str(archive_dest))
                except Exception:
                    shutil.copy2(str(entry), str(archive_dest))
                    os.remove(str(entry))

            except Exception as e:
                continue

        return items

    def parse_eml_bytes(self, raw_bytes: bytes, source_file: str = "tip.eml") -> List[IncomingEvidenceItem]:
        """
        Parses raw email bytes into one or more IncomingEvidenceItem objects
        (one per attachment, or one for the body text if no attachments exist).
        """
        items = []
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)

        from_addr = str(msg.get("From", "anonymous-tipster@evidentia.local")).strip()
        subject = str(msg.get("Subject", "Evidence Tip-off Submission")).strip()
        date_hdr = msg.get("Date")

        # Parse receipt timestamp
        receipt_dt = datetime.now(timezone.utc)
        if date_hdr:
            try:
                receipt_dt = email.utils.parsedate_to_datetime(str(date_hdr))
                if receipt_dt.tzinfo is None:
                    receipt_dt = receipt_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Extract body text
        body_text = ""
        try:
            body = msg.get_body(preferencelist=('plain', 'html'))
            if body:
                body_text = body.get_content()
        except Exception:
            body_text = ""

        # Extract attachments
        attachments = []
        for part in msg.iter_attachments():
            fn = part.get_filename() or f"attachment_{len(attachments)+1}.bin"
            payload = part.get_payload(decode=True)
            if payload:
                attachments.append((fn, payload, part.get_content_type()))

        source_sys = f"email_inbox:{from_addr}"

        if attachments:
            for fn, data, ctype in attachments:
                items.append(self.normalize({
                    "raw_bytes": data,
                    "filename": fn,
                    "from_addr": from_addr,
                    "subject": subject,
                    "receipt_time": receipt_dt,
                    "content_type": ctype,
                    "body_excerpt": body_text[:500],
                    "email_filename": source_file
                }))
        elif body_text.strip():
            # If no attachment, treat email body itself as a tip statement text exhibit
            sanitized_subj = "".join(c for c in subject if c.isalnum() or c in " _-")[:30].strip() or "tip_statement"
            fn = f"tip_{sanitized_subj}.txt"
            tip_content = f"--- TIP-OFF EMAIL EXHIBIT ---\nFrom: {from_addr}\nSubject: {subject}\nDate: {receipt_dt.isoformat()}\n\n{body_text}".encode("utf-8")
            items.append(self.normalize({
                "raw_bytes": tip_content,
                "filename": fn,
                "from_addr": from_addr,
                "subject": subject,
                "receipt_time": receipt_dt,
                "content_type": "text/plain",
                "body_excerpt": body_text[:500],
                "email_filename": source_file
            }))

        return items

    def normalize(self, raw_data: Dict[str, Any]) -> IncomingEvidenceItem:
        """
        Normalizes email attachment or statement into standard IncomingEvidenceItem.
        """
        filename = raw_data.get("filename", "email_evidence.bin")
        ext = Path(filename).suffix.lower()

        if ext in [".jpg", ".jpeg", ".png"]:
            ev_type = "photograph"
        elif ext in [".pdf", ".doc", ".docx"]:
            ev_type = "document"
        elif ext in [".mp3", ".wav", ".m4a"]:
            ev_type = "audio"
        elif ext in [".csv", ".xlsx"]:
            ev_type = "financial" if "bank" in filename.lower() else "telecom"
        else:
            ev_type = "witness" if "tip" in filename.lower() else "document"

        from_addr = raw_data.get("from_addr", "anonymous_tip")
        source_sys = f"email_inbox:{from_addr}"

        return IncomingEvidenceItem(
            raw_bytes=raw_data["raw_bytes"],
            filename=filename,
            evidence_type=ev_type,
            source_system=source_sys,
            receipt_time=raw_data.get("receipt_time") or datetime.now(timezone.utc),
            metadata={
                "sender": from_addr,
                "subject": raw_data.get("subject", ""),
                "email_file": raw_data.get("email_filename"),
                "body_excerpt": raw_data.get("body_excerpt", "")
            },
            custody_notes=f"Extracted from tip email sent by '{from_addr}' (Subject: '{raw_data.get('subject', '')}').",
            collected_by=f"Email Tip-off Gateway [{self.name}]"
        )

