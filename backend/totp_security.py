"""
backend/totp_security.py
========================
Two-Factor Authentication (2FA) security module implementing RFC 6238 Time-Based
One-Time Password (TOTP) standard and hashed one-time backup recovery codes.
"""

import os
import json
import secrets
import hashlib
from typing import List, Tuple, Optional
import pyotp


def generate_totp_secret() -> str:
    """Generates a cryptographically secure random base32 secret for TOTP."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Evidentia-AI") -> str:
    """
    Returns the standard otpauth:// URI for QR code generation in authenticator
    apps (Google Authenticator, Microsoft Authenticator, Aegis, 1Password).
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verifies a 6-digit TOTP code against the shared base32 secret.
    Allows a 1-step window (±30 seconds) to account for clock skew.
    """
    if not secret or not code:
        return False
    clean_code = str(code).strip().replace(" ", "").replace("-", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    totp = pyotp.TOTP(secret)
    return totp.verify(clean_code, valid_window=1)


def generate_backup_codes(count: int = 8) -> Tuple[List[str], str]:
    """
    Generates single-use recovery backup codes formatted as XXXX-XXXX.
    Returns:
      - plain_codes: list of strings to show the user once.
      - hashed_json: JSON string of SHA-256 hashes to store in the database.
    """
    plain_codes = []
    hashed_list = []

    for _ in range(count):
        raw_token = secrets.token_hex(4).upper()  # 8 hex chars
        formatted = f"{raw_token[:4]}-{raw_token[4:]}"
        plain_codes.append(formatted)
        h = hashlib.sha256(formatted.encode("utf-8")).hexdigest()
        hashed_list.append(h)

    return plain_codes, json.dumps(hashed_list)


def verify_and_consume_backup_code(raw_code: str, backup_codes_json: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Checks if raw_code matches any stored hashed backup code.
    If matched, consumes (removes) that code and returns (True, updated_json).
    Otherwise returns (False, backup_codes_json).
    """
    if not backup_codes_json or not raw_code:
        return False, backup_codes_json

    clean_code = str(raw_code).strip().upper()
    if "-" not in clean_code and len(clean_code) == 8:
        clean_code = f"{clean_code[:4]}-{clean_code[4:]}"

    target_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

    try:
        hashes = json.loads(backup_codes_json)
        if not isinstance(hashes, list):
            return False, backup_codes_json

        if target_hash in hashes:
            hashes.remove(target_hash)
            return True, json.dumps(hashes)
    except Exception:
        pass

    return False, backup_codes_json

