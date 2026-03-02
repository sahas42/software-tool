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
