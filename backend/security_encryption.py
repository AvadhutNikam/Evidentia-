"""
backend/security_encryption.py
==============================
Cryptographic field-level encryption at rest for sensitive investigative records:
- Criminal Prior Records & Modus Operandi (Section 54 IEA / Section 52 BSA safeguards)
- Suspect Plausibility Profiles & Personal Identifiable Information (PII)

Uses authenticated AES-GCM (256-bit) encryption with cryptographically random nonces.
Transparently handles legacy unencrypted plaintext while encrypting all newly saved data.
"""

import os
import base64
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Magic header prefix for encrypted fields
CIPHERTEXT_PREFIX = "ENC_v1:"

_KEY_FILE = Path(__file__).resolve().parent / ".evidentia_encryption.key"
_CACHED_KEY: Optional[bytes] = None


def get_encryption_key() -> bytes:
    """
    Retrieves or generates a 32-byte (256-bit) master AES key for data at rest.
    Prioritizes EVIDENTIA_DATA_ENCRYPTION_KEY environment variable.
    Falls back to a securely stored local keyfile with restricted permissions.
    """
    global _CACHED_KEY
    if _CACHED_KEY is not None:
        return _CACHED_KEY

    env_key = os.getenv("EVIDENTIA_DATA_ENCRYPTION_KEY")
    if env_key:
        try:
            # Can be base64-encoded or raw 32-char string
            decoded = base64.urlsafe_b64decode(env_key.encode("utf-8"))
            if len(decoded) == 32:
                _CACHED_KEY = decoded
                return _CACHED_KEY
        except Exception:
            pass
        if len(env_key.encode("utf-8")) >= 32:
            _CACHED_KEY = env_key.encode("utf-8")[:32]
            return _CACHED_KEY

    if _KEY_FILE.exists():
        try:
            with open(_KEY_FILE, "rb") as f:
                key_bytes = f.read().strip()
                if len(key_bytes) == 32:
                    _CACHED_KEY = key_bytes
                    return _CACHED_KEY
                decoded = base64.urlsafe_b64decode(key_bytes)
                if len(decoded) == 32:
                    _CACHED_KEY = decoded
                    return _CACHED_KEY
        except Exception as e:
            print(f"[!] Warning: failed reading encryption keyfile: {e}")

    # Generate a new 256-bit key and persist safely
    new_key = AESGCM.generate_key(bit_length=256)
    try:
        with open(_KEY_FILE, "wb") as f:
            f.write(base64.urlsafe_b64encode(new_key))
        try:
            os.chmod(_KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception as e:
        print(f"[!] Warning: failed writing encryption keyfile: {e}")

    _CACHED_KEY = new_key
    return _CACHED_KEY


def encrypt_field(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypts a plaintext string using AES-GCM with a fresh 12-byte nonce.
    Returns URL-safe base64 string prefixed with 'ENC_v1:'.
    Returns None/empty string unchanged.
    """
    if plaintext is None:
        return None
    if not isinstance(plaintext, str):
        plaintext = str(plaintext)
    if plaintext == "":
        return ""
    if plaintext.startswith(CIPHERTEXT_PREFIX):
        return plaintext  # Already encrypted

    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce recommended for AES-GCM
    data = plaintext.encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, data, None)

    # Pack nonce + ciphertext together
    payload = nonce + ciphertext
    b64_payload = base64.urlsafe_b64encode(payload).decode("utf-8")
    return f"{CIPHERTEXT_PREFIX}{b64_payload}"


def decrypt_field(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypts an encrypted field string.
    If the string does not have the 'ENC_v1:' prefix, it is treated as
    legacy plaintext and returned as-is (graceful backward compatibility).
    """
    if ciphertext is None:
        return None
    if not isinstance(ciphertext, str):
        return str(ciphertext)
    if not ciphertext.startswith(CIPHERTEXT_PREFIX):
        return ciphertext  # Graceful fallback for legacy unencrypted database rows

    raw_b64 = ciphertext[len(CIPHERTEXT_PREFIX):]
    try:
        payload = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        if len(payload) < 28:  # 12-byte nonce + at least 16-byte GCM tag
            return ciphertext
        nonce = payload[:12]
        ct = payload[12:]

        key = get_encryption_key()
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ct, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        # If decryption fails (e.g. key changed), return safe error notice
        return f"[DECRYPTION_ERROR: {str(e)}]"

