"""
backend/routers/auth.py
=======================
Authentication, Two-Factor Authentication (2FA), Session Management & Access Control Router.
"""

import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSession
from schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserOut, TwoFactorSetupResponse, TwoFactorVerifyRequest,
    TwoFactorChallengeRequest, TwoFactorDisableRequest, UserSessionOut
)
from auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
    require_role, get_user_accessible_case_ids, ACCESS_TOKEN_EXPIRE_MINUTES
)
from totp_security import (
    generate_totp_secret, get_totp_uri, verify_totp_code,
    generate_backup_codes, verify_and_consume_backup_code
)
from security_encryption import encrypt_field, decrypt_field
from audit_engine import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _extract_device_info(request: Optional[Request]) -> Tuple[str, str, str]:
    """Helper to extract IP, user agent, and human-readable device string."""
    if not request:
        return "127.0.0.1", "Evidentia Web Client", "Evidentia Client"
    ip = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown Browser")
    device = "Desktop / Web"
    if "Mobile" in ua:
        device = "Mobile Device"
    elif "Postman" in ua or "python" in ua.lower():
        device = "API Client"
    elif "Windows" in ua:
        device = "Windows Workstation"
    elif "Macintosh" in ua:
        device = "macOS Workstation"
    elif "Linux" in ua:
        device = "Linux Workstation"
    return ip, ua, device


@router.post("/register", response_model=TokenResponse)
def register_user(req: UserRegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    is_first = db.query(User).count() == 0
    assigned_role = "admin" if is_first else (req.role or "analyst")
    
    new_user = User(
        email=req.email.lower().strip(),
        full_name=req.full_name,
        role=assigned_role,
        badge_number=req.badge_number,
        department=req.department,
        hashed_password=hash_password(req.password),
        is_active=True,
        is_2fa_enabled=False,
        session_duration_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create initial UserSession
    now = datetime.now(timezone.utc)
    ip, ua, device = _extract_device_info(request)
    session_jti = str(uuid.uuid4())
    session_hash = hashlib.sha256(session_jti.encode("utf-8")).hexdigest()
    expire_delta = timedelta(minutes=new_user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)

    sess = UserSession(
        user_id=new_user.id,
        session_token_hash=session_hash,
        device_info=device,
        ip_address=ip,
        user_agent=ua,
        expires_at=now + expire_delta,
        is_revoked=False
    )
    db.add(sess)
    db.commit()

    access_token = create_access_token(
        {"sub": str(new_user.id), "email": new_user.email, "role": new_user.role},
        expires_delta=expire_delta,
        jti=session_jti
    )
    refresh_token = create_refresh_token({"sub": str(new_user.id)})
    
    user_out = UserOut.model_validate(new_user)
    user_out.accessible_cases = None if new_user.role == "admin" else []
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=new_user.session_duration_minutes,
        user=user_out,
        requires_2fa=False
    )


@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    now = datetime.now(timezone.utc)
    if user.locked_until:
        locked_time = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
        if locked_time > now:
            mins_left = int((locked_time - now).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Account temporarily locked due to multiple failed attempts. Try again in {mins_left} minutes."
            )
            
    if not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=f"Maximum failed attempts reached ({MAX_FAILED_ATTEMPTS}). Account locked for {LOCKOUT_DURATION_MINUTES} minutes."
            )
        db.commit()
        remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
        raise HTTPException(
            status_code=401,
            detail=f"Invalid email or password. {remaining} attempt(s) remaining before lockout."
        )
        
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # Two-Factor Authentication Check
    if getattr(user, 'is_2fa_enabled', False):
        temp_token = create_access_token(
            {"sub": str(user.id), "type": "2fa_pending", "email": user.email},
            expires_delta=timedelta(minutes=5)
        )
        return TokenResponse(
            access_token="",
            refresh_token="",
            token_type="bearer",
            expires_in_minutes=5,
            user=None,
            requires_2fa=True,
            temp_token=temp_token
        )
    
    # Establish authenticated short session
    ip, ua, device = _extract_device_info(request)
    session_jti = str(uuid.uuid4())
    session_hash = hashlib.sha256(session_jti.encode("utf-8")).hexdigest()
    expire_delta = timedelta(minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)

    sess = UserSession(
        user_id=user.id,
        session_token_hash=session_hash,
        device_info=device,
        ip_address=ip,
        user_agent=ua,
        expires_at=now + expire_delta,
        is_revoked=False
    )
    db.add(sess)
    db.commit()

    access_token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=expire_delta,
        jti=session_jti
    )
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    accessible_cases = get_user_accessible_case_ids(user, db)
    user_out = UserOut.model_validate(user)
    user_out.accessible_cases = accessible_cases
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES,
        user=user_out,
        requires_2fa=False
    )


@router.post("/2fa/challenge", response_model=TokenResponse)
def verify_2fa_challenge(req: TwoFactorChallengeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Validates a 2FA challenge code (TOTP or single-use recovery code)
    and delivers the final authenticated short session token.
    """
    payload = decode_token(req.temp_token)
    if payload.get("type") != "2fa_pending":
        raise HTTPException(status_code=400, detail="Invalid temporary token for 2FA challenge")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account inactive or not found")

    # Decrypt TOTP secret
    decrypted_secret = decrypt_field(user.totp_secret)
    is_valid = verify_totp_code(decrypted_secret, req.code)

    if not is_valid:
        # Check if it matches a recovery backup code
        is_backup, updated_hashes = verify_and_consume_backup_code(req.code, user.backup_codes)
        if is_backup:
            user.backup_codes = updated_hashes
            db.commit()
            is_valid = True
            try:
                log_audit_event(
                    db=db,
                    action_type="2FA_BACKUP_CODE_USED",
                    target_type="user",
                    target_id=str(user.id),
                    description=f"User {user.full_name} logged in using a single-use 2FA backup recovery code.",
                    user_id=user.id,
                    user_name=user.full_name,
                    user_role=user.role
                )
            except Exception:
                pass

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid 2FA code or backup recovery code. Please try again.")

    # 2FA succeeded: establish session
    now = datetime.now(timezone.utc)
    ip, ua, device = _extract_device_info(request)
    session_jti = str(uuid.uuid4())
    session_hash = hashlib.sha256(session_jti.encode("utf-8")).hexdigest()
    expire_delta = timedelta(minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)

    sess = UserSession(
        user_id=user.id,
        session_token_hash=session_hash,
        device_info=device,
        ip_address=ip,
        user_agent=ua,
        expires_at=now + expire_delta,
        is_revoked=False
    )
    db.add(sess)
    db.commit()

    access_token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=expire_delta,
        jti=session_jti
    )
    refresh_token = create_refresh_token({"sub": str(user.id)})

    accessible_cases = get_user_accessible_case_ids(user, db)
    user_out = UserOut.model_validate(user)
    user_out.accessible_cases = accessible_cases

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES,
        user=user_out,
        requires_2fa=False
    )


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates 2FA setup for the logged-in investigator:
    Generates a new base32 TOTP secret, standard otpauth:// URI, and 8 recovery backup codes.
    The backup code hashes are staged so that upon verification, the same recovery codes are active.
    """
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    plain_codes, hashed_codes = generate_backup_codes(count=8)
    current_user.backup_codes = hashed_codes
    db.commit()

    return TwoFactorSetupResponse(
        secret=secret,
        otpauth_uri=uri,
        backup_codes=plain_codes
    )


@router.post("/2fa/verify-and-enable")
def verify_and_enable_2fa(
    req: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validates the 6-digit TOTP code against the secret to verify the user
    successfully configured their authenticator app, then activates 2FA.
    """
    if not req.secret:
        raise HTTPException(status_code=400, detail="TOTP secret is required for verification")

    if not verify_totp_code(req.secret, req.code):
        raise HTTPException(status_code=400, detail="Invalid verification code. Please check your authenticator clock.")

    # Encrypt secret before storing in DB at rest
    current_user.totp_secret = encrypt_field(req.secret)
    # Ensure backup recovery codes exist; keep staged ones or generate if none
    if not current_user.backup_codes:
        _, hashed_codes = generate_backup_codes(count=8)
        current_user.backup_codes = hashed_codes
    current_user.is_2fa_enabled = True
    db.commit()

    try:
        log_audit_event(
            db=db,
            action_type="2FA_ENABLED",
            target_type="user",
            target_id=str(current_user.id),
            description=f"Two-Factor Authentication activated for {current_user.full_name} ({current_user.role}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": "Two-Factor Authentication enabled successfully. Please store your backup codes safely."
    }


@router.post("/2fa/disable")
def disable_2fa(
    req: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disables 2FA on the user's account after verifying current password.
    """
    if not verify_password(req.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password confirmation.")

    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = None
    db.commit()

    try:
        log_audit_event(
            db=db,
            action_type="2FA_DISABLED",
            target_type="user",
            target_id=str(current_user.id),
            description=f"Two-Factor Authentication deactivated for {current_user.full_name} ({current_user.role}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role
        )
    except Exception:
        pass

    return {"status": "success", "message": "Two-Factor Authentication disabled."}


@router.get("/sessions", response_model=List[UserSessionOut])
def get_user_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns active sessions for the current investigator,
    marking the current active device and expiration times.
    """
    now = datetime.now(timezone.utc)
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_revoked == False,
        UserSession.expires_at > now
    ).order_by(UserSession.last_active_at.desc()).all()

    # Determine current session jti from token
    auth_header = request.headers.get("authorization", "")
    current_jti_hash = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                current_jti_hash = hashlib.sha256(jti.encode("utf-8")).hexdigest()
        except Exception:
            pass

    results = []
    for s in sessions:
        out = UserSessionOut.model_validate(s)
        out.is_current = bool(current_jti_hash and s.session_token_hash == current_jti_hash)
        results.append(out)

    return results


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes a specific session remotely."""
    sess = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    sess.is_revoked = True
    db.commit()
    return {"status": "success", "message": f"Session #{session_id} revoked."}


@router.delete("/sessions/other")
def revoke_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes all active sessions for this user except the current session."""
    auth_header = request.headers.get("authorization", "")
    current_jti_hash = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                current_jti_hash = hashlib.sha256(jti.encode("utf-8")).hexdigest()
        except Exception:
            pass

    q = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_revoked == False
    )
    if current_jti_hash:
        q = q.filter(UserSession.session_token_hash != current_jti_hash)

    revoked_count = q.update({"is_revoked": True}, synchronize_session=False)
    db.commit()

    return {"status": "success", "message": f"Revoked {revoked_count} other active session(s)."}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: dict, db: Session = Depends(get_db)):
    ref_token = request.get("refresh_token")
    if not ref_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
        
    payload = decode_token(ref_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type for refresh")
        
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account inactive or not found")

    now = datetime.now(timezone.utc)
    session_jti = str(uuid.uuid4())
    session_hash = hashlib.sha256(session_jti.encode("utf-8")).hexdigest()
    expire_delta = timedelta(minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)

    sess = UserSession(
        user_id=user.id,
        session_token_hash=session_hash,
        device_info="Refreshed Session",
        ip_address="127.0.0.1",
        expires_at=now + expire_delta,
        is_revoked=False
    )
    db.add(sess)
    db.commit()

    access_token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=expire_delta,
        jti=session_jti
    )
    new_refresh = create_refresh_token({"sub": str(user.id)})
    
    accessible_cases = get_user_accessible_case_ids(user, db)
    user_out = UserOut.model_validate(user)
    user_out.accessible_cases = accessible_cases
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in_minutes=user.session_duration_minutes or ACCESS_TOKEN_EXPIRE_MINUTES,
        user=user_out,
        requires_2fa=False
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible_cases = get_user_accessible_case_ids(current_user, db)
    user_out = UserOut.model_validate(current_user)
    user_out.accessible_cases = accessible_cases
    return user_out


@router.get("/users", response_model=List[UserOut])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active == True).all()
    results = []
    for u in users:
        uo = UserOut.model_validate(u)
        uo.accessible_cases = get_user_accessible_case_ids(u, db)
        results.append(uo)
    return results


@router.post("/logout")
def logout_user(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                token_hash = hashlib.sha256(jti.encode("utf-8")).hexdigest()
                sess = db.query(UserSession).filter(
                    UserSession.session_token_hash == token_hash,
                    UserSession.user_id == current_user.id
                ).first()
                if sess:
                    sess.is_revoked = True
                    db.commit()
        except Exception:
            pass
    return {"status": "success", "message": "Session terminated successfully"}
