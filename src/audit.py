import os
import io
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

from src.compliance_checker.models import UsageRules, Violation, ComplianceReport, ViolationListWrapper
from src.compliance_checker.vector_store import IncrementalVectorStore
from src.semantic_chunker import SemanticChunker

# Load environment variables (API keys)
load_dotenv()

# Available embedding models for the Advanced RAG pipeline.
EMBEDDING_MODELS = {
    "jina": {
        "model_name": "jinaai/jina-embeddings-v2-base-code",
        "model_kwargs": {"device": "cpu", "trust_remote_code": True},
        "label": "Jina Embeddings v2 Base Code (Fixed)",
    },
    "bge": {
        "model_name": "BAAI/bge-small-en-v1.5",
        "model_kwargs": {"device": "cpu"},
        "label": "BGE-small-en-v1.5",
    },
}

def generate_hyde_snippet(rule: str, llm) -> str:
    """Generates a hypothetical code snippet that would violate the given rule."""
    prompt = f"Write a tiny, 5-line Python snippet that EXPLICITLY violates this rule: '{rule}'. Return ONLY the code."
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception:
        return rule

def _initialize_embeddings_with_timeout(model_name, model_kwargs, timeout=120):
    """
    Initialize embeddings with timeout to prevent Jina from hanging on Windows.
    Jina downloads a large model on first load which can hang indefinitely.
    """
    from langchain_huggingface import HuggingFaceEmbeddings
    import sys
    
    # On Windows, Jina is problematic - try a safer initialization approach
    if sys.platform == "win32" and "jina" in model_name.lower():
        print("[WARNING] Initializing Jina on Windows - this may take 2-5 minutes on first load...")
        # Add more env vars to help Jina load on Windows
        os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
        )
        return embeddings
    except Exception as e:
        if "jina" in model_name.lower():
            raise RuntimeError(
                f"Failed to load Jina embeddings: {str(e)}. "
                f"Jina has known issues on Windows. "
                f"Please try the BGE model or Vanilla pipeline instead."
            )
        raise

def analyze_advanced(
    rules: UsageRules, 
    codebase: dict[str, str], 
    api_key: str, 
    repo_id: str = "local_upload", 
    embed_model: str = "jina", 
    use_hyde: bool = True,
    progress_callback=None
) -> ComplianceReport:
    """Advanced RAG Pipeline: Semantic chunking + Vector Search."""
    if not api_key:
        raise ValueError("Google API Key is required for the Advanced Pipeline.")

    # Lazy imports to prevent hang on module load
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
    from langchain_core.documents import Document

    # Set attention implementation via environment variable to avoid TypeError on Windows
    os.environ['TRANSFORMERS_ATTENTION_IMPLEMENTATION'] = 'eager'

    embed_cfg = EMBEDDING_MODELS.get(embed_model, EMBEDDING_MODELS["jina"])

    if progress_callback:
        progress_callback(10, f"Loading embedding model: {embed_cfg['label']}...")

    # Initialize embeddings (Jina may take several minutes on first Windows load)
    try:
        embeddings = _initialize_embeddings_with_timeout(
            embed_cfg["model_name"],
            embed_cfg["model_kwargs"],
        )
    except RuntimeError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(
            f"Error loading {embed_cfg.get('label', 'embedding model')}: {str(e)}"
        )

    if progress_callback:
        progress_callback(20, "Chunking codebase for vector search...")

    from src.semantic_chunker import SemanticChunker
    semantic_chunker = SemanticChunker()
    fallback_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON, chunk_size=1500, chunk_overlap=150
    )

    def chunk_fn(filepath, content, metadata):
        if filepath.endswith(".py"):
            try:
                return semantic_chunker.chunk_python_file(content, metadata)
            except Exception:
                return fallback_splitter.split_documents([Document(page_content=content, metadata=metadata)])
        return fallback_splitter.split_documents([Document(page_content=content, metadata=metadata)])

    safe_repo_id = "".join(c if c.isalnum() else "_" for c in repo_id).lower()
    collection_name = f"repo_{safe_repo_id}_{embed_model}"

    store = IncrementalVectorStore(collection_name=collection_name, embeddings=embeddings)
    vector_store = store.sync_codebase(codebase, fallback_splitter, chunk_fn=chunk_fn)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
    structured_llm = llm.with_structured_output(ViolationListWrapper)

    all_violations = []
    barred_rules = rules.barred_uses
    total_rules = len(barred_rules) if barred_rules else 1

    for i, rule in enumerate(barred_rules, 1):
        if progress_callback:
            # Scaled from 30% to 90%
            progress = 30 + int((i / total_rules) * 60)
            progress_callback(progress, f"Checking rule {i}/{total_rules}: {rule[:30]}...")
            
        # Add a tiny sleep to help with Gemini rate limits
        import time
        time.sleep(2)

        search_query = generate_hyde_snippet(rule, llm) if use_hyde else rule
        retrieved_docs = vector_store.similarity_search(search_query, k=4)
        
        if not retrieved_docs: continue
            
        code_context = "\n\n".join([f"--- FILE: {d.metadata.get('source', 'Unknown')} ---\n{d.page_content}" for d in retrieved_docs])

        prompt = f"SYSTEM: Auditor. RULE: {rule}. CODE: {code_context}. Extract violations if any, else empty list []."
        try:
            violation_wrapper = structured_llm.invoke(prompt)
            if violation_wrapper and violation_wrapper.items:
                all_violations.extend(violation_wrapper.items)
        except Exception as e:
            raise RuntimeError(f"LLM API Error during Advanced Analysis: {e}")

    is_compliant = len(all_violations) == 0
    summary = f"Advanced RAG detected {len(all_violations)} potential rule violation(s)." if not is_compliant else "Advanced RAG passed. No violations found."
    return ComplianceReport(violations=all_violations, summary=summary, is_compliant=is_compliant)

def analyze_vanilla(
    rules: UsageRules, 
    codebase: dict[str, str], 
    api_key: str, 
    progress_callback=None
) -> ComplianceReport:
    """Vanilla Pipeline: Naive full-context injection."""
    if not api_key:
        raise ValueError("Google API Key is required for the Vanilla Pipeline.")

    # Lazy imports
    from langchain_google_genai import ChatGoogleGenerativeAI

    if progress_callback:
        progress_callback(10, "Preparing codebase context...")

    code_context = ""
    for filepath, content in codebase.items():
        code_context += f"\n\n--- FILE: {filepath} ---\n{content}\n"
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
    structured_llm = llm.with_structured_output(ViolationListWrapper)

    all_rules_text = "\n".join([f"- {r}" for r in rules.barred_uses + rules.conditions + rules.attribution_requirements + rules.redistribution_terms])

    prompt = f"SYSTEM: Auditor. RULES: {all_rules_text}. CODEBASE: {code_context[:800000]}. Extract violations into schema, else empty list []."

    if progress_callback:
        progress_callback(50, "Running Vanilla Gemini Analysis (Full Context)...")
    
    try:
        violation_wrapper = structured_llm.invoke(prompt)
        violations = violation_wrapper.items if violation_wrapper and hasattr(violation_wrapper, "items") else []
    except Exception as e:
        raise RuntimeError(f"LLM API Error during Vanilla Analysis: {e}")

    summary_prompt = f"Summarize codebase compliance in 3 sentences based on these rules: {all_rules_text}"
    try:
        summary_msg = llm.invoke(summary_prompt)
        summary = summary_msg.content if hasattr(summary_msg, 'content') else str(summary_msg)
    except Exception:
        summary = "Summary generation failed."

    return ComplianceReport(violations=violations, summary=summary, is_compliant=len(violations) == 0)

if __name__ == "__main__":
    print("Compliance Auditor module loaded.")
