"""Send codebase + rules to Gemini and get a structured compliance report."""

from __future__ import annotations
import json
import re
import time
import sys
from pathlib import Path
from google import genai
from .models import UsageRules, ComplianceReport

MAX_RETRIES = 3
INITIAL_DELAY = 10
MAX_RELEVANT_TXT = 5


SYSTEM_PROMPT = """\
You are a dataset-usage compliance auditor.

You will receive:
1. Information about a dataset (name, source, license, description).
2. A list of ALLOWED uses for this dataset.
3. A list of BARRED (prohibited) uses for this dataset.
4. The full source code of a project that uses this dataset.

Your job:
- Read every source file carefully.
- Identify any code that violates the barred-use rules or uses the dataset
  in a way that is NOT covered by the allowed-use list.
- For each violation, report the file name, approximate line range,
  a short code snippet, which rule was violated, severity (high/medium/low),
  and a clear explanation.
- If the codebase is fully compliant, return an empty violations list and
  set is_compliant to true.

Be precise. Do not hallucinate violations that don't exist in the code.
Only flag clear, concrete violations.
"""


def _extract_relevance_terms(rules: UsageRules) -> set[str]:
    raw_text = " ".join(
        [
            rules.dataset.name or "",
            rules.dataset.source or "",
            rules.dataset.license or "",
            rules.dataset.description or "",
            " ".join(rules.allowed_uses or []),
            " ".join(rules.barred_uses or []),
        ]
    )
    candidates = re.findall(r"\b[a-z0-9]{3,}\b", raw_text.lower())
    return set(candidates) or {"dataset", "data"}


def _score_text(query_terms: set[str], text: str) -> int:
    normalized = text.lower()
    return sum(1 for term in query_terms if term in normalized)


def _filter_relevant_txt_files(codebase: dict[str, str], rules: UsageRules) -> dict[str, str]:
    query_terms = _extract_relevance_terms(rules)
    txt_scores: list[tuple[int, str, str]] = []

    for filepath, content in codebase.items():
        if Path(filepath).suffix.lower() != ".txt":
            continue
        score = _score_text(query_terms, filepath + " " + content)
        txt_scores.append((score, filepath, content))

    txt_scores.sort(reverse=True, key=lambda item: item[0])
    keep = {}
    for score, filepath, content in txt_scores:
        if score > 0:
            keep[filepath] = content
    # Keep up to MAX_RELEVANT_TXT top .txt files if none scored positively (fallback)
    if not keep:
        for score, filepath, content in txt_scores[:MAX_RELEVANT_TXT]:
            keep[filepath] = content

    return keep


def _build_user_prompt(rules: UsageRules, codebase: dict[str, str] | str) -> str:
    """Compose the user message with rules + code."""
    parts: list[str] = []

    parts.append("## Dataset Information")
    parts.append(f"- Name: {rules.dataset.name}")
    parts.append(f"- Source: {rules.dataset.source}")
    parts.append(f"- License: {rules.dataset.license}")
    parts.append(f"- Description: {rules.dataset.description}")

    parts.append("\n## Allowed Uses")
    for use in rules.allowed_uses:
        parts.append(f"- {use}")

    parts.append("\n## Barred Uses")
    for use in rules.barred_uses:
        parts.append(f"- {use}")

    parts.append("\n## Source Code")
    if isinstance(codebase, dict):
        relevant_txt = _filter_relevant_txt_files(codebase, rules)
        for filepath, content in codebase.items():
            suffix = Path(filepath).suffix.lower()
            if suffix == ".txt" and filepath not in relevant_txt:
                continue
            parts.append(f"\n### File: {filepath}")
            parts.append(f"```\n{content}\n```")

        if relevant_txt:
            parts.append("\n## Note: Filtered .txt files")
            parts.append(
                f"Included {len(relevant_txt)} relevant .txt file(s) and excluded irrelevant .txt files."
            )
            parts.append("\n## Included .txt Files:")
            for path in sorted(relevant_txt.keys()):
                parts.append(f"- {path}")
        else:
            parts.append("\n## Note: No .txt files were included because none were relevant to the rules query.")
    else:
        # It's a single string digest from gitingest
        parts.append(f"\n```\n{codebase}\n```")

    return "\n".join(parts)


def analyze(
    rules: UsageRules,
    codebase: dict[str, str] | str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> ComplianceReport:
    """Run the compliance analysis via Gemini and return a structured report."""
    client = genai.Client(api_key=api_key)

    user_prompt = _build_user_prompt(rules, codebase)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": ComplianceReport,
                },
            )

            # Parse the JSON text into our Pydantic model
            data = json.loads(response.text)
            return ComplianceReport(**data)
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"\nERROR: Gemini API failed after {MAX_RETRIES} attempts: {e}", file=sys.stderr)
                raise
            delay = INITIAL_DELAY * (2 ** (attempt - 1))
            print(f"\n  Rate-limited (attempt {attempt}/{MAX_RETRIES}). Retrying in {delay}s ...")
            time.sleep(delay)

    # Should never reach here, but just in case
    raise RuntimeError("Exhausted retries")

