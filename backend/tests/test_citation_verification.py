"""
Tests for Source-Span Citation & Quote Verification Engine.
Validates:
1. Text chunking with sentence boundaries and character offsets.
2. Cryptographic and lexical verification of exact quotes against source text.
3. Normalized whitespace and punctuation matching.
4. Fuzzy token matching for near-verbatim quotes.
5. Strict rejection of hallucinated/fabricated quotes.
6. Persistent database anchoring of verified fact citations.
"""

import pytest
from citation_engine import chunk_text, verify_and_anchor_quote, index_exhibit_chunks, anchor_fact_citation
from models import Case, Evidence, SourceCitation


RAW_FORENSIC_REPORT = """
OFFICIAL FORENSIC LABORATORY EXAMINATION REPORT
Case Reference: CR-2026-9081
Examining Specialist: Dr. Maya Lin, Senior Criminalist

1. PHYSICAL EVIDENCE RECEIVED
Exhibit 4: Partial blood smear collected from north stairwell railing.
Exhibit 5: Latent print lifted from interior window latch.

2. FORENSIC ANALYSIS RESULTS
The genotype matches suspect Marcus Vance (DOB: 14-Aug-1988) with a random match probability 
of less than 1 in 10 billion in the general population.
Co-suspect Julian Hayes is definitively excluded as a contributor to this stain.
Latent print Exhibit 5 displays 11 distinct ridge characteristics consistent with standard 
reference whorl patterns.
"""


def test_chunk_text_boundaries_and_pages():
    """Verifies that exhibit text is split into sequential chunks with valid offsets."""
    chunks = chunk_text(RAW_FORENSIC_REPORT, chunk_size=200)

    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
        assert c["page_number"] >= 1
        assert c["char_start"] < c["char_end"]
        sliced_text = RAW_FORENSIC_REPORT.strip()[c["char_start"]:c["char_end"]]
        assert len(sliced_text) > 0


def test_verified_quote_exact_match():
    """Validates that verbatim quotes extracted from exhibit text verify with 1.0 confidence."""
    target_quote = "The genotype matches suspect Marcus Vance (DOB: 14-Aug-1988)"
    res = verify_and_anchor_quote(
        full_text=RAW_FORENSIC_REPORT,
        raw_quote=target_quote
    )

    assert res["verified_match"] is True
    assert res["match_confidence"] >= 0.95
    assert res["verification_method"] in ["exact_substring", "normalized_substring"]
    assert res["char_start"] is not None
    assert res["char_end"] is not None
    assert RAW_FORENSIC_REPORT[res["char_start"]:res["char_end"]] == target_quote


def test_verified_quote_normalized_whitespace():
    """Validates matching despite line breaks or multiple spaces in raw quotes."""
    quote_with_newline = "random match probability\nof less than 1 in 10 billion"
    res = verify_and_anchor_quote(
        full_text=RAW_FORENSIC_REPORT,
        raw_quote=quote_with_newline
    )

    assert res["verified_match"] is True
    assert res["match_confidence"] >= 0.90
    assert res["verification_method"] in ["exact_substring", "normalized_substring", "fuzzy_token"]


def test_verified_quote_fuzzy_match():
    """Validates token-level similarity when OCR or LLM introduces minor character differences."""
    fuzzy_quote = "The genotyp matches suspect Marcus Vance (DOB: 14-Aug-1988)"
    res = verify_and_anchor_quote(
        full_text=RAW_FORENSIC_REPORT,
        raw_quote=fuzzy_quote
    )

    assert res["verified_match"] is True
    assert res["match_confidence"] >= 0.75
    assert res["verification_method"] == "fuzzy_token"


def test_rejection_of_hallucinated_quote():
    """Validates that hallucinated or fabricated statements are strictly flagged as unverified."""
    fake_quote = "Marcus Vance admitted during interrogation that he entered the north stairwell at midnight."
    res = verify_and_anchor_quote(
        full_text=RAW_FORENSIC_REPORT,
        raw_quote=fake_quote
    )

    assert res["verified_match"] is False
    assert res["verification_method"] == "unverified"
    assert res["match_confidence"] < 0.65


def test_persistent_citation_anchoring_in_db(db):
    """Verifies indexing exhibit chunks and anchoring persistent citations in the database."""
    case = Case(title="Citation Anchor Test", description="Testing persistent citations")
    db.add(case)
    db.commit()

    evidence = Evidence(
        case_id=case.id,
        file_name="forensic_report.txt",
        file_type="text",
        extracted_text=RAW_FORENSIC_REPORT
    )
    db.add(evidence)
    db.commit()

    # Index chunks
    chunks = index_exhibit_chunks(db, evidence_id=evidence.id, case_id=case.id, text=RAW_FORENSIC_REPORT)
    assert len(chunks) > 0

    # Anchor a verified citation for an entity
    valid_quote = "Co-suspect Julian Hayes is definitively excluded as a contributor to this stain."
    citation = anchor_fact_citation(
        db=db,
        case_id=case.id,
        evidence_id=evidence.id,
        fact_type="entity",
        fact_id=1,
        raw_quote=valid_quote,
        chunk_id=chunks[0].id
    )

    assert citation is not None
    assert citation.verified_match is True
    assert citation.match_confidence >= 0.90

    # Anchor an unverified/hallucinated citation
    fake_quote = "Julian Hayes was seen holding a red crowbar inside the basement."
    bad_citation = anchor_fact_citation(
        db=db,
        case_id=case.id,
        evidence_id=evidence.id,
        fact_type="entity",
        fact_id=2,
        raw_quote=fake_quote
    )
    assert bad_citation.verified_match is False
