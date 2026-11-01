"""
backend/tests/test_requirements_completeness.py
===============================================
Validates that requirements.txt is complete, accurately pinned, and includes
all modules required by the codebase (pyotp, cryptography, Pillow, pypdf, pytesseract, openai-whisper)
to prevent clean installation startup failures.
"""

import os
from pathlib import Path


def test_requirements_file_contains_all_core_and_multimodal_dependencies():
    """
    Verifies that requirements.txt explicitly lists all packages imported by
    the core backend, encryption/TOTP security, and multimodal extraction pipeline.
    """
    req_path = Path(__file__).resolve().parent.parent / "requirements.txt"
    assert req_path.exists(), "backend/requirements.txt must exist"

    with open(req_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    packages = {}
    for line in lines:
        parts = line.split("==")
        pkg_name = parts[0].split("[")[0].strip().lower().replace("-", "_")
        version = parts[1].strip() if len(parts) > 1 else None
        packages[pkg_name] = version

    # Critical packages that must be present
    required_critical = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "psycopg2_binary",
        "pydantic",
        "bcrypt",
        "pyjwt",
        "pyotp",
        "cryptography",
        "pillow",
        "pypdf",
        "pytesseract",
        "openai_whisper",
        "reportlab",
        "requests",
        "httpx",
        "google_genai",
        "pytest",
        "openpyxl",
        "python_dotenv",
        "python_multipart",
        "alembic"
    ]

    for req in required_critical:
        assert req in packages, f"Missing critical dependency in requirements.txt: {req}"
        assert packages[req] is not None, f"Dependency {req} must be pinned with exact version (==)"


def test_core_dependencies_import_successfully_without_error():
    """
    Verifies that all core and security dependencies can be imported directly
    in the Python runtime environment without raising ModuleNotFoundError.
    """
    import pyotp
    import cryptography
    import PIL
    import pypdf
    import pytesseract

    assert pyotp.random_base32 is not None
    assert hasattr(cryptography, "__version__")
    assert hasattr(PIL, "__version__")
    assert hasattr(pypdf, "__version__")
    assert hasattr(pytesseract, "__version__")

