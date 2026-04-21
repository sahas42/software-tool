"""LLM-powered extraction of structured UsageRules from legal PDF documents.

Uses pypdf for text extraction and Gemini for structured interpretation,
ensuring zero loss of nuance when converting complex legal language into
the UsageRules schema.
"""

from __future__ import annotations

import io
import json
import os
import time
import sys
from typing import Optional

from .models import UsageRules, DatasetInfo

MAX_RETRIES = 3
INITIAL_DELAY = 10

# ── Extraction prompt ──────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """\
You are an expert legal-document analyst specialising in data-use licenses,
terms of service, and dataset agreements.

You will receive the **full text** extracted from a PDF document.  Your job is
to read it exhaustively and produce a structured JSON object that captures
**every** permission, prohibition, condition, and obligation with ZERO loss of
nuance.

Output a JSON object matching this exact schema:

{
  "dataset": {
    "name":        "<dataset / product name>",
    "source":      "<URL or origin if mentioned>",
    "license":     "<license identifier or name if stated>",
    "description": "<concise summary of what the dataset contains>"
  },
  "allowed_uses":             ["<permitted use 1>", ...],
  "barred_uses":              ["<prohibited use 1>", ...],
  "conditions":               ["<conditional clause 1>", ...],
  "attribution_requirements": ["<attribution / citation obligation 1>", ...],
  "redistribution_terms":     ["<redistribution rule 1>", ...],
  "geographic_restrictions":  ["<jurisdiction constraint 1>", ...],
  "temporal_constraints":     ["<time-limited permission 1>", ...]
}

Rules for extraction:
1. Preserve the original legal wording as closely as possible — do NOT
   paraphrase into vague generalisations.
2. If a clause is conditional (e.g. "permitted only if …"), place it in
   **conditions** rather than allowed_uses or barred_uses.
3. If the document does not mention a category, use an empty list [].
4. When a single clause contains multiple distinct obligations, split them
   into separate list items.
5. For the dataset description, be concise but accurate (max ~200 words).
6. If the document is not a recognisable license/terms document, still
   extract whatever usage-related information is present and note
   "Unrecognised document format" in the dataset description.

Return ONLY the JSON — no markdown fences, no commentary.
"""


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract the complete text from every page of a PDF."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"--- Page {i + 1} ---\n{text}")
    return "\n\n".join(pages)


def _call_gemini(
    text: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash",
) -> dict:
    """Send the full PDF text to Gemini and return the parsed JSON dict."""
    from google import genai
    client = genai.Client(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Extract structured rules from the following legal document:\n\n{text}",
                config={
                    "system_instruction": EXTRACTION_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                },
            )
            return json.loads(response.text)
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(
                    f"\nERROR: Gemini extraction failed after {MAX_RETRIES} attempts: {e}",
                    file=sys.stderr,
                )
                raise
            delay = INITIAL_DELAY * (2 ** (attempt - 1))
            print(f"  Extraction retry ({attempt}/{MAX_RETRIES}) in {delay}s …")
            time.sleep(delay)

    raise RuntimeError("Exhausted retries")  # unreachable


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_rules_from_pdf(
    file_bytes: bytes,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
) -> UsageRules:
    """Extract a fully-populated UsageRules from a legal PDF.

    1. Extracts all text via pypdf.
    2. Sends the text to Gemini for structured interpretation.
    3. Validates the output against the Pydantic schema.
    4. Stores the original extracted text in ``raw_extracted_text``
       so downstream audit prompts can reference the source wording.

    Args:
        file_bytes: Raw bytes of the PDF file.
        api_key:    Gemini API key.  Falls back to the ``GEMINI_API_KEY``
                    environment variable when not supplied.
        model_name: Gemini model to use for extraction.

    Returns:
        A validated ``UsageRules`` instance.

    Raises:
        ValueError:  If no API key is available.
        RuntimeError: If Gemini extraction fails after retries.
    """
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not resolved_key:
        raise ValueError(
            "A Gemini API key is required for PDF rule extraction. "
            "Pass it explicitly or set the GEMINI_API_KEY env var."
        )

    # Step 1 — text extraction
    full_text = _extract_text_from_pdf(file_bytes)
    if not full_text.strip():
        raise ValueError("The PDF appears to contain no extractable text.")

    # Step 2 — LLM-powered structured extraction
    raw_json = _call_gemini(full_text, resolved_key, model_name)

    # Step 3 — Pydantic validation
    # Ensure nested dataset dict exists
    if "dataset" not in raw_json or not isinstance(raw_json["dataset"], dict):
        raw_json["dataset"] = {
            "name": "Unknown (extracted from PDF)",
            "description": full_text[:500],
        }

    rules = UsageRules(**raw_json)

    # Step 4 — attach the raw text for downstream audit context
    rules.raw_extracted_text = full_text

    return rules
