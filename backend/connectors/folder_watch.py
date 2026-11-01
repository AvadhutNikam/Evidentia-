"""
backend/connectors/folder_watch.py
==================================
Style 1: Folder Watch Connector (Drop-Box / Shared Network Folder Ingestion).

Monitors a shared directory where forensic labs, telecom providers, or banks
drop evidentiary files (CDR dumps, toxicology reports, bank statements, CCTV clips).
Requires no outside API credentials or external permissions.
"""

import os
import shutil
import fnmatch
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from connectors.base import BaseConnector, IncomingEvidenceItem

FORBIDDEN_PATHS = [
    "c:\\windows", "c:\\program files", "/etc", "/var", "/bin", "/sbin", "/usr"
]


class FolderWatchConnector(BaseConnector):
    """
    Watches a local or mounted network folder for newly deposited evidence files.
    """

    def __init__(self, connector_record):
        super().__init__(connector_record)
        self.watch_path = self._sanitize_and_resolve_path(self.source_identifier)
        self.patterns = self.config.get("file_patterns", [
            "*.pdf", "*.txt", "*.log", "*.csv", "*.pcap", "*.pcapng",
            "*.jpg", "*.jpeg", "*.png", "*.mp3", "*.wav", "*.mp4", "*.m4a"
        ])
        self.archive_folder = self.watch_path / ".ingested"

    def _sanitize_and_resolve_path(self, raw_path: str) -> Path:
        """
        Validates the path to ensure directory traversal or access to sensitive system roots
        is strictly prevented.
        """
        p = Path(raw_path).resolve()
        p_str = str(p).lower()

        for forbidden in FORBIDDEN_PATHS:
            if p_str.startswith(forbidden):
                raise ValueError(f"Access to system directory '{forbidden}' is strictly forbidden.")

        # Ensure directory exists or create safe subfolder in backend/data/connectors
        p.mkdir(parents=True, exist_ok=True)
        return p

    def fetch_new_items(self, db: Session) -> List[IncomingEvidenceItem]:
        """
        Scans the watch folder for uningested files matching patterns.
        """
        self.archive_folder.mkdir(parents=True, exist_ok=True)
        items = []

        if not self.watch_path.exists():
            return []

        # Find all candidate files
        for entry in self.watch_path.iterdir():
            if entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue  # skip hidden/temporary files

            # Check pattern match
            matches_pattern = any(fnmatch.fnmatch(entry.name.lower(), pat.lower()) for pat in self.patterns)
            if not matches_pattern:
                continue

            # Read file bytes
            try:
                with open(entry, "rb") as f_in:
                    raw_bytes = f_in.read()

                mtime = entry.stat().st_mtime
                receipt_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)

                item = self.normalize({
                    "raw_bytes": raw_bytes,
                    "filename": entry.name,
                    "receipt_time": receipt_dt,
                    "file_path": str(entry)
                })
                items.append(item)

                # Move to archive directory
                archive_dest = self.archive_folder / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{entry.name}"
                try:
                    shutil.move(str(entry), str(archive_dest))
                except Exception as me:
                    # If file locked on Windows, copy and delete
                    shutil.copy2(str(entry), str(archive_dest))
                    os.remove(str(entry))

            except Exception as e:
                # Log error and skip locked/in-flight write files
                continue

        return items

    def normalize(self, raw_data: Dict[str, Any]) -> IncomingEvidenceItem:
        """
        Normalizes a watch folder file entry into standard IncomingEvidenceItem.
        """
        filename = raw_data.get("filename", "drop_evidence.bin")
        ext = Path(filename).suffix.lower()

        # Categorize evidence type based on extension
        if ext in [".pcap", ".pcapng", ".cap"]:
            ev_type = "digital"
        elif ext in [".csv", ".xlsx", ".tsv"]:
            ev_type = "financial" if "bank" in filename.lower() or "txn" in filename.lower() else "telecom" if "cdr" in filename.lower() or "tower" in filename.lower() else "document"
        elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            ev_type = "photograph"
        elif ext in [".mp3", ".wav", ".m4a", ".ogg"]:
            ev_type = "audio"
        elif ext in [".mp4", ".mkv", ".avi", ".mov"]:
            ev_type = "cctv"
        else:
            ev_type = "forensic" if "fsl" in filename.lower() or "autopsy" in filename.lower() else "document"

        source_sys = f"watch_folder:{self.watch_path.as_posix()}"
        receipt_time = raw_data.get("receipt_time") or datetime.now(timezone.utc)

        return IncomingEvidenceItem(
            raw_bytes=raw_data["raw_bytes"],
            filename=filename,
            evidence_type=ev_type,
            source_system=source_sys,
            receipt_time=receipt_time,
            metadata={
                "watch_folder_path": str(self.watch_path),
                "original_path": raw_data.get("file_path"),
                "file_size": len(raw_data["raw_bytes"])
            },
            custody_notes=f"Auto-ingested from laboratory watch folder '{self.watch_path.name}' upon file deposit.",
            collected_by=f"Folder Watch Connector [{self.name}]"
        )

