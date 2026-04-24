# AI-Powered Dataset Compliance Checker (MVP)

An AI-driven compliance checker designed to audit codebases and detect dataset license/usage violations. It parses a target codebase and maps it against a set of allowed and barred usage rules defined in a configuration file, utilizing the Gemini 2.5 Flash model for static analysis and reasoning.

## Key Features

- **Modern Web Interface:** A highly interactive Next.js web application for managing audits, supplemented by a vanilla Flask API and UI.
- **Versatile Code Input:** Analyze code via remote GitHub URLs, uploaded ZIP archives, multiple local file uploads, or entire directory folders.
- **LLM-Powered Rules Extraction:** Supply compliance rules via standard YAML configuration files, or use the advanced LLM-powered pipeline to structure and extract nuanced contextual usage rules directly from complex legal PDF documents (replacing naive text extraction).
- **Asynchronous Processing:** Robust background task execution using Celery and Redis to handle long-running code analysis jobs efficiently without blocking the web interface.
- **Local & Remote Scanning:** Traverse local directories or dynamically fetch public GitHub repositories using `gitingest`.
- **Dockerized Infrastructure:** Simplified local deployment orchestration via Docker Compose incorporating Qdrant and Redis services out of the box.
- **Advanced Agentic RAG & HyDE Generation:** An integrated targeted audit pipeline that chunks the codebase and uses a HyDE (Hypothetical Document Embeddings) sub-agent to dynamically synthesize mock-violating code snippets matching your rules. Powered by a local Vector database, this bridges the semantic gap between legal language and actual source code for highly precise vector retrieval.
- **AI-Driven Analysis:** Leverages Google's Gemini 2.5 Flash model for context-aware static code analysis and precise violation detection.

## How It Works

The tool orchestrates an end-to-end static audit pipeline:
1. **Rule Ingestion:** Parses a YAML file (`rules.yaml`) containing the dataset metadata (license, description) alongside explicit lists of `allowed_uses` and `barred_uses`.
2. **Codebase Aggregation:** 
   - *Local Mode:* Recursively traverses the target project directory, filtering out noise (like `.git`, `__pycache__`, `venv`, etc.) and aggregating all relevant source code text.
   - *Remote Mode:* Dynamically accepts a GitHub URL and fetches a prompt-optimized code digest via the `gitingest` library.
3. **AI Analysis:** Constructs a comprehensive, context-rich prompt that merges the dataset usage constraints and the raw source code.
4. **Structured Inference:** Queries Google's generative AI (Gemini 2.5 Flash) using a strict JSON schema template to ensure the model outputs a deterministic `ComplianceReport` (via Pydantic).
5. **Violation Reporting:** The model isolates problematic code snippets, identifies the specific rule broken, assesses the severity, and provides an explanation.

## Current Architecture & Directory Structure

```text
software-tool/
├── .env                           # Local environment variables (GEMINI_API_KEY)
├── backend/                       # Backend specific files
├── celery_app.py                  # Celery app initialization for background tasks
├── docker-compose.yml             # Docker composition for services
├── docs-and-plans/                # Project planning and SRS documents
├── examples/                      # Fixtures and sample code for testing
│   ├── rules.yaml                 # Sample constraints
│   └── sample_project/            # Dummy ML project intentionally violating the rules
├── fetch_github.py                # Script to scrape code from public repositories
├── frontend/                      # Modern Next.js web application interface
├── literature-review/             # SOTA review and research documents
├── main.py                        # Main entry point script
├── plan/                          # Legacy and current release plans
├── pyproject.toml                 # Package configuration and dependencies
├── README.md                      # This document
├── requirements.txt               # Required Python packages
├── server.py                      # Flask web server to run the vanilla frontend
├── src/
│   ├── audit.py                   # Advanced Agentic RAG Pipeline logic
│   ├── compliance_checker/        # Core CLI and static analysis package
│   │   ├── analyzer.py            # Core AI analysis and inference
│   │   ├── pdf_rule_extractor.py  # Structured PDF rule extraction
│   │   └── vector_store.py        # Vector database abstractions
│   ├── rules_parser/              # Modules for parsing YAML and PDF rules
│   └── semantic_chunker.py        # Tree-sitter powered code parser and chunker
├── tests/                         # Automated unit tests (Pytest)
│   ├── test_hyde.py
│   ├── test_pdf_rule_extractor.py
│   └── test_semantic_chunker.py
├── webapp/                        # Frontend UI assets (HTML, CSS, JS)
└── worker.py                      # Worker script for long-running processes
```

## MVP Assumptions & Constraints

For this initial Minimal Viable Product roll-out, we made a few deliberate trade-offs to optimize for speed and demonstration value:

1. **Context Window Limitations:** The tool assumes the aggregate codebase text easily fits within the model's token limit (Gemini 2.5 Flash natively supports up to 1M tokens). Very massive repositories might still hit this boundary.
2. **AI Provider:** We are hardcoded to use the Google GenAI SDK and specifically target the `gemini-2.5-flash` model. We also assume the usage of the free tier API which imposes rate ceilings. To mitigate 429 errors, `analyzer.py` utilizes exponential backoff to handle rate limits gracefully.
3. **Remote Parsing:** The integration of `gitingest` natively pulls `.gitignore` respected code. Ensure private repositories provide a `GITHUB_TOKEN` to gitingest via environment variables if used.

> [!NOTE] 
> **Current State of Development:** Both the "Vanilla" (full context window) and "Advanced RAG" (chunking, embedding, vector search, and HyDE sub-agent) pipelines are now fully integrated into the Web Application. Users can toggle between these modes and select their retrieval strategies directly from the UI.

## Setup & Installation

You should install this tool inside an isolated Python virtual environment.

```bash
# 1. Clone the repository and navigate to the project root
git clone https://github.com/sahas42/software-tool.git
cd software-tool

# 2. Create and activate a Virtual Environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# 3. Install the dependencies
# Option A (Recommended): Install the package itself in editable mode along with all dev/frontend dependencies via pyproject.toml
pip install -e ".[dev]"

# Option B: Alternatively, if you just want to install the required packages without installing the compliance checker as a module
pip install -r requirements.txt
```

## Usage

You must provide a valid Gemini API Key. You can set it in a `.env` file at the root of the project to avoid passing it every time:

```bash
# Create a .env file
echo GEMINI_API_KEY=your_actual_api_key_here > .env
```

**CRITICAL NOTE:** Always run the commands below from the *root directory of the project* (`software-tool/`), **not** from inside the `src/` directory. If you run it from `src/`, relative paths like `examples/rules.yaml` will fail with a `FileNotFoundError`.

### Example 1: Local Codebase Check
Run the package module, pointing it to both a rules file and a target codebase directory:

```bash
python -m compliance_checker --rules examples/rules.yaml --codebase examples/sample_project
```

### Example 2: Remote GitHub Repository Check
You can pass a GitHub URL to the `--codebase` flag to scrape public repositories dynamically:

```bash
python -m compliance_checker --rules examples/rules.yaml --codebase https://github.com/sahas42/ocr
```

### Example 3: Web Application (Vanilla UI)
A basic Flask-based web interface is available for easier interaction:

```bash
python server.py
```
Then, open your browser and navigate to `http://localhost:5001`. You can upload rule files (YAML/PDF) and analyze local files, ZIP archives, or GitHub repositories directly from the UI.

### Example 4: Modern Web Application (Next.js UI)
A modern, advanced Agentic Scanner interface built with Next.js is also available. It connects to the Flask backend API.

First, ensure the backend is running:
```bash
python server.py
```

Then, in a separate terminal, install dependencies and start the Next.js frontend:
```bash
cd frontend
npm install
npm run dev
```
Finally, open your browser and navigate to `http://localhost:3000` to access the modern web app interface.


### Running Tests
To run the automated test suite and prevent module resolution errors (like `ModuleNotFoundError`), always use the `pytest` module flag from the project root:

```bash
python -m pytest tests/
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

- [ ] **IDE Integration?:** Expose the tool as a VS Code extension to block bad commits in real-time?

- [ ] **Auto-Compliance Check on Push:** Automatically run the compliance check on every push to the repository.
