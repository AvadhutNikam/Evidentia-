"""
backend/auth.py
===============
Authentication & Role-Based Access Control (RBAC) Module for Evidentia-AI.

Roles:
  - 'admin': Full system access, manages users and all cases.
  - 'lead_investigator': Full access (create, analyze, delete, finalize) for assigned cases.
  - 'analyst': Can upload exhibits, run ACH analysis, and add hypotheses; cannot delete or close cases.
  - 'reviewer': Read-only access to assigned cases, can inspect evidence and export briefings.

Security:
  - Passwords hashed using bcrypt.
  - Short-lived JWT Access Tokens (60 min) + Refresh Tokens (7 days).
  - Failed login attempt rate-limiting with 15-minute temporary lockout.
  - Case membership isolation: Non-admin users can only view and interact with assigned cases.
"""

import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from dotenv import load_dotenv
from pathlib import Path

# Explicitly ensure environment is loaded
_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE)
else:
    load_dotenv()

from database import get_db
from models import User, CaseMember, Case, UserSession
import uuid
import hashlib

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

# Insecure default strings that must never be permitted in production or evaluation
_INSECURE_DEFAULT_SECRETS = {
    "evidentia_super_secret_forensic_jwt_key_2026_prod",
    "secret",
    "changeme",
    "jwt_secret_key",
    "evidentia_secret",
    "your_jwt_secret_key_here"
}

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

def validate_jwt_secret() -> str:
    """
    Validates that JWT_SECRET_KEY is defined in host environment settings
    and meets cryptographic security standards.
    Stops the app at startup with a clear error if missing or insecure.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or not secret.strip():
        raise RuntimeError(
            "\n" + "=" * 80 + "\n"
            "[FATAL SECURITY ERROR] 'JWT_SECRET_KEY' environment variable is NOT set!\n\n"
            "Evidentia-AI requires a cryptographically secure JWT secret key to start.\n"
            "Hardcoded default secrets have been completely removed.\n\n"
            "To fix this, generate a long random secret:\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(64))\"\n\n"
            "And add it to your environment (.env):\n"
            "  JWT_SECRET_KEY=<generated_secret>\n"
            + "=" * 80 + "\n"
        )
    if secret.strip() in _INSECURE_DEFAULT_SECRETS or len(secret.strip()) < 32:
        raise RuntimeError(
            "\n" + "=" * 80 + "\n"
            "[FATAL SECURITY ERROR] 'JWT_SECRET_KEY' is set to an insecure default or is too short (< 32 chars)!\n"
            "A strong, unique cryptographic secret is required. Please set a secure JWT_SECRET_KEY.\n"
            + "=" * 80 + "\n"
        )
    return secret.strip()

# Stop the app at startup with a clear error if JWT_SECRET_KEY is missing or insecure
JWT_SECRET_KEY = validate_jwt_secret()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Security Upgrade: High-security shorter sessions (15 minutes)
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Role hierarchy & permissions
ROLE_PERMISSIONS = {
    "admin": {
        "can_manage_users": True,
        "can_view_all_cases": True,
        "can_create_case": True,
        "can_delete_case": True,
        "can_add_evidence": True,
        "can_delete_evidence": True,
        "can_analyze": True,
        "can_finalize_case": True,
        "can_override_scoring": True,
        "can_export": True
    },
    "lead_investigator": {
        "can_manage_users": False,
        "can_view_all_cases": False,
        "can_create_case": True,
        "can_delete_case": True,
        "can_add_evidence": True,
        "can_delete_evidence": True,
        "can_analyze": True,
        "can_finalize_case": True,
        "can_override_scoring": True,
        "can_export": True
    },
    "analyst": {
        "can_manage_users": False,
        "can_view_all_cases": False,
        "can_create_case": False,
        "can_delete_case": False,
        "can_add_evidence": True,
        "can_delete_evidence": False,
        "can_analyze": True,
        "can_finalize_case": False,
        "can_override_scoring": True,
        "can_export": True
    },
    "reviewer": {
        "can_manage_users": False,
        "can_view_all_cases": False,
        "can_create_case": False,
        "can_delete_case": False,
        "can_add_evidence": False,
        "can_delete_evidence": False,
        "can_analyze": False,
        "can_finalize_case": False,
        "can_override_scoring": False,
        "can_export": True
    }
}

security = HTTPBearer(auto_error=False)


# ==============================================================================
# PASSWORD HASHING
# ==============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ==============================================================================
# JWT TOKEN MANAGEMENT
# ==============================================================================

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> str:
    """Create a signed JWT access token with unique JTI session identifier."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    session_id = jti or str(uuid.uuid4())
    token_type = data.get("type", "access")
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": token_type,
        "jti": session_id
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a longer-lived refresh token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token signature.",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ==============================================================================
# DEPENDENCIES: USER AUTHENTICATION
# ==============================================================================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates Bearer token and returns authenticated User model.
    Falls back to first active admin in development if credentials are absent.
    """
    if credentials:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject identifier"
            )
        if str(user_id).isdigit():
            user = db.query(User).filter(User.id == int(user_id)).first()
        else:
            user = db.query(User).filter(User.email == str(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token no longer exists"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # Check session revocation if jti is present
        jti = payload.get("jti")
        if jti:
            token_hash = hashlib.sha256(jti.encode("utf-8")).hexdigest()
            sess = db.query(UserSession).filter(
                UserSession.session_token_hash == token_hash,
                UserSession.user_id == user.id
            ).first()
            if sess:
                if sess.is_revoked:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session has been revoked by user or administrator. Please sign in again.",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                # Touch last_active_at
                sess.last_active_at = datetime.now(timezone.utc)
                db.commit()

        return user

    # Strict authentication: credentials are required
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required. Please sign in with a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"}
    )


def require_role(allowed_roles: List[str]):
    """
    Dependency factory requiring user to have one of the allowed global roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action restricted. Required role in {allowed_roles}, your role is '{current_user.role}'."
            )
        return current_user
    return role_checker


# Convenient admin-only dependency
require_admin = require_role(["admin"])


# ==============================================================================
# CASE ACCESS & MEMBERSHIP VERIFICATION
# ==============================================================================

def check_case_access(
    case_id: int,
    user: User,
    db: Session,
    action: str = "read"
) -> bool:
    """
    Verifies if user has permission to perform action on specific case:
      - Admin: allowed for all cases
      - Others: must be in case_members table
      - Checks action permissions (read, analyze, add_evidence, delete, finalize)
    """
    if user.role == "admin":
        return True

    membership = db.query(CaseMember).filter(
        CaseMember.case_id == case_id,
        CaseMember.user_id == user.id
    ).first()

    if not membership:
        return False

    effective_role = membership.case_role or user.role
    if effective_role == "lead":
        effective_role = "lead_investigator"
    perms = ROLE_PERMISSIONS.get(effective_role, ROLE_PERMISSIONS["reviewer"])

    action_map = {
        "read": True,
        "view_case": True,
        "view_evidence": True,
        "analyze": perms.get("can_analyze", False),
        "edit_case": perms.get("can_analyze", False),
        "edit_evidence": perms.get("can_analyze", False),
        "review_case": perms.get("can_override_scoring", False) or effective_role in ["admin", "lead_investigator", "reviewer"],
        "add_evidence": perms.get("can_add_evidence", False),
        "delete_evidence": perms.get("can_delete_evidence", False),
        "delete_case": perms.get("can_delete_case", False),
        "finalize_case": perms.get("can_finalize_case", False),
        "override_scoring": perms.get("can_override_scoring", False),
        "export": perms.get("can_export", True)
    }

    return action_map.get(action, False)


def get_user_accessible_case_ids(user: User, db: Session) -> Optional[List[int]]:
    """
    Returns list of accessible case IDs for user.
    Returns None if user is admin (meaning all cases are accessible).
    """
    if user.role == "admin":
        return None  # Unrestricted

    memberships = db.query(CaseMember.case_id).filter(CaseMember.user_id == user.id).all()
    return [m[0] for m in memberships]
