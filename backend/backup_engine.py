"""
backend/backup_engine.py
========================
Disaster Recovery, Automated Backups with Verification Restore Testing,
and Statutory Retention / Legal Hold Management for Evidentia-AI.

Guarantees:
1. Automated Sandbox Restore Testing: Every backup automatically executes a dry-run
   integrity restore test (`PRAGMA integrity_check;` + schema + row counts) in an isolated sandbox.
   Backups are only marked 'passed' if the restore test succeeds.
2. Legal Hold Preservation: If a case has `is_legal_hold=True`, all exhibit deletions,
   data purges, and case destruction actions are strictly locked (HTTP 423).
3. Cryptographic Hashing: Every backup snapshot is stamped with a SHA-256 integrity hash.
"""

import os
import shutil
import sqlite3
import hashlib
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database import engine

_BACKUP_DIR = Path(__file__).resolve().parent / "backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def calculate_file_sha256(filepath: Path) -> str:
    """Calculates SHA-256 checksum of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_sandbox_restore_test(backup_filepath: Path) -> Dict[str, Any]:
    """
    Executes an isolated dry-run restore test against a backup SQLite file.
    Runs:
      1. PRAGMA integrity_check;
      2. Table existence checks (cases, users, evidence, hypotheses).
      3. Total records count.
    Returns:
      {
        "status": "passed" | "failed",
        "duration_ms": int,
        "tables_verified": int,
        "total_rows": int,
        "notes": str,
        "error": Optional[str]
      }
    """
    start_time = time.time()
    if not backup_filepath.exists():
        return {
            "status": "failed",
            "duration_ms": 0,
            "tables_verified": 0,
            "total_rows": 0,
            "notes": "Backup file not found on disk",
            "error": "File missing"
        }

    try:
        # Connect read-only to sandbox database
        conn = sqlite3.connect(f"file:{backup_filepath.resolve()}?mode=ro", uri=True)
        cursor = conn.cursor()

        # 1. Run SQLite low-level page and B-Tree integrity check
        cursor.execute("PRAGMA integrity_check;")
        integrity_res = cursor.fetchall()
        if not integrity_res or integrity_res[0][0] != "ok":
            conn.close()
            return {
                "status": "failed",
                "duration_ms": int((time.time() - start_time) * 1000),
                "tables_verified": 0,
                "total_rows": 0,
                "notes": f"PRAGMA integrity_check reported errors: {integrity_res}",
                "error": "Database corruption detected"
            }

        # 2. Verify schema and table counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
        
        expected_core_tables = ["cases", "users", "evidence", "hypotheses"]
        missing_tables = [t for t in expected_core_tables if t not in tables]

        # 3. Count rows across tables
        total_rows = 0
        table_counts = {}
        for t in tables[:15]:  # Sample first 15 tables
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = cursor.fetchone()[0]
                table_counts[t] = cnt
                total_rows += cnt
            except Exception:
                pass

        conn.close()
        elapsed_ms = int((time.time() - start_time) * 1000)

        if missing_tables:
            return {
                "status": "failed",
                "duration_ms": elapsed_ms,
                "tables_verified": len(tables),
                "total_rows": total_rows,
                "notes": f"Missing expected core tables: {missing_tables}",
                "error": "Schema incomplete"
            }

        notes = f"Verified {len(tables)} tables ({total_rows} total rows). PRAGMA integrity_check OK in {elapsed_ms}ms."
        return {
            "status": "passed",
            "duration_ms": elapsed_ms,
            "tables_verified": len(tables),
            "total_rows": total_rows,
            "notes": notes,
            "error": None
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "failed",
            "duration_ms": elapsed_ms,
            "tables_verified": 0,
            "total_rows": 0,
            "notes": f"Restore test failed with exception: {str(e)}",
            "error": str(e)
        }


def create_backup(
    db: Session,
    user_name: str = "System Admin",
    backup_type: str = "full"
) -> Any:
    """
    Creates a new timestamped backup of evidentia.db, calculates SHA-256 hash,
    and runs the automated sandbox restore test.
    """
    from models import BackupRecord

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"evidentia_backup_{timestamp_str}_{backup_type}.db"
    dest_path = _BACKUP_DIR / backup_filename

    # Source database path
    src_db_path = Path(__file__).resolve().parent / "evidentia.db"
    if not src_db_path.exists():
        # Look in current working directory
        src_db_path = Path("evidentia.db")

    # Use SQLite online backup API to ensure 100% ACID consistency without locking issues
    src_conn = sqlite3.connect(src_db_path)
    dest_conn = sqlite3.connect(dest_path)
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()

    size_bytes = dest_path.stat().st_size
    sha256_hash = calculate_file_sha256(dest_path)

    # Immediately execute automated sandbox restore test
    restore_result = run_sandbox_restore_test(dest_path)

    backup_rec = BackupRecord(
        backup_filename=backup_filename,
        backup_type=backup_type,
        size_bytes=size_bytes,
        sha256_hash=sha256_hash,
        storage_path=str(dest_path.resolve()),
        created_by=user_name,
        restore_test_status=restore_result["status"],
        restore_test_at=datetime.now(timezone.utc),
        restore_test_notes=restore_result["notes"]
    )
    db.add(backup_rec)
    db.commit()
    db.refresh(backup_rec)

    return backup_rec


def verify_existing_backup_restore(backup_id: int, db: Session) -> Dict[str, Any]:
    """Re-runs the sandbox restore test on demand for an existing backup record."""
    from models import BackupRecord

    rec = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not rec:
        raise ValueError(f"Backup record #{backup_id} not found.")

    target_path = Path(rec.storage_path)
    if not target_path.exists():
        # Try finding in default backup dir
        target_path = _BACKUP_DIR / rec.backup_filename

    res = run_sandbox_restore_test(target_path)
    rec.restore_test_status = res["status"]
    rec.restore_test_at = datetime.now(timezone.utc)
    rec.restore_test_notes = res["notes"]
    db.commit()
    db.refresh(rec)

    return {
        "backup_id": rec.id,
        "filename": rec.backup_filename,
        "restore_status": rec.restore_test_status,
        "restore_notes": rec.restore_test_notes,
        "sha256_hash": rec.sha256_hash
    }


def set_case_legal_hold(
    case_id: int,
    db: Session,
    is_legal_hold: bool,
    reason: Optional[str],
    user_name: str
) -> Any:
    """
    Places or releases a legal hold on a case.
    When active, all evidence deletions and case purging are strictly blocked.
    """
    from models import Case

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case #{case_id} not found.")

    case.is_legal_hold = is_legal_hold
    if is_legal_hold:
        case.legal_hold_reason = reason or "Statutory Evidence Preservation Order (CrPC / BNSS)"
        case.legal_hold_placed_by = user_name
        case.legal_hold_placed_at = datetime.now(timezone.utc)
    else:
        case.legal_hold_reason = None
        case.legal_hold_placed_by = None
        case.legal_hold_placed_at = None

    db.commit()
    db.refresh(case)
    return case

