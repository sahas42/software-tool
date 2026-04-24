# Technical Deep Dive: API & Data Models

This document serves as an in-depth companion to the `ARCHITECTURE.md`, outlining the specific API endpoints, real-time WebSocket communication, and the underlying data schema used across the system. It is designed to aid in the maintenance of the codebase and help onboard new engineers.

## 1. API Architecture (FastAPI & Celery)

The system is transitioning away from synchronous API requests (via Flask) to an fully asynchronous architecture using **FastAPI** (`main.py`) paired with **Celery** to prevent long-running AI static analysis from blocking the main thread.

### A. Initialization & CORS
The overarching App is configured as an "Agentic Compliance Enforcement Platform" (ACEP). `main.py` leverages standard `CORSMiddleware` to allow disparate frontend web apps (like the Next.js service) to connect smoothly to the backend API residing at port `5001`.

### B. Core Endpoints

#### 1. `POST /api/analyze`
The primary entry point to trigger an audit.

- **Accepts `multipart/form-data`**:
  - `api_key`: The Gemini API Key.
  - `codebase_type`: Sourcing protocol (`github`, `files`, `zip`, `folder`).
  - `codebase_url`, `codebase_zip`, `codebase_files`: The corresponding source vectors.
  - `rules_file`: YAML or PDF mapping the structured legal constraints.
  - `pipeline_type`, `embed_model`, `use_hyde`: Toggles dictating if the RAG backend or vanilla context-window approach should be executed.
- **Functionality**:
  - Validates and securely reads data objects asynchronously.
  - Attempts to structure standard YAML inputs or defers to the LLM structured extraction pipeline (`extract_rules_from_pdf`) for PDF bounds.
  - Pushes an extensive payload into a Celery queue (`analyze_codebase_task.delay()`).
- **Returns**: A JSON packet comprising the generated `task_id` and a `PENDING` status.

#### 2. `POST /api/tasks/{task_id}/cancel`
A kill-switch endpoint.
- Invokes `celery_app.control.revoke(task_id, terminate=True)`, which kills the job on the running worker node. Vital for preventing runaway LLM queries and token expenditure.

#### 3. `GET /api/tasks/{task_id}`
A traditional HTTP polling route checking the instantaneous Celery `AsyncResult` state (e.g., `PENDING`, `PROGRESS`, `SUCCESS`, `FAILURE`).

#### 4. `WS /ws/status/{task_id}`
The real-time **WebSocket** reporting layer.
- Immediately accepts the WS handshake.
- Infinitely loops over the `AsyncResult` of the given `task_id` with a 1-second delay tick.
- Broadcasts JSON status frames containing progressing logs or the eventual final compliance report payload when `SUCCESS` is achieved.

## 2. Core Domain Data Models

We enforce rigid structures on unstructured AI inferences by utilizing **Pydantic** schema definitions mapped directly to LLM generative inference outputs (`src/compliance_checker/models.py`).

### `UsageRules`
Maps a dataset's legal and functional bounds.
- `dataset (DatasetInfo)`: Metadata (Name, License, Description, Source).
- `allowed_uses (list[str])`: Blanketly permitted objectives.
- `barred_uses (list[str])`: Strictly forbidden objectives.
- **Extended Legal Fields** (Mapped dynamically when reading PDF files):
  - `conditions`: Conditional usage clauses ("Only if X").
  - `attribution_requirements`: Citation mapping.
  - `redistribution_terms`: Guardrails on sharing.
  - `geographic_restrictions`: Jurisdiction-bounds constraints.
  - `temporal_constraints`: Time-limited privileges and expiry.

### `Violation`
The singular unit of a broken rule.
- `file (str)`: Affected script path.
- `line_range (str)`: Bounding lines containing the non-compliant code.
- `code_snippet (str)`: Exact sub-string causing the conflict.
- `violated_rule (str)`: Direct referential string tracing back to `UsageRules`.
- `severity (str)`: Categorized as High, Medium, or Low.
- `explanation (str)`: LLM's definitive reasoning highlighting exactly why the rules boundary has been breached.

### `ComplianceReport`
The terminal artifact relayed to the Client app via the WS stream.
- `violations (list[Violation])`: Array of extracted `Violation` objects.
- `summary (str)`: An overall AI-generated thesis regarding the project's adherence.
- `is_compliant (bool)`: Returns `True` natively if zero violations populate the previous array.
