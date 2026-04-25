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

> **For a deep technical dive into the core pipelines and advanced RAG implementation, see [ARCHITECTURE.md](ARCHITECTURE.md).**
> **For detailed documentation of the FastAPI endpoints, WebSocket real-time queues, and Pydantic AI schemas, see [docs-and-plans/API_AND_MODELS.md](docs-and-plans/API_AND_MODELS.md).**
> **For a complete breakdown of modules, features, and external dependencies/libraries, see [docs-and-plans/MODULES_AND_DEPENDENCIES.md](docs-and-plans/MODULES_AND_DEPENDENCIES.md).**
> **For an granular file-by-file purpose guide, see [docs-and-plans/FILE_BY_FILE_BREAKDOWN.md](docs-and-plans/FILE_BY_FILE_BREAKDOWN.md).**

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

## System Capabilities & Trade-offs

The framework has been engineered to balance high-speed compliance inference with context complexity.

1. **Large-Scale Inference:** By default, the Vanilla pipeline leverages the robust 1M-token context window of Google's `gemini-2.5-flash` model, allowing instantaneous analysis of most standard codebases. For enterprise-scale monoliths, users can toggle the **Advanced RAG Pipeline**, which maps code context into a local Vector Store (Qdrant) and handles bounds dynamically via HyDE sub-agents.
2. **Rate Limit Handling:** When relying on free-tier Gemini API keys, extensive multi-chunk iterative querying via the Advanced RAG pipeline could brush against rate ceilings. To ensure stability, the backend utilizes exponential backoff to handle rate limits gracefully within background Celery tasks.
3. **Private Repository Ingestion:** While `gitingest` operates seamlessly on public GitHub repositories by natively respecting `.gitignore` paths, running audits against private repositories requires explicitly injecting a `GITHUB_TOKEN` into the environment variables.

> [!NOTE] 
> Both the "Vanilla" (full context window) and "Advanced Agentic RAG" pipelines are natively toggleable within the web interface, empowering users to dynamically select between maximum speed (Vanilla) and precision at scale (RAG).

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

# 4. Start Infrastructure Services (Docker Compose) - *OPTIONAL*
# Required ONLY if you want to run the Modern Next.js interface with Celery background tasks.
# The legacy Vanilla UI (server.py) bypasses Celery and uses an in-memory Vector store.
docker-compose up -d
```

## Usage

You must provide a valid Gemini API Key. For backend and command-line operations (CLI), you can set it in a `.env` file at the root of the project:

```bash
# Create a .env file
echo GEMINI_API_KEY=your_actual_api_key_here > .env
```

> **Note for Web Application Users:** Due to client-side validations, even if the backend environment variable is set, you **must paste your API Key** directly into the frontend UI field before submitting an audit request.

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
A basic Flask-based web interface is available for easier interaction. **This mode does not require Docker, Celery, or Redis.** It executes tasks synchronously and natively spins up the Qdrant Vector database entirely in machine memory.

```bash
python server.py
```
Then, open your browser and navigate to `http://localhost:5001`. You can upload rule files (YAML/PDF) and analyze local files, ZIP archives, or GitHub repositories directly from the UI.

### Example 4: Modern Web Application (Next.js UI)
A modern, advanced Agentic Scanner interface built with Next.js is also available. It connects to the Flask backend API and relies on Celery for background processing.

1. Start infrastructural services (if not already running):
```bash
docker-compose up -d
```

2. Start the Celery Worker (in a separate terminal):
```bash
# On Windows (use pool=solo):
celery -A celery_app.celery_app worker --loglevel=info --pool=solo
# On macOS/Linux:
# celery -A celery_app.celery_app worker --loglevel=info
```

3. Start the Flask Backend API (in another terminal):
```bash
python server.py
```

4. Start the Next.js frontend (in another terminal):
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

Once the asynchronous Celery analysis completes, the Web App elegantly renders an interactive **Compliance Report** displaying:

1. **Overall Verdict:** A massive dynamically-colored banner rendering either `✅ COMPLIANT` or `❌ NON-COMPLIANT`.
2. **Metrics & Severity Stats:** High-level count chips showcasing exactly how many `High`, `Medium`, or `Low` violations were surfaced by the LLM.
3. **AI Analysis Summary:** A paragraph breaking down the LLM's comprehensive thesis regarding the codebase adherence to the restrictions.
4. **Violation Cards:** Isolated cards displaying precisely where things went wrong:
   - **File & Location:** The path and explicit line range (e.g., `train.py · lines 39-44`).
   - **Triggered Rule:** The exact dataset constraint that was crossed.
   - **Code Snippet:** The syntax breaking the rule.
   - **Explanation:** The LLM's step-by-step reasoning explaining why the code matches the barred conditions.

You can also selectively download the structured JSON schema direct from the UI for external CICD processing or record-keeping.