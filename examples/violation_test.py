"""
violation_test.py — intentional compliance violations for CodeSearchNet rules.

This file is used to TEST the ComplianceAI web app and verify it catches violations.
It deliberately violates the CodeSearchNet dataset usage rules.
"""

import os
import json

# ---- VIOLATION 1: Commercial code generation product without attribution ----
# Using CodeSearchNet-trained model embeddings inside a paid SaaS product
# This violates: "Commercial code generation products without proper attribution"

class CommercialCodeSuggestor:
    """
    Paid SaaS feature: AI-powered code completion powered by a model
    trained on the CodeSearchNet dataset — sold to enterprise customers
    at $99/month. No attribution to CodeSearchNet authors is included.
    """

    def __init__(self, model_path: str):
        # Model was fine-tuned exclusively on CodeSearchNet corpus
        self.model = self._load_codesearchnet_model(model_path)

    def _load_codesearchnet_model(self, path: str):
        # Loads the fine-tuned CodeSearchNet embedding model
        return {"path": path, "trained_on": "CodeSearchNet"}

    def suggest(self, partial_code: str) -> list[str]:
        """Return top-5 code completions for the enterprise customer."""
        # Revenue-generating feature, no license disclosure
        return ["completion_1", "completion_2"]


# ---- VIOLATION 2: Redistribution of raw dataset without original license ----
# Bundling the raw CodeSearchNet JSON files into a downloadable package
# This violates: "Redistribution of raw dataset without original license"

def package_dataset_for_redistribution(output_dir: str):
    """
    Bundles the raw CodeSearchNet dataset files into a downloadable ZIP
    and uploads them to our CDN for users to download — no MIT license included.
    """
    raw_files = [
        "codesearchnet_python_train.jsonl",
        "codesearchnet_javascript_train.jsonl",
        "codesearchnet_go_train.jsonl",
    ]
    for f in raw_files:
        dest = os.path.join(output_dir, f)
        print(f"Redistributing {f} -> {dest}")  # Without original license!


# ---- VIOLATION 3: Surveillance / user profiling tool ----
# Using CodeSearchNet embeddings to profile developers and track behaviour
# This violates: "Training surveillance or user-profiling tools"

def build_developer_profile(user_id: str, code_commits: list[str]) -> dict:
    """
    Builds a surveillance profile of a developer by embedding their code
    using a CodeSearchNet-trained model and comparing against known profiles.
    Used by HR departments to monitor developer productivity and flag anomalies.
    """
    # Embed each commit using CodeSearchNet model
    profiles = {
        "user_id": user_id,
        "style_vector": [0.1, 0.2, 0.3],  # from CodeSearchNet embeddings
        "risk_score": 0.87,               # used for employee surveillance
        "flagged": True,
    }
    return profiles


# ---- VIOLATION 4: Malicious code generation ----
# Using the model to help write exploits
# This violates: "Training models for generating malicious code or exploits"

def generate_exploit_template(cve_id: str) -> str:
    """
    Uses a CodeSearchNet-based model to auto-generate exploit code
    for known CVEs. Intended for offensive security tool sold commercially.
    """
    # Leverages CodeSearchNet code patterns to craft exploit templates
    return f"# Auto-generated exploit for {cve_id}\nimport socket\n# ..."


if __name__ == "__main__":
    # Demo all violations
    suggestor = CommercialCodeSuggestor("models/codesearchnet_v2.bin")
    print(suggestor.suggest("def train_model("))

    package_dataset_for_redistribution("/tmp/redistributed_dataset")
    profile = build_developer_profile("user_42", ["commit_abc", "commit_def"])
    print(json.dumps(profile, indent=2))

    exploit = generate_exploit_template("CVE-2024-1234")
    print(exploit)
