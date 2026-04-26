# Software Engineering Lab - Release 2 Project Proposal

## 1. OVERVIEW & PURPOSE
This document serves as the official submission guideline for Release 2 of the Software Engineering Lab project. We are proposing the development of an **AI-Powered Dataset Compliance Checker**. The project is designed to audit codebases and detect dataset license and usage violations using a combination of static analysis, Agentic RAG pipelines, and Google's Gemini 2.5 Flash model. This consolidated document covers the mandatory sections detailing our problem space, proposed solution, and technological approach.

## 2. PROBLEM STATEMENT
As open-source datasets and pre-trained models proliferate, developers often unknowingly violate complex licensing agreements and dataset usage constraints (e.g., restricted commercial use, prohibited generative training). 

Junior and senior developers alike spend countless hours manually cross-referencing legal texts with their codebase implementations. Existing static analysis tools and generic linters lack the semantic understanding required to map verbose, nuanced legal language to functional source code behavior. The absence of context-aware compliance tooling leaves a massive gap that exposes organizations to significant legal liability, copyright infringement, and ethical breaches when models are deployed or datasets are mishandled.

## 3. PROPOSED SOLUTION
We propose building an **AI-Powered Dataset Compliance Checker**, a sophisticated compliance scanning tool that bridges the gap between unstructured legal text and application source code.

**What we are building:**
- **Automated Rule Definition:** The system converts complex dataset licenses (via PDFs or YAML configuration) into structured constraints using an LLM-powered extraction pipeline to prevent the loss of legal nuance.
- **Multimodal Code Ingestion:** The tool analyzes local workspaces, uploaded ZIPs, or public GitHub repositories directly.
- **Advanced Agentic RAG Pipeline:** Our system bridges the semantic gap using Hypothetical Document Embeddings (HyDE). A sub-agent synthesizes hypothetical rule-violating code, which is then used to query the codebase vector embeddings for high-accuracy semantic matches.
- **AI-Driven Detection & Reporting:** The pipeline uses Gemini 2.5 Flash to evaluate the flagged snippets and output deterministic, line-by-line feedback explaining why a snippet violates the conditions.

**Why it is novel / better:**
Instead of traditional regex or generic token-matching, our solution translates legal jargon into code semantics and evaluates AST boundaries using Tree-sitter. This minimizes false positives and provides users with actionable remediation context rather than a simple boolean flag.

* **GitHub Repository:** [https://github.com/sahas42/software-tool](https://github.com/sahas42/software-tool) 
* Complete source code, features description, architecture, `requirements.txt`, setup steps, and comments are already included and actively maintained in the repository's `README.md` and codebase directories.

## 4. SYSTEM ARCHITECTURE
Our architecture adopts a containerized microservice design, split into three main layers:

- **Frontend Layer:** A modern Next.js web application for managing audits alongside a lightweight vanilla Flask-based UI fallback.
- **Backend API & Task Broker:** A Flask API gateway utilizing Celery and Redis. This layer orchestrates asynchronous analysis jobs, ensuring the web client remains unblocked during heavy inference.
- **AI/ML Analysis Pipeline:** The core engine utilizing Tree-sitter for semantic code chunking. Extracted chunks are stored in a local Qdrant Vector database. The pipeline leverages a HyDE (Hypothetical Document Embeddings) sub-agent and Google Gemini 2.5 Flash for the final structured generative inference.

**System Layout Diagram:**
```mermaid
flowchart TD
    UI[User Interface <br> Next.js / Flask] <--> API[Flask API Backend]
    API <--> Workers[Celery Task Workers <br> & Redis Broker]
    
    subgraph AI/ML Analysis Pipeline
        Workers --> |Code Fetch| Ingestion[Codebase Ingestion <br> Local / GitHub]
        Ingestion --> TS[Tree-sitter <br> Semantic Chunker]
        TS --> QD[(Qdrant <br> Vector DB)]
        
        Workers --> |Rule Parse| Rules[Legal Rules <br> PDF/YAML]
        Rules --> Extractor[LLM Rule Extractor]
        Extractor --> HyDE[HyDE Sub-Agent <br> Synthetic Code Generation]
        
        HyDE --> |Semantic Search| QD
        QD --> |Flagged Context| Infer[Gemini 2.5 Flash <br> Generative Inference]
    end
    
    Infer --> |Compliance Report| API
```

## 5. TECH STACK
- **Frontend:** Next.js (React) for the rich, modern web interface; vanilla HTML/CSS/JS for the lightweight UI fallback.
- **Backend:** Python alongside the Flask framework serving as the REST API gateway and orchestrator.
- **Task Scheduling / Concurrency:** Celery for asynchronous background task execution, backed by Redis acting as the message broker.
- **Database (Vector Store):** Qdrant (deployed locally via Docker) for robust indexing and semantic search over code embeddings.
- **AI / ML:** Google Gemini 2.5 Flash via API (for extraction, reasoning, and context-aware static code analysis); Tree-sitter for semantic abstract syntax tree (AST) codebase chunking; Jina/BGE equivalent variants for text embedding.
- **DevOps / Collaboration:** Docker and Docker Compose for infrastructure orchestration and seamless local provisioning; Git/GitHub for version control.

## 6. TEAM ROLES

*Clearly define the role and responsibilities of each team member. Every member must have a distinct, meaningful contribution to the project. Generic or overlapping roles are not acceptable. Each member must also list the specific tasks they personally completed for Release 1 — not just their role title. Contributions must be verifiable through GitHub commits or task logs.*

- **Member Name:** [Insert Name 1]
  - **Role Title:** [Insert Role]
  - **Specific Responsibilities:** [Detail specific responsibilities here]

- **Member Name:** [Insert Name 2]
  - **Role Title:** [Insert Role]
  - **Specific Responsibilities:** [Detail specific responsibilities here]


- **Member Name:** [Insert Name 3]
  - **Role Title:** [Insert Role]
  - **Specific Responsibilities:** [Detail specific responsibilities here]



## 7. AI USAGE DECLARATION

### Sahasvat

- **Architecture & Planning:** I manually defined most of the system design, using AI purely to validate and refine my instincts.
- **Code Generation:** Code was scaffolded using generative AI via strictly orchestrated, detailed prompts.
- **Quality Assurance:** Every line of my AI-crafted code was rigorously reviewed to prevent and fix unintended behavior.
- **Research:** Leveraged LLMs to break down and understand unfamiliar code snippets.

*My workflow reflects responsible AI usage: automating boilerplate to focus on high-level engineering, rather than blindly relying on AI outputs.*


### Prathamesh


## 8. PROMPTS

### Sahasvat

Please find links to my chats here: https://drive.google.com/drive/folders/1iPlRRQo2XlbHTwvBJRHeUMXurdeWuAvA?usp=sharing 

### Prathamesh

## 9. PROJECT DOCUMENTATION

*For comprehensive technical specifications, API schemas, design decisions, and system blueprints, please refer to the global documentation files housed within the project repository:*

- [Main Project README](https://github.com/sahas42/software-tool/blob/main/README.md)
- [System Architecture](https://github.com/sahas42/software-tool/blob/main/ARCHITECTURE.md)
- [API & Models Requirements](https://github.com/sahas42/software-tool/blob/main/docs-and-plans/API_AND_MODELS.md)
- [File-by-File Breakdown](https://github.com/sahas42/software-tool/blob/main/docs-and-plans/FILE_BY_FILE_BREAKDOWN.md)
- [Flask Integration Report](https://github.com/sahas42/software-tool/blob/main/docs-and-plans/FLASK_INTEGRATION_REPORT.md)
- [Modules & Dependencies](https://github.com/sahas42/software-tool/blob/main/docs-and-plans/MODULES_AND_DEPENDENCIES.md)
- [SOTA Code Embedding Models Report](https://github.com/sahas42/software-tool/blob/main/literature-review/SOTA_Code_Embedding_Models_Report.md)
