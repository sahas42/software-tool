# Flask Application Integration Report

This report outlines exactly which files are actively invoked during the lifecycle of the **Vanilla Flask Web App** (`server.py`) execution path, as well as detailing extraneous files that exist out-of-scope for the legacy Flask context.

## 1. Files Actively Integrated with the Flask App (`server.py`)

When you run `python server.py` and communicate with `http://localhost:5001`, the following infrastructure dictates the compliance audit:

### API & Interface
- **`server.py`**: The main Flask HTTP server. Acts as the static file webserver `send_from_directory("webapp")` and controls the singular blocking route `/api/analyze`.
- **`webapp/index.html`**: The UI rendering framework defining the multi-step form execution structure.
- **`webapp/app.js`**: Controls the multi-part data payload generation, client-side HTTP `fetch` logic, and handles parsing the completed LLM metrics (violation cards) directly onto the DOM.
- **`webapp/styles.css` & `bouncing-icons.js`**: Core layout definitions mapping visual UX animations natively holding onto Web components.

### Analysis & Models Engine
The Flask App directly invokes these Python dependencies:
- **`src/compliance_checker/models.py`**: Universally maps output inference from Gemini 2.5 against `UsageRules`, `ComplianceReport`, and `Violation` components.
- **`src/compliance_checker/codebase_loader.py`**: The bridge file resolving ZIP archives and GitHub links (`gitingest`) directly off the Flask multipart form.
- **`src/compliance_checker/pdf_rule_extractor.py`**: LLM-aided parser directly called to map non-YAML binary constraints.
- **`src/compliance_checker/analyzer.py`**: Vanilla context pipeline.
- **`src/audit.py`**: Advanced Agentic RAG logic entrypoint. 
- **`src/compliance_checker/vector_store.py`**: Provides the localized `:memory:` mode Qdrant instance.
- **`src/semantic_chunker.py`**: Tree-sitter bounds chunker directly injected during `audit.py`'s analysis logic.

---

## 2. Files NOT Integrated with the Flask App

The following files exist to support the *Modern Next.js Architecture* or act as independent tooling, meaning `server.py` ignores them completely execution-wise.

### Modern Scaling Architecture
- **`main.py`**: The FastAPI server stack implementing asynchronous task streaming schemas bridging to Celery. It represents the *successor* to `server.py`.
- **`celery_app.py` & `worker.py`**: Handle distributed queues. Since `server.py` processes jobs synchronously (locking its main thread), the Celery nodes remain utterly dormant and untouched.
- **`docker-compose.yml`**: Provisions Qdrant and Redis servers natively. The Flask backend spins up Qdrant *in-memory* internally, negating the use of the orchestrated Docker instance.

### Modern App Frontends
- **`frontend/`**: The entire Next.js structure powers `localhost:3000`. `server.py` is entirely unattached from this framework component.

### Extraneous Scripts
- **`fetch_github.py`**: A standalone debugging CLI tool used to clone/extract GitHub contexts arbitrarily directly into a `fetched_content` folder format, skipping compliance logic entirely.
- **`verify_acep.py`**: An internal dry-run mock tester explicitly executed manually to trace the `analyze_advanced()` initialisation chain contextually decoupled from web servers.
- **`tests/`**: Pytest definitions utilized heavily in CI/CD chains but intentionally isolated from the `server.py` runtime environments.
