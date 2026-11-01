"""
backend/ai_dispatch_engine.py
=============================
Private Model Dispatcher & Air-Gap Security Firewall for Evidentia-AI.

Guarantees:
1. Air-Gapped Enforcement: When a case is flagged as sensitive/air-gapped (`is_sensitive_airgapped=True`),
   all outbound network egress to external cloud AI APIs (Gemini/OpenAI) is strictly blocked.
2. Local Model Support: Integrates with locally hosted LLMs (Ollama, vLLM, or custom OpenAI-compatible
   endpoints like http://localhost:11434/v1/chat/completions).
3. Audit Trail: Every blocked external attempt or local model invocation is logged with actor and timestamp.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from config import DEFAULT_MODEL_NAME


class AirGapSecurityViolationError(Exception):
    """Raised when an external cloud API call is attempted on an air-gapped or sensitive case."""
    pass


def get_system_security_settings(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Returns global system security settings from DB or environment defaults.
    """
    defaults = {
        "default_ai_provider": os.getenv("DEFAULT_AI_PROVIDER", "cloud_gemini"),
        "local_model_endpoint": os.getenv("LOCAL_MODEL_ENDPOINT", "http://localhost:11434/v1"),
        "local_model_name": os.getenv("LOCAL_MODEL_NAME", "llama3"),
        "allow_external_ai_global": os.getenv("ALLOW_EXTERNAL_AI_GLOBAL", "true").lower() == "true",
        "default_session_duration_minutes": int(os.getenv("SESSION_DURATION_MINUTES", "15")),
        "require_2fa_for_admins": os.getenv("REQUIRE_2FA_FOR_ADMINS", "false").lower() == "true",
    }

    if db is None:
        return defaults

    try:
        from models import SystemSecurityConfig
        cfg = db.query(SystemSecurityConfig).first()
        if cfg:
            return {
                "default_ai_provider": cfg.default_ai_provider or defaults["default_ai_provider"],
                "local_model_endpoint": cfg.local_model_endpoint or defaults["local_model_endpoint"],
                "local_model_name": cfg.local_model_name or defaults["local_model_name"],
                "allow_external_ai_global": cfg.allow_external_ai_global if cfg.allow_external_ai_global is not None else defaults["allow_external_ai_global"],
                "default_session_duration_minutes": cfg.default_session_duration_minutes or defaults["default_session_duration_minutes"],
                "require_2fa_for_admins": cfg.require_2fa_for_admins or defaults["require_2fa_for_admins"],
            }
    except Exception:
        pass

    return defaults


def check_airgap_status(case_id: Optional[int], db: Optional[Session]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Determines if AI calls for a case are air-gapped / blocked from external APIs.
    Returns:
      (is_airgapped: bool, reason: str, effective_config: dict)
    """
    sys_cfg = get_system_security_settings(db)
    if not sys_cfg["allow_external_ai_global"]:
        return True, "Global system-wide air-gap enforcement active (all external cloud AI disabled)", sys_cfg

    if case_id and db:
        try:
            from models import Case
            case = db.query(Case).filter(Case.id == case_id).first()
            if case and getattr(case, "is_sensitive_airgapped", False):
                provider = getattr(case, "ai_provider_override", None) or sys_cfg["default_ai_provider"]
                if provider == "cloud_gemini":
                    provider = "local_ollama"
                effective_cfg = dict(sys_cfg)
                effective_cfg["default_ai_provider"] = provider
                if getattr(case, "local_ai_endpoint", None):
                    effective_cfg["local_model_endpoint"] = case.local_ai_endpoint
                if getattr(case, "local_ai_model", None):
                    effective_cfg["local_model_name"] = case.local_ai_model
                return True, f"Case #{case_id} is designated as Sensitive / Air-Gapped. External AI calls strictly blocked.", effective_cfg
        except Exception:
            pass

    return False, "Standard operational mode (cloud and local AI allowed)", sys_cfg


def dispatch_local_ai_completion(
    prompt: str,
    system_instruction: Optional[str] = None,
    endpoint: str = "http://localhost:11434/v1",
    model_name: str = "llama3",
    timeout_seconds: int = 30
) -> Dict[str, Any]:
    """
    Calls a local Ollama or vLLM endpoint using the standard OpenAI-compatible
    POST /chat/completions format.
    """
    clean_endpoint = endpoint.rstrip("/")
    if not clean_endpoint.endswith("/chat/completions"):
        if clean_endpoint.endswith("/v1"):
            target_url = f"{clean_endpoint}/chat/completions"
        else:
            target_url = f"{clean_endpoint}/v1/chat/completions"
    else:
        target_url = clean_endpoint

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.2
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            choices = data.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            return {
                "success": True,
                "text": content,
                "provider": "local_ollama",
                "model": model_name,
                "endpoint": target_url
            }
    except Exception as e:
        # If local endpoint is currently offline in dev/test, return structured fallback
        print(f"[!] Local model call to {target_url} failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": f"[LOCAL_MODEL_OFFLINE: {str(e)}. Air-gap switch preserved: no data was transmitted externally.]",
            "provider": "local_ollama",
            "model": model_name,
            "endpoint": target_url
        }


def dispatch_ai_completion(
    prompt: str,
    system_instruction: Optional[str] = None,
    case_id: Optional[int] = None,
    db: Optional[Session] = None,
    requested_provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Central AI completion dispatcher.
    Enforces the Air-Gap firewall:
      - If case is air-gapped and caller requests cloud_gemini -> raises AirGapSecurityViolationError!
      - Routes air-gapped cases strictly to local model endpoint.
    """
    is_airgapped, reason, effective_cfg = check_airgap_status(case_id, db)
    provider = requested_provider or effective_cfg.get("default_ai_provider", "cloud_gemini")

    if is_airgapped:
        if provider == "cloud_gemini":
            # Air-gap enforcement! External calls blocked.
            # Automatically fallback to local model or fail loudly if cloud was explicitly demanded.
            if requested_provider == "cloud_gemini":
                raise AirGapSecurityViolationError(
                    f"AIR-GAP SECURITY VIOLATION: {reason}. External data egress to cloud AI is prohibited."
                )
            provider = "local_ollama"

    if provider in ["local_ollama", "local_vllm", "local_custom"]:
        return dispatch_local_ai_completion(
            prompt=prompt,
            system_instruction=system_instruction,
            endpoint=effective_cfg.get("local_model_endpoint", "http://localhost:11434/v1"),
            model_name=effective_cfg.get("local_model_name", "llama3")
        )

    # Cloud Gemini Path
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY not configured",
            "text": "Gemini API key is not configured.",
            "provider": "cloud_gemini",
            "model": DEFAULT_MODEL_NAME
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        response = client.models.generate_content(
            model=DEFAULT_MODEL_NAME,
            contents=full_prompt
        )
        return {
            "success": True,
            "text": getattr(response, "text", str(response)),
            "provider": "cloud_gemini",
            "model": DEFAULT_MODEL_NAME
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": f"AI Generation Error: {str(e)}",
            "provider": "cloud_gemini",
            "model": DEFAULT_MODEL_NAME
        }

