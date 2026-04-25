"""Pydantic models for rules, violations, and compliance reports."""

from __future__ import annotations
from pydantic import BaseModel


class DatasetInfo(BaseModel):
    name: str
    source: str = ""
    license: str = ""
    description: str = ""


class UsageRules(BaseModel):
    dataset: DatasetInfo
    allowed_uses: list[str]
    barred_uses: list[str]
    # Extended fields for richer legal-PDF extraction (all optional for backward compat)
    conditions: list[str] = []                # Conditional usage clauses ("Only if …", "Provided that …")
    attribution_requirements: list[str] = []  # Citation / attribution obligations
    redistribution_terms: list[str] = []      # Rules on sharing / redistribution
    geographic_restrictions: list[str] = []   # Jurisdiction-based constraints
    temporal_constraints: list[str] = []      # Time-limited permissions
    raw_extracted_text: str = ""              # Full original PDF text for audit reference


class Violation(BaseModel):
    file: str
    line_range: str
    code_snippet: str
    violated_rule: str
    severity: str  # high / medium / low
    explanation: str


class ComplianceReport(BaseModel):
    violations: list[Violation]
    summary: str
    is_compliant: bool

class ViolationListWrapper(BaseModel):
    items: list[Violation]
