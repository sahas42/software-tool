# Modules and Dependencies

This document provides a comprehensive map of the project's ecosystem. It details every functional module within the codebase, outlines the underlying features provided by each module, and pairs them with the exact libraries and frameworks utilized.

---

## 1. Frontend & User Interface Moduels

### A. Modern Next.js Interface (`frontend/`)
- **Features:**
  - Modern, responsive client-side interface substituting the original vanilla Python templates.
  - Component-based architecture for managing codebase uploads, rule submission, and streaming WebSocket results.
  - Type-safe components and automated compilation.
- **Libraries / Frameworks:**
  - `Next.js (16.2)` and `React (19.2)`: Application framework and core UI library.
  - `TailwindCSS (v4)`: Utility-first CSS framework for styling.
  - `TypeScript`: Enabling strict typing across the client side.

### B. Legacy / Vanilla Client (`webapp/`)
- **Features:** 
  - A fallback, simplistic user interface for static evaluations independent of Node.js.
  - Uses basic HTML/CSS/JS with Fetch API querying the backend.
- **Libraries / Frameworks:** 
  - Standard DOM API, Vanilla Javascript.

---

## 2. API Gateway Module

### A. Asynchronous Gateway (`main.py`)
- **Features:** 
  - Main entry point for interacting with the compliance engine asynchronously.
  - Orchestrates Celery background tasks upon an `/api/analyze` request.
  - Opens WebSocket connections (`/ws/status/{task_id}`) to stream real-time task statuses directly to the client.
  - Manages asynchronous file uploads and multipart forms.
- **Libraries / Frameworks:**
  - `FastAPI`: The hyper-fast web framework powering the backend.
  - `Uvicorn`: ASGI web server implementation.
  - `websockets`: Enabling real-time concurrent bi-directional data flow.
  - `python-multipart`: Required for processing `multipart/form-data` (ZIP, PDF uploads).

### B. Synchronous Gateway (`server.py`)
- **Features:** 
  - The legacy simple backend serving the Vanilla UI via static directories.
  - Allows blocking requests for testing and simplified deployment setups.
- **Libraries / Frameworks:** 
  - `Flask (3.0)`: Synchronous WSGI web framework.
  - `flask-cors`: CORS management handling cross-origin UI requests.

---

## 3. Background Task Execution Module

Located primarily within `celery_app.py` and `worker.py`.

- **Features:**
  - Offloads computationally expensive tasks (embeddings, generation, dynamic scaling) off the API's main thread.
  - Distributes workload across isolated nodes allowing horizontally scalable compliance checks.
  - Manages execution state updates (`PENDING`, `PROGRESS`, `SUCCESS`).
- **Libraries / Frameworks:**
  - `Celery (5.3)`: Primary queue orchestration engine.
  - `Redis (5.0)`: In-memory datastore acting as both the Message Broker and the Result Backend.

---

## 4. Advanced RAG Analysis Module

Located within `src/audit.py`, `src/semantic_chunker.py`, and `src/compliance_checker/vector_store.py`.

- **Features:**
  - Subdivides raw codebase strings into manageable, semantically-aware logical units (e.g., stopping specifically at class or function boundaries rather than arbitrary string limits).
  - Maintains `incremental` local vector databases for rapid chunk retrieval based on localized repositories.
  - Generates HyDE (Hypothetical Document Embeddings) to bridge the legal vs code linguistic variance.
- **Libraries / Frameworks:**
  - `LangChain`: Core framework for vector-db wrappers and text-splitters (e.g. `langchain-huggingface`, `langchain-google-genai`).
  - `Qdrant` (`qdrant-client`, `langchain-qdrant`): Advanced local vector store powering similarity search queries.
  - `Sentence Transformers` (`sentence-transformers`): Facilitating the `BAAI` and `jinaai` embedding models.
  - `Tree-Sitter` (`tree-sitter`, `tree-sitter-python`): For contextual AST-parsing semantic chunk splitting.

---

## 5. Core Static Analysis Engine

Located within `src/compliance_checker/analyzer.py` and `src/compliance_checker/models.py`.

- **Features:** 
  - Constructs vast context-rich prompts combining legal constraints and code slices.
  - Interfaces directly with Google's GenAI endpoint to produce deterministically shaped outputs matching predefined schemas.
- **Libraries / Frameworks:**
  - `Google GenAI SDK` (`google-genai`): The underlying API client referencing `gemini-2.5-flash`.
  - `Pydantic` (`pydantic>=2.0`): The data validation parser forcing LLM output bounds.

---

## 6. Data Ingestion & Parsers

Scattered between `src/compliance_checker/codebase_loader.py`, `src/compliance_checker/pdf_rule_extractor.py`, and the API layer.

- **Features:**
  - Fetches external remote directories optimally.
  - Destructures nested legal clauses from messy PDFs into mapped objects.
  - Pulls straightforward metrics from lightweight YAML constraints.
- **Libraries / Frameworks:**
  - `Gitingest` (`gitingest`): Re-creates local-style code digests from GitHub URLs using prompt-optimized abstractions.
  - `PyPDF` (`pypdf`): Initial text abstraction from uploaded `.pdf` documents.
  - `PyYAML` (`pyyaml`): Unmarshalling config-as-code YAML boundaries into dictionary structures.
  - `Python DotEnv` (`python-dotenv`): Variable management for parsing secure API keys.
