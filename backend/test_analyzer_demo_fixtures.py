"""
Unit test to verify isolation of demo fixtures and enforce real pipeline extraction for uploaded files.
"""

import sys
import os
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from demo_fixtures import DEMO_EXHIBIT_DOSSIERS, get_demo_fixture
from analyzer import (
    extract_raw_text_from_file,
    analyze_with_fallback,
    run_comprehensive_analysis
)

def test_demo_fixture_lookup():
    print("[1] Testing demo fixture lookup...")
    assert "sample_atm_cctv.mp4" in DEMO_EXHIBIT_DOSSIERS
    assert "sample_cdr_dump.pdf" in DEMO_EXHIBIT_DOSSIERS
    assert "qualis_forensics.pdf" in DEMO_EXHIBIT_DOSSIERS
    assert "approver_confession.pdf" in DEMO_EXHIBIT_DOSSIERS

    fixture = get_demo_fixture("sample_atm_cctv.mp4")
    assert fixture is not None
    assert "Yerwada SBI ATM" in fixture["transcript"]

    unknown = get_demo_fixture("random_unrelated_file.pdf")
    assert unknown is None
    print("    -> Demo fixture lookup: PASSED")


def test_extraction_isolation():
    print("[2] Testing extract_raw_text_from_file isolation...")
    # When allow_fixtures=False (default for all real uploads), it must NOT return canned fixture text
    # for a file path that does not exist on disk
    text_blocked = extract_raw_text_from_file("nonexistent_dir/sample_atm_cctv.mp4", "Video", allow_fixtures=False)
    assert text_blocked == "", f"Expected empty text for missing file when allow_fixtures=False, got: {text_blocked}"

    # When allow_fixtures=True (strictly for demo cases), fixture text is permitted
    text_allowed = extract_raw_text_from_file("sample_atm_cctv.mp4", "Video", allow_fixtures=True)
    assert "Yerwada SBI ATM" in text_allowed
    print("    -> Raw text extraction isolation: PASSED")


def test_fallback_isolation():
    print("[3] Testing analyze_with_fallback isolation...")
    # Real pipeline fallback (allow_fixtures=False)
    sample_text = "Suspect was driving vehicle MH-12-AR-2541 and had IMEI 35489002148102 near Yerwada."
    res_live = analyze_with_fallback("sample_atm_cctv.mp4", "Video", sample_text, allow_fixtures=False)
    assert res_live["extraction_mode"] == "live"
    assert res_live["is_demo_fixture"] is False
    assert not res_live["summary"].startswith("[Demo data]")
    # Verify regex extracted vehicle and phone entities
    entity_types = [e["type"] for e in res_live["entities"]]
    assert "VEHICLE" in entity_types
    assert "PHONE" in entity_types

    # Demo fixture fallback (allow_fixtures=True)
    res_fixture = analyze_with_fallback("sample_atm_cctv.mp4", "Video", sample_text, allow_fixtures=True)
    assert res_fixture["extraction_mode"] == "demo_fixture"
    assert res_fixture["is_demo_fixture"] is True
    assert res_fixture["summary"].startswith("[Demo data]")
    print("    -> Fallback isolation: PASSED")


def test_comprehensive_analysis_pipeline():
    print("[4] Testing run_comprehensive_analysis pipeline behavior...")
    # Simulated newly uploaded user file matching demo name:
    # Must NEVER return demo fixture when allow_demo_fixtures=False!
    res_upload = run_comprehensive_analysis(
        file_path="uploads/user_uploaded_atm_cctv.mp4",
        file_name="sample_atm_cctv.mp4",
        file_type="Video",
        existing_text="Custom real CCTV note: Person in blue shirt entered at 22:00.",
        is_demo_case=False,
        allow_demo_fixtures=False
    )
    assert res_upload["extraction_mode"] == "live", f"Expected live, got: {res_upload['extraction_mode']}"
    assert res_upload["is_demo_fixture"] is False
    assert "Custom real CCTV note" in res_upload["text"]
    assert not res_upload["summary"].startswith("[Demo data]")

    # Simulated demo docket exhibit with is_demo_case=True and allow_demo_fixtures=True:
    res_demo = run_comprehensive_analysis(
        file_path="uploads/sample_atm_cctv.mp4",
        file_name="sample_atm_cctv.mp4",
        file_type="Video",
        is_demo_case=True,
        allow_demo_fixtures=True
    )
    assert res_demo["extraction_mode"] == "demo_fixture"
    assert res_demo["is_demo_fixture"] is True
    assert res_demo["summary"].startswith("[Demo data]")
    print("    -> Comprehensive analysis pipeline: PASSED")


if __name__ == "__main__":
    print("\n=== RUNNING DEMO FIXTURE ISOLATION TESTS ===")
    test_demo_fixture_lookup()
    test_extraction_isolation()
    test_fallback_isolation()
    test_comprehensive_analysis_pipeline()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

