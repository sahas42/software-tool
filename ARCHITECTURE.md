# Project Architecture & Technical Details

This document provides a deep dive into the technical architecture and underlying pipelines of the AI-Powered Dataset Compliance Checker.

## 1. High-Level Architecture Overview

The system is designed as a modular, containerized application with three main execution environments:
- **Frontend Layer:** A modern Next.js React application offering a rich user interface, plus a legacy Flask-based UI serving as a lightweight alternative.
- **Backend API & Task Queue:** A Flask server acting as the main API gateway, integrated with **Celery** (backed by **Redis**) to handle asynchronous, long-running static analysis tasks without blocking the client.
- **AI/ML Analysis Pipeline:** The core intelligence consisting of semantic code chunking, vector embeddings, Hypothetical Document Embeddings (HyDE), and LLM-powered inference (Google Gemini 2.5 Flash).

## 2. Core Analysis Pipelines

The tool supports two primary distinct auditing methodologies to accommodate codebases of different sizes and complexities:

### A. Vanilla Full-Context Analysis
Ideal for smaller codebases or specific file checking.
- The entire filtered codebase string is injected directly into a single prompt along with the dataset usage constraints.
- Capitalizes on Gemini 2.5 Flash's massive 1M+ token context window constraint bounds.
- Fast, but can become expensive or prone to hallucination for excessively large monolithic repositories.

### B. Advanced Agentic RAG Pipeline (`audit.py`)
Designed for large, enterprise-scale repositories. This pipeline bridges the semantic gap between legal constraints and raw source code using an iterative vector-search approach.

1. **Semantic Chunking:** Employs **Tree-sitter** (`semantic_chunker.py`) to parse abstract syntax trees (ASTs), intelligently splitting Python code by logical boundaries (e.g., classes, functions) rather than arbitrary character counts. A fallback mechanism (Recursive Character Splitting) handles non-Python text.
2. **Incremental Indexing:** Text chunks are embedded (e.g., using `Jina` or `BGE` models) and stored incrementally in a local **Qdrant Vector Store**.
3. **HyDE (Hypothetical Document Embeddings):** Before querying the vector database for a specific legal rule (e.g., "Do not train exploitative models"), a sub-agent tasks the LLM to generate a synthetic code snippet that *explicitly violates* that rule. 
4. **Iterative Vector Retrieval:** The vector DB is queried using the HyDE snippet rather than the legal text. This significantly boosts retrieval accuracy by matching code semantics against code semantics.
5. **Generative Inference:** The retrieved context chunks are evaluated by Gemini 2.5 Flash against the rule in question, forced to output a deterministic schema via `Pydantic` defining the exact line string, severity, and explanation of the violation.

## 3. Legal Rules Ingestion Pipeline

Rules define the bounds of the audit. The system maps unstructured legal text into a strict `UsageRules` Pydantic model (`models.py`) containing `allowed_uses`, `barred_uses`, `conditions`, `attribution_requirements`, and `redistribution_terms`.

- **YAML Parsing:** Direct mapping of static files into the Pydantic schema.
- **LLM-Powered PDF Extraction:** (`pdf_rule_extractor.py`) A dedicated sub-pipeline for nuanced legal PDFs. It replaces naive text extractions by asking an LLM to semantically read the PDF and map conditions and complex clauses directly into the nested `UsageRules` model.

## 4. Input Aggregation

The tool supports robust multi-source ingestion:
- **Local Directories & ZIPs:** Traversed recursively, with automatic noise filtering (e.g., ignoring `.venv`, `.git`, `node_modules`).
- **Remote GitHub Repositories:** Dynamically fetched via the `gitingest` module, providing a clean, prompt-optimized digest of the repository contents.

## 5. Infrastructure & Deployment (`docker-compose.yml`)

The application embraces microservices orchestration:
- **Redis:** Operates as the message broker for Celery asynchronous task distribution.
- **Qdrant:** Operates as the vector database for managing RAG-based codebase embeddings.
- **Worker Nodes:** (`worker.py`) Can be scaled horizontally. They listen to the Redis queue, execute the heavy LLM pipelines, and report status/results back to the backend.

The entire environment can be spun up using Docker Compose, providing a smooth "out-of-the-box" setup.
