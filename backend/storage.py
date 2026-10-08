# backend/storage.py
"""
Storage abstraction module supporting:
- Local filesystem storage (with safe relative paths)
- Supabase Storage / S3 object storage compatibility
- Ingest-time raw byte SHA-256 fingerprinting
"""

import os
import uuid
import hashlib
from pathlib import Path
from typing import Tuple, Optional
import httpx

BACKEND_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "evidentia-evidence")


async def save_uploaded_file(file_content: bytes, original_filename: str) -> Tuple[str, int, str]:
    """
    Computes SHA-256 hash immediately over raw bytes, then persists to object storage or local disk.
    Returns:
        (storage_path_or_url, file_size_in_bytes, sha256_hash)
    """
    file_size = len(file_content)
    
    # 1. Compute SHA-256 fingerprint BEFORE any transformation
    sha256_hash = hashlib.sha256(file_content).hexdigest()

    file_extension = os.path.splitext(original_filename)[1]
    unique_name = f"{uuid.uuid4().hex}{file_extension}"

    # 2. Try Supabase Storage if configured
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            upload_endpoint = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{SUPABASE_BUCKET}/{unique_name}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    upload_endpoint,
                    content=file_content,
                    headers={
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "apikey": SUPABASE_KEY,
                        "Content-Type": "application/octet-stream"
                    }
                )
                if res.status_code in [200, 201]:
                    public_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{SUPABASE_BUCKET}/{unique_name}"
                    return (public_url, file_size, sha256_hash)
        except Exception as e:
            print(f"[!] Object storage upload failed ({e}), falling back to local persistent store.")

    # 3. Local persistent store fallback
    local_path = UPLOAD_DIR / unique_name
    local_path.write_bytes(file_content)
    relative_path = f"uploads/{unique_name}"
    
    return (relative_path, file_size, sha256_hash)
