"""
backend/upload_validator.py
===========================
Forensic Evidence Upload Validation Engine for Evidentia-AI.

Enforces:
1. Strict Whitelist of Allowed Forensic File Types:
   - PDF (.pdf)
   - Images (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff, .tif)
   - Audio (.mp3, .wav, .ogg, .flac, .m4a, .aac)
   - Video (.mp4, .mkv, .avi, .mov, .webm)
   - Text (.txt, .log, .json, .md)
   - CSV (.csv, .tsv)
   - Network Captures / PCAP (.pcap, .pcapng, .cap)
2. Deep Magic Byte / File Signature Verification:
   - Inspects real binary header signatures beyond trusting extensions.
   - Rejects executable files disguised as allowed extensions (e.g. PE/MZ, ELF, Mach-O).
3. Dual-Tier Storage Size Enforcement:
   - Maximum per-file size (default: 50 MB, configurable via MAX_FILE_SIZE_BYTES).
   - Maximum cumulative storage per case (default: 250 MB, configurable via MAX_CASE_STORAGE_BYTES).
4. Filename Sanitization & Directory Traversal Prevention:
   - Strips dangerous path separators, null bytes, and non-printable characters.
   - Normalizes extensions and truncates length safely.
5. Tamper-Evident Audit Logging:
   - Logs security warnings via Python logging.
   - Persists rejected upload attempts into the Merkle-chained audit ledger.
"""

import os
import re
import logging
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

logger = logging.getLogger("evidentia.upload_validator")

# ==============================================================================
# CONFIGURATION & THRESHOLDS
# ==============================================================================

# 50 MB per file limit by default
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", 50 * 1024 * 1024))

# 250 MB cumulative storage limit per case by default
MAX_CASE_STORAGE_BYTES = int(os.getenv("MAX_CASE_STORAGE_BYTES", 250 * 1024 * 1024))

# Allowed Extension Mappings
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf": "PDF",
    ".txt": "Text",
    ".log": "Text",
    ".json": "Text",
    ".md": "Text",
    ".csv": "CSV",
    ".tsv": "CSV",
    # Images
    ".jpg": "Image",
    ".jpeg": "Image",
    ".png": "Image",
    ".gif": "Image",
    ".webp": "Image",
    ".bmp": "Image",
    ".tiff": "Image",
    ".tif": "Image",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".ogg": "Audio",
    ".flac": "Audio",
    ".m4a": "Audio",
    ".aac": "Audio",
    # Video
    ".mp4": "Video",
    ".mkv": "Video",
    ".avi": "Video",
    ".mov": "Video",
    ".webm": "Video",
    # Network Captures
    ".pcap": "PCAP",
    ".pcapng": "PCAP",
    ".cap": "PCAP",
}

# Dangerous Binary Executable Signatures that must never enter the evidence vault
DISALLOWED_EXECUTABLE_SIGNATURES = [
    (b"\x4D\x5A", "Windows PE/DOS Executable (MZ)"),
    (b"\x7FELF", "Linux/UNIX Executable (ELF)"),
    (b"\xFE\xED\xFA\xCE", "Mach-O 32-bit Executable"),
    (b"\xFE\xED\xFA\xCF", "Mach-O 64-bit Executable"),
    (b"\xCE\xFA\xED\xFE", "Mach-O Executable (reversed)"),
    (b"\xCF\xFA\xED\xFE", "Mach-O 64-bit Executable (reversed)"),
    (b"\xCA\xFE\xBA\xBE", "Java Bytecode / Mach-O Fat Binary"),
    (b"\x4C\x00\x00\x00", "Windows Shortcut / Shell Link (LNK)"),
    (b"MSCF", "Microsoft Cabinet File (CAB)"),
]


# ==============================================================================
# FILENAME SANITIZATION
# ==============================================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes uploaded filename:
      - Strips directory traversal (prevents ../ or ..\\ injection).
      - Eliminates control characters, null bytes, and shell metacharacters.
      - Normalizes file extension to lowercase.
      - Restricts length to 200 characters while preserving extension.
    """
    if not filename or not isinstance(filename, str):
        return "unnamed_evidence.bin"

    # 1. Strip directory traversal paths (both POSIX and Windows separators)
    clean_name = os.path.basename(filename.replace("\\", "/"))
    
    # 2. Remove null bytes and control characters
    clean_name = re.sub(r"[\r\n\t\x00]", "", clean_name)
    
    # 3. Restrict characters to safe alphanumeric, underscores, hyphens, and periods
    clean_name = re.sub(r"[^\w\s\.\-\(\)]", "_", clean_name).strip()

    # 4. Strip leading dots to prevent hidden unix files
    clean_name = clean_name.lstrip(".")
    if not clean_name:
        clean_name = "unnamed_evidence"

    # 5. Extract and normalize extension
    name, ext = os.path.splitext(clean_name)
    safe_ext = ext[:12].lower()
    safe_base = name[:180].strip() or "evidence"

    return f"{safe_base}{safe_ext}"


# ==============================================================================
# MAGIC BYTE / FILE SIGNATURE INSPECTION
# ==============================================================================

def detect_file_signature(file_bytes: bytes, extension: str) -> Tuple[bool, str, str]:
    """
    Examines real binary signatures (magic bytes) to verify that the raw byte content
    matches the declared extension and is a permitted forensic evidence type.

    Returns:
        (is_valid, detected_category, error_reason)
    """
    if not file_bytes:
        return False, "Unknown", "File is empty (0 bytes). Forensic evidence must contain data."

    ext = extension.lower().strip()
    sample_16 = file_bytes[:16]
    sample_1k = file_bytes[:1024]

    # Step 1: Reject any binary starting with an executable signature
    for sig, desc in DISALLOWED_EXECUTABLE_SIGNATURES:
        if sample_16.startswith(sig):
            return False, "Executable", f"Dangerous executable binary signature detected ({desc}). Upload rejected for forensic security."

    # Step 2: Signature verification by declared extension category

    # A. PDF
    if ext == ".pdf":
        # Standard PDF magic header: %PDF-
        if sample_1k.startswith(b"%PDF-") or b"%PDF-" in sample_1k:
            return True, "Document", ""
        return False, "Invalid_PDF", "File signature validation failed: Declared as .pdf but lacks the valid '%PDF-' header."

    # B. Images
    if ext in [".jpg", ".jpeg"]:
        if sample_16.startswith(b"\xFF\xD8\xFF"):
            return True, "Image", ""
        return False, "Invalid_JPEG", "File signature validation failed: Declared as JPEG but lacks valid JPEG magic bytes (FF D8 FF)."

    if ext == ".png":
        if sample_16.startswith(b"\x89PNG\r\n\x1a\n"):
            return True, "Image", ""
        return False, "Invalid_PNG", "File signature validation failed: Declared as PNG but lacks valid PNG magic bytes."

    if ext == ".gif":
        if sample_16.startswith(b"GIF87a") or sample_16.startswith(b"GIF89a"):
            return True, "Image", ""
        return False, "Invalid_GIF", "File signature validation failed: Declared as GIF but lacks valid GIF magic bytes."

    if ext == ".webp":
        if sample_16.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
            return True, "Image", ""
        return False, "Invalid_WEBP", "File signature validation failed: Declared as WEBP but lacks valid RIFF/WEBP header."

    if ext == ".bmp":
        if sample_16.startswith(b"BM"):
            return True, "Image", ""
        return False, "Invalid_BMP", "File signature validation failed: Declared as BMP but lacks valid 'BM' magic header."

    if ext in [".tiff", ".tif"]:
        if sample_16.startswith(b"II*\x00") or sample_16.startswith(b"MM\x00*"):
            return True, "Image", ""
        return False, "Invalid_TIFF", "File signature validation failed: Declared as TIFF but lacks valid TIFF endian header."

    # C. Audio
    if ext == ".mp3":
        # ID3 container or MPEG audio sync frame
        if sample_16.startswith(b"ID3") or sample_16[:2] in (b"\xFF\xFB", b"\xFF\xF3", b"\xFF\xF2", b"\xFF\xE3"):
            return True, "Audio", ""
        return False, "Invalid_MP3", "File signature validation failed: Declared as MP3 but lacks valid ID3 tag or MPEG audio sync frame."

    if ext == ".wav":
        if sample_16.startswith(b"RIFF") and file_bytes[8:12] == b"WAVE":
            return True, "Audio", ""
        return False, "Invalid_WAV", "File signature validation failed: Declared as WAV but lacks valid RIFF/WAVE header."

    if ext == ".ogg":
        if sample_16.startswith(b"OggS"):
            return True, "Audio", ""
        return False, "Invalid_OGG", "File signature validation failed: Declared as OGG but lacks valid 'OggS' container header."

    if ext == ".flac":
        if sample_16.startswith(b"fLaC"):
            return True, "Audio", ""
        return False, "Invalid_FLAC", "File signature validation failed: Declared as FLAC but lacks valid 'fLaC' stream marker."

    if ext in [".m4a", ".aac"]:
        if file_bytes[4:8] == b"ftyp" and file_bytes[8:12] in (b"M4A ", b"mp42", b"isom", b"dash"):
            return True, "Audio", ""
        if sample_16[:2] in (b"\xFF\xF1", b"\xFF\xF9"):  # ADTS AAC
            return True, "Audio", ""
        return False, "Invalid_Audio", "File signature validation failed: Declared as M4A/AAC but lacks valid MPEG-4 audio container."

    # D. Video
    if ext in [".mp4", ".mov"]:
        if file_bytes[4:8] == b"ftyp" or file_bytes[4:8] == b"moov" or sample_16.startswith(b"\x00\x00\x00"):
            return True, "Video", ""
        return False, "Invalid_MP4", "File signature validation failed: Declared as MP4/MOV but lacks valid ISO/QuickTime container header."

    if ext in [".mkv", ".webm"]:
        if sample_16.startswith(b"\x1A\x45\xDF\xA3"):  # Matroska / EBML header
            return True, "Video", ""
        return False, "Invalid_MKV", "File signature validation failed: Declared as MKV/WEBM but lacks valid EBML container header."

    if ext == ".avi":
        if sample_16.startswith(b"RIFF") and file_bytes[8:12] in (b"AVI ", b"AVIX"):
            return True, "Video", ""
        return False, "Invalid_AVI", "File signature validation failed: Declared as AVI but lacks valid RIFF/AVI header."

    # E. Network Packet Captures (PCAP)
    if ext in [".pcap", ".pcapng", ".cap"]:
        # Standard libpcap microsecond
        if sample_16.startswith(b"\xd4\xc3\xb2\xa1") or sample_16.startswith(b"\xa1\xb2\xc3\xd4"):
            return True, "PCAP", ""
        # Nanosecond libpcap
        if sample_16.startswith(b"\x4d\x3c\xb2\xa1") or sample_16.startswith(b"\xa1\xb2\x3c\x4d"):
            return True, "PCAP", ""
        # PCAPNG Block header: 0x0A0D0D0A
        if sample_16.startswith(b"\x0a\x0d\x0d\x0a"):
            return True, "PCAP", ""
        return False, "Invalid_PCAP", "File signature validation failed: Declared as PCAP/PCAPNG but lacks valid packet capture magic bytes."

    # F. Text & CSV Files (.txt, .log, .json, .md, .csv, .tsv)
    if ext in [".txt", ".log", ".json", ".md", ".csv", ".tsv"]:
        # Check text decodability without binary null bytes
        try:
            sample_text = sample_1k.decode("utf-8")
        except UnicodeDecodeError:
            try:
                sample_text = sample_1k.decode("latin-1")
            except Exception:
                return False, "Invalid_Text", "File signature validation failed: Content is not valid text (failed text decoding)."

        # Reject binary files containing null bytes in initial sample
        if "\x00" in sample_text:
            return False, "Binary_In_Text", "File signature validation failed: Binary null bytes detected inside declared text file."

        cat = "CSV" if ext in [".csv", ".tsv"] else "Document"
        return True, cat, ""

    return False, "Unsupported", f"File extension '{ext}' is not permitted. Only forensic evidence types (PDF, Images, Audio, Video, Text, CSV, PCAP) are allowed."


# ==============================================================================
# CENTRAL VALIDATION & ENFORCEMENT ENGINE
# ==============================================================================

class UploadValidationResult:
    def __init__(
        self,
        sanitized_filename: str,
        detected_category: str,
        file_size: int,
        sha256_hash: str
    ):
        self.sanitized_filename = sanitized_filename
        self.detected_category = detected_category
        self.file_size = file_size
        self.sha256_hash = sha256_hash


def validate_evidence_upload(
    file_bytes: bytes,
    original_filename: str,
    case_id: int,
    db: Session,
    user: Any
) -> UploadValidationResult:
    """
    Executes end-to-end security and forensic validation on an uploaded exhibit.

    Checks:
      1. Non-empty file check.
      2. Per-file maximum size (MAX_FILE_SIZE_BYTES).
      3. Cumulative case storage limit (MAX_CASE_STORAGE_BYTES).
      4. Whitelisted extension check.
      5. Binary magic byte / signature check.
      6. Filename sanitization.

    If any validation check fails:
      - Logs a security warning.
      - Writes a rejection event to the Merkle audit ledger.
      - Raises FastAPI HTTPException (400 Bad Request or 413 Payload Too Large).
    """
    import hashlib
    from models import Evidence
    from audit_engine import log_audit_event

    file_size = len(file_bytes)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    def _reject(status_code: int, reason: str):
        logger.warning(
            f"[UPLOAD REJECTED] Case #{case_id} | User: {getattr(user, 'email', 'unknown')} | "
            f"File: '{original_filename}' | Size: {file_size:,} bytes | SHA256: {sha256_hash[:12]}... | "
            f"Reason: {reason}"
        )
        try:
            log_audit_event(
                db=db,
                action_type="EVIDENCE_UPLOAD_REJECTED",
                target_type="evidence",
                target_id=None,
                description=f"Rejected upload '{original_filename}' ({file_size:,} bytes): {reason}",
                user_id=getattr(user, "id", None),
                user_name=getattr(user, "full_name", "Unknown"),
                user_role=getattr(user, "role", "unknown"),
                case_id=case_id,
                before_value=f"OriginalFilename: {original_filename}",
                after_value=f"RejectionReason: {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to record rejection in audit ledger: {e}")

        raise HTTPException(status_code=status_code, detail=reason)

    # 1. Non-empty check
    if file_size == 0:
        _reject(status.HTTP_400_BAD_REQUEST, "Upload rejected: File is empty (0 bytes).")

    # 2. Maximum size per file check
    if file_size > MAX_FILE_SIZE_BYTES:
        mb_size = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        _reject(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File size exceeds maximum allowed limit. Uploaded file is {mb_size:.1f} MB, maximum permitted is {max_mb:.1f} MB."
        )

    # 3. Maximum cumulative storage per case check
    current_case_bytes = (
        db.query(func.coalesce(func.sum(Evidence.file_size), 0))
        .filter(Evidence.case_id == case_id, Evidence.is_deleted == False)
        .scalar()
        or 0
    )
    if (current_case_bytes + file_size) > MAX_CASE_STORAGE_BYTES:
        cur_mb = current_case_bytes / (1024 * 1024)
        att_mb = file_size / (1024 * 1024)
        max_case_mb = MAX_CASE_STORAGE_BYTES / (1024 * 1024)
        _reject(
            status.HTTP_400_BAD_REQUEST,
            f"Cumulative case storage limit exceeded for Case #{case_id}. "
            f"Current case storage: {cur_mb:.1f} MB, attempted addition: {att_mb:.1f} MB, "
            f"maximum case quota: {max_case_mb:.1f} MB."
        )

    # 4. Filename sanitization and extension whitelisting
    sanitized = sanitize_filename(original_filename)
    _, ext = os.path.splitext(sanitized)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        allowed_list_str = "PDF (.pdf), Images (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff), Audio (.mp3, .wav, .ogg, .flac, .m4a), Video (.mp4, .mkv, .avi, .mov, .webm), Text (.txt, .log, .json, .md), CSV (.csv, .tsv), PCAP (.pcap, .pcapng, .cap)"
        _reject(
            status.HTTP_400_BAD_REQUEST,
            f"File type '{ext}' is not permitted. Permitted forensic evidence formats: {allowed_list_str}."
        )

    # 5. Deep Magic Byte / File Signature Check
    is_valid_sig, detected_cat, sig_error = detect_file_signature(file_bytes, ext)
    if not is_valid_sig:
        _reject(status.HTTP_400_BAD_REQUEST, sig_error)

    logger.info(
        f"[UPLOAD VALIDATED] Case #{case_id} | File: '{sanitized}' | Size: {file_size:,} bytes | "
        f"Category: {detected_cat} | SHA256: {sha256_hash[:12]}..."
    )

    return UploadValidationResult(
        sanitized_filename=sanitized,
        detected_category=detected_cat,
        file_size=file_size,
        sha256_hash=sha256_hash
    )

