# AI-Powered Dataset Compliance Checker (MVP)

An AI-driven compliance checker designed to audit codebases and detect dataset license/usage violations. It parses a target codebase and maps it against a set of allowed and barred usage rules defined in a configuration file, utilizing the Gemini 2.5 Flash model for static analysis and reasoning.

## How It Works

The tool orchestrates an end-to-end static audit pipeline:
1. **Rule Ingestion:** Parses a YAML file (`rules.yaml`) containing the dataset metadata (license, description) alongside explicit lists of `allowed_uses` and `barred_uses`.
2. **Codebase Aggregation:** Recursively traverses the target project directory, filtering out noise (like `.git`, `__pycache__`, `venv`, etc.) and aggregating all relevant source code text.
3. **AI Analysis:** Constructs a comprehensive, context-rich prompt that merges the dataset usage constraints and the raw source code.
4. **Structured Inference:** Queries Google's generative AI (Gemini) using a strict JSON schema template to ensure the model outputs a deterministic `ComplianceReport` (via Pydantic).
5. **Violation Reporting:** The model isolates problematic code snippets, identifies the specific rule broken, assesses the severity, and provides an explanation.

## Current Architecture & Directory Structure

```text
software-tool/
├── examples/                      # Fixtures and sample code for testing
│   ├── rules.yaml                 # Sample constraints for the "CodeSearchNet" dataset
│   └── sample_project/            # A dummy ML project intentionally violating the rules
│       └── train.py               # The dummy script containing the violations
├── src/
│   └── compliance_checker/        # Core package
│       ├── __init__.py
│       ├── __main__.py            # Module entry point (python -m compliance_checker)
│       ├── analyzer.py            # Gemini API integration, retries, and schema enforcement
│       ├── cli.py                 # Command Line Interface argument parsing
│       ├── codebase_loader.py     # Filesystem traversal and source extraction
│       └── models.py              # Pydantic schemas (UsageRules, Violation, Report)
├── debug_api.py                   # Ad-hoc script to test Gemini API connectivity
├── pyproject.toml                 # Package configuration and dependencies
└── README.md                      # This document
```

## MVP Assumptions & Constraints

For this initial Minimal Viable Product roll-out, we made a few deliberate trade-offs to optimize for speed and demonstration value:

1. **Context Window Limitations:** The current codebase loader simply concatenates all `.py` files and injects them alongside the rules. This assumes the aggregate codebase text easily fits within the model's token limit (Gemini 2.5 Flash supports up to 1M tokens, which is generous but not infinite for massive monorepos).
2. **AI Provider:** We are hardcoded to use the Google GenAI SDK and specifically target the `gemini-2.5-flash` model. We also assume the usage of the free tier API which imposes rate ceilings. To mitigate 429 errors, `analyzer.py` utilizes basic exponential backoff, delaying execution and retrying.
3. **Language Scope:** Out-of-the-box, the tool only aggressively targets `.py` files. While the `--extensions` flag allows targeting `.js`, `.java`, etc., parsing mechanics (like ignoring imports, massive vendor folders, binary blobs) handles Python best at this stage.

## Setup & Installation

You should install this tool inside an isolated Python virtual environment.

```bash
# 1. Create and activate a Virtual Environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# 2. Install the package in editable mode with dependencies
pip install -e ".[dev]"
```

## Usage

You must provide a valid Gemini API Key. You can pass it explicitly, or set it as an environment variable:
```bash
# Set environment variable (Windows PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"
```

Run the package module, pointing it to both a rules file and a target codebase directory:

```bash
python -m compliance_checker --rules examples/rules.yaml --codebase examples/sample_project
```

### Example Output

If violations are found, the system will trigger a non-zero exit code (`1`) and output a structured report:

```text
Loading rules from examples\rules.yaml ...
Scanning codebase at examples\sample_project ...
  Found 1 file(s).
Sending to Gemini for analysis ...

============================================================
❌  NON-COMPLIANT — 3 violation(s) found.

  [1] HIGH — Training models for generating malicious code or exploits
      File: train.py  (lines 39)
      Snippet: exploit_dataset = dataset.filter(lambda x: "vulnerability" in x["func_code_string"].lower())
      Explanation: The code filters the dataset for vulnerabilities and proceeds to train a causal language model specifically to produce exploit code.

  # ... (other violations)

Summary: The project breaks multiple rules including redistribution of raw data...
============================================================
```

## Future Roadmap

- [ ] **Chunking & Indexing:** Introduce an AST parser and RAG-based vector database (like Chroma/FAISS) to chunk large codebases dynamically instead of naive concatenation.

- [ ] **IDE Integration?:** Expose the tool as a VS Code extension to block bad commits in real-time?
