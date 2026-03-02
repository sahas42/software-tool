"""Send codebase + rules to Gemini and get a structured compliance report."""

from __future__ import annotations
import json
import time
import sys
from google import genai
from .models import UsageRules, ComplianceReport

MAX_RETRIES = 3
INITIAL_DELAY = 10  # seconds


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


def _build_user_prompt(rules: UsageRules, codebase: dict[str, str]) -> str:
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
    for filepath, content in codebase.items():
        parts.append(f"\n### File: {filepath}")
        parts.append(f"```\n{content}\n```")

    return "\n".join(parts)


def analyze(
    rules: UsageRules,
    codebase: dict[str, str],
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

