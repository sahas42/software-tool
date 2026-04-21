"""Unit tests for the LLM-powered PDF rule extraction module."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.compliance_checker.models import UsageRules, DatasetInfo
from src.compliance_checker.pdf_rule_extractor import (
    extract_rules_from_pdf,
    _extract_text_from_pdf,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_LLM_RESPONSE = {
    "dataset": {
        "name": "LegalBench",
        "source": "https://example.com/legalbench",
        "license": "CC BY-NC 4.0",
        "description": "A benchmark dataset for legal NLP tasks.",
    },
    "allowed_uses": [
        "Academic research on legal NLP",
        "Non-commercial benchmarking",
    ],
    "barred_uses": [
        "Commercial use without written consent",
        "Training surveillance tools",
    ],
    "conditions": [
        "Only permitted if user agrees to the data use agreement",
    ],
    "attribution_requirements": [
        "Must cite the original paper in all publications",
    ],
    "redistribution_terms": [
        "Redistribution only with prior approval from the authors",
    ],
    "geographic_restrictions": [],
    "temporal_constraints": [
        "License expires on 2027-12-31",
    ],
}


def _make_fake_pdf_bytes() -> bytes:
    """Create a minimal valid PDF that pypdf can read."""
    from pypdf import PdfWriter
    import io

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)

    # pypdf PdfWriter doesn't easily let us inject text into a blank page,
    # so we'll patch _extract_text_from_pdf instead for the LLM flow tests.
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestExtractTextFromPdf:
    """Tests for the low-level pypdf text extraction helper."""

    def test_empty_pdf(self):
        pdf_bytes = _make_fake_pdf_bytes()
        text = _extract_text_from_pdf(pdf_bytes)
        # Blank page → no extractable text
        assert isinstance(text, str)


class TestExtractRulesFromPdf:
    """Tests for the full LLM-powered extraction pipeline."""

    @patch("src.compliance_checker.pdf_rule_extractor._call_gemini")
    @patch("src.compliance_checker.pdf_rule_extractor._extract_text_from_pdf")
    def test_successful_extraction(self, mock_extract_text, mock_call_gemini):
        """Happy path: LLM returns a valid JSON blob and we get a rich UsageRules."""
        mock_extract_text.return_value = "This is a legal license document..."
        mock_call_gemini.return_value = SAMPLE_LLM_RESPONSE

        rules = extract_rules_from_pdf(b"fake-pdf-bytes", api_key="test-key")

        assert isinstance(rules, UsageRules)
        assert rules.dataset.name == "LegalBench"
        assert rules.dataset.license == "CC BY-NC 4.0"
        assert len(rules.allowed_uses) == 2
        assert len(rules.barred_uses) == 2
        assert len(rules.conditions) == 1
        assert len(rules.attribution_requirements) == 1
        assert len(rules.redistribution_terms) == 1
        assert len(rules.geographic_restrictions) == 0
        assert len(rules.temporal_constraints) == 1
        # raw text should be attached
        assert "legal license document" in rules.raw_extracted_text

    @patch("src.compliance_checker.pdf_rule_extractor._call_gemini")
    @patch("src.compliance_checker.pdf_rule_extractor._extract_text_from_pdf")
    def test_missing_dataset_in_response(self, mock_extract_text, mock_call_gemini):
        """If the LLM omits the dataset key, a fallback dataset is created."""
        mock_extract_text.return_value = "Some document text"
        incomplete = {
            "allowed_uses": ["Research"],
            "barred_uses": ["Commercial use"],
        }
        mock_call_gemini.return_value = incomplete

        rules = extract_rules_from_pdf(b"fake-pdf-bytes", api_key="test-key")

        assert "Unknown" in rules.dataset.name or "extracted" in rules.dataset.name.lower()
        assert rules.allowed_uses == ["Research"]

    @patch("src.compliance_checker.pdf_rule_extractor._extract_text_from_pdf")
    def test_empty_pdf_raises(self, mock_extract_text):
        """An empty PDF should raise a ValueError."""
        mock_extract_text.return_value = ""

        with pytest.raises(ValueError, match="no extractable text"):
            extract_rules_from_pdf(b"fake-pdf-bytes", api_key="test-key")

    def test_no_api_key_raises(self):
        """Missing API key should raise a ValueError."""
        with pytest.raises(ValueError, match="API key"):
            extract_rules_from_pdf(b"fake-pdf-bytes", api_key="")

    @patch("src.compliance_checker.pdf_rule_extractor._call_gemini")
    @patch("src.compliance_checker.pdf_rule_extractor._extract_text_from_pdf")
    def test_gemini_failure_propagates(self, mock_extract_text, mock_call_gemini):
        """If Gemini raises, the error should propagate."""
        mock_extract_text.return_value = "Document text"
        mock_call_gemini.side_effect = RuntimeError("Gemini unavailable")

        with pytest.raises(RuntimeError, match="Gemini unavailable"):
            extract_rules_from_pdf(b"fake-pdf-bytes", api_key="test-key")


class TestBackwardCompatibility:
    """Ensure existing YAML-based UsageRules still work with new fields defaulting."""

    def test_yaml_rules_still_parse(self):
        """Old-format dicts (no new fields) should parse without errors."""
        old_format = {
            "dataset": {"name": "TestDS", "source": "", "license": "MIT", "description": "A test"},
            "allowed_uses": ["Research"],
            "barred_uses": ["Malicious use"],
        }
        rules = UsageRules(**old_format)
        assert rules.conditions == []
        assert rules.attribution_requirements == []
        assert rules.redistribution_terms == []
        assert rules.geographic_restrictions == []
        assert rules.temporal_constraints == []
        assert rules.raw_extracted_text == ""
