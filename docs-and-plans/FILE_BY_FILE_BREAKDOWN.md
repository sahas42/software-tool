# High-Level Technical File Breakdown

This reference guide breaks down every core file within the repository, explaining its exact purpose within the larger software architecture and detailing the specific libraries and frameworks each file relies upon.

---

## 1. Root Directory

### `main.py`
- **Purpose**: Acts as the primary **Asynchronous API Gateway**. It receives HTTP traffic for new compliance audit tasks, processes file uploads (ZIPs, PDFs, raw code files), pushes tasks directly onto the background queue, and hosts WebSockets to broadcast the live progress of ongoing AI analysis.
- **Libraries/Frameworks utilized**: `FastAPI` (Core routing), `uvicorn` (ASGI Server), `python-multipart` (processing binary file uploads), `websockets` (live stream sockets).

### `server.py`
- **Purpose**: The legacy **Synchronous API Gateway**. It originally served the vanilla UI and computed AI checks blocking the main thread. Preserved as a fallback or lightweight execution standard.
- **Libraries/Frameworks utilized**: `Flask`, `flask-cors`.

### `celery_app.py`
- **Purpose**: Bootstraps the application's distributed task queue mechanism, establishing a persistent connection to the Redis message broker.
- **Libraries/Frameworks utilized**: `Celery` (Task queues), `python-dotenv` (ENV variables injection).

### `worker.py`
- **Purpose**: Defines the actual background logic for the `analyze_codebase_task` method. The background worker cluster executes this file, keeping the APIs responsive. Contains logic to push status updates (`PENDING`, `PROGRESS`, `SUCCESS`) back out of the worker pool.
- **Libraries/Frameworks utilized**: `Celery`.

### `docker-compose.yml`
- **Purpose**: Infrastructure-as-code orchestration initializing external non-python servers crucial for operations (the Redis instance and the Qdrant DB container).
- **Libraries/Frameworks utilized**: Native `Docker Compose`.

### `fetch_github.py`
- **Purpose**: An abstraction script used to download and compact GitHub repositories cleanly, skipping unneeded items like `.gitignore` artifacts.
- **Libraries/Frameworks utilized**: `gitingest`.

### `verify_acep.py`
- **Purpose**: Simple dry-run internal testing script to ensure the complex Advanced RAG methodology (`analyze_advanced`) structurally instantiates without crashing the application.

---

## 2. Core RAG Architecture (`src/`)

### `audit.py`
- **Purpose**: The brain of the **Advanced Agentic RAG Pipeline**. This script is responsible for connecting numerous subsystems. It coordinates chunking the codebase, embedding it in the vector store, generating HyDE (Hypothetical Document Embeddings) rules, and iteratively checking the codebase against specific constrained rules.
- **Libraries/Frameworks utilized**: `langchain-huggingface` (for embedding code tokens), `langchain-google-genai` (executing Gemini), `pydantic` (strictly enforcing output structures).

### `semantic_chunker.py`
- **Purpose**: Bypasses arbitrary character-count data splitting (which often breaks python code logic) by building an Abstract Syntax Tree (AST). Ensures that chunks cleanly break exactly at class definitions or function boundaries.
- **Libraries/Frameworks utilized**: `tree-sitter`, `tree-sitter-python`.

---

## 3. Compliance Checker Module (`src/compliance_checker/`)

### `analyzer.py`
- **Purpose**: Executing the **Vanilla Analysis Pipeline**. Forcases the entire retrieved codebase into a massive single-context prompt for Gemini to reason through holistically.
- **Libraries/Frameworks utilized**: `google-genai`.

### `models.py`
- **Purpose**: The absolute source-of-truth for strict object-schemas across the entire codebase. This file ensures that unstructured LLM outputs must be constrained into standardized, parseable JSON layouts denoting specifically what rules were broken and where.
- **Libraries/Frameworks utilized**: `pydantic>=2.0`.

### `vector_store.py`
- **Purpose**: An abstracted wrapper around the Qdrant databases. Automatically skips re-embedding unchanged documents (`sync_codebase`), speeding up iterative searches on the same dataset.
- **Libraries/Frameworks utilized**: `qdrant-client`, `langchain-qdrant`.

### `pdf_rule_extractor.py`
- **Purpose**: Solves the complex issue of extracting structured legal bounding rules from heavy PDFs. Extracts raw pages, bundles them into prompts, and has Gemini meticulously parse out discrete classes covering "geographic limitations", "attribution requirements", etc., into our `models.py`.
- **Libraries/Frameworks utilized**: `pypdf`, `langchain-google-genai`.

### `codebase_loader.py`
- **Purpose**: Deep filesystem recursive search script capable of sweeping large subdirectories looking for `.py` files and mapping them to active memory while bypassing specific cache and build folders.

---

## 4. Client Side Applications

### Modern Workspace (`frontend/`)
- **Purpose**: Represents the highly responsive web interface displaying WebSocket streams in real-time, supporting advanced dropzones for zip/pdf uploads.
- **Libraries/Frameworks utilized**: `Next.js` and `React` (Core reactive DOM), `TailwindCSS` (CSS tokens and utility styling).

### Legacy Workspace (`webapp/`)
- **Purpose**: Fundamental HTML workspace hosted via the Flask `server.py` static route. Primarily a demonstration tool.
- **Libraries/Frameworks utilized**: `HTML`, `CSS`, `Vanilla JS`.
