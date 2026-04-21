import os
import io
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.compliance_checker.models import UsageRules, Violation, ComplianceReport
from src.compliance_checker.vector_store import IncrementalVectorStore
from src.semantic_chunker import SemanticChunker

# Available embedding models for the Advanced RAG pipeline.
# Keys are the UI-facing identifiers sent from the frontend.
EMBEDDING_MODELS = {
    "jina": {
        "model_name": "jinaai/jina-embeddings-v2-base-code",
        "model_kwargs": {"device": "cpu"},
        "label": "Jina Embeddings v2 Base Code",
    },
    "bge": {
        "model_name": "BAAI/bge-small-en-v1.5",
        "model_kwargs": {"device": "cpu"},
        "label": "BGE-small-en-v1.5",
    },
}

def generate_hyde_snippet(rule: str, llm: ChatGoogleGenerativeAI) -> str:
    """
    Generates a mock code snippet that explicitly violates the given rule.
    """
    prompt = f"""
    SYSTEM: You are an expert Software Engineer. Your task is to write a short, realistic code snippet that EXPLICITLY VIOLATES the following compliance rule.
    DO NOT provide any explanations, markdown formatting, or comments. ONLY output the raw code snippet that breaks the rule.
        
    RULE: "{rule}"
    """
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        # Strip markdown code blocks if the LLM adds them
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 2:
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return content.strip()
    except Exception as e:
        print(f"[Advanced Pipeline] HyDE Generation Error for rule '{rule[:30]}...': {e}")
        return rule  # Fall back to the original rule if generation fails

def analyze_advanced(
    rules: UsageRules, 
    codebase: dict[str, str] | str, 
    api_key: str, 
    repo_id: str = "default_repo",
    embed_model: str = "jina", 
    use_hyde: bool = True,
    progress_callback=None
) -> ComplianceReport:
    """
    Advanced RAG Pipeline:
    Dynamically chunks the codebase, embeds it into a managed Qdrant vector store
    incrementally, and runs a localized RAG query for each barred rule.

    Args:
        repo_id: A unique identifier for the repository (e.g., GitHub URL or folder name).
        embed_model: Key from EMBEDDING_MODELS dict. Defaults to "jina".
    """
    if not api_key:
        raise ValueError("Google API Key is required for the Advanced Pipeline.")

    # Resolve embedding config — fall back to jina if an unknown key is supplied
    embed_cfg = EMBEDDING_MODELS.get(embed_model, EMBEDDING_MODELS["jina"])

    print(f"\n[Advanced Pipeline] Initializing for repo '{repo_id}'...")
    if progress_callback:
        progress_callback(10, f"Setting up Advanced RAG Pipeline for '{repo_id}'...")

    # Normalize codebase into a dict for incremental indexing
    if not isinstance(codebase, dict):
        codebase = {"github_repository": codebase}

    # Initialize Embeddings
    print(f"[Advanced Pipeline] Loading embedding model: {embed_cfg['label']}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=embed_cfg["model_name"],
        model_kwargs=embed_cfg["model_kwargs"],
    )

    # Set up tree-sitter semantic chunker for Python + fallback for other files
    semantic_chunker = SemanticChunker()
    fallback_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON, chunk_size=1500, chunk_overlap=150
    )

    def chunk_fn(filepath, content, metadata):
        """Use tree-sitter for .py files, fallback splitter for everything else."""
        if filepath.endswith(".py"):
            return semantic_chunker.extract_chunks(content, metadata)
        else:
            doc = Document(page_content=content, metadata=metadata)
            return fallback_splitter.split_documents([doc])

    print("[Advanced Pipeline] Chunking codebase with semantic rules (Tree-sitter for Python)...")
    if progress_callback:
        progress_callback(20, "Chunking codebase for vector search...")

    # Collection name is scoped to repo and embed_model
    safe_repo_id = "".join(c if c.isalnum() else "_" for c in repo_id).lower()
    collection_name = f"repo_{safe_repo_id}_{embed_model}"

    # Incremental Vector Store setup with semantic chunking
    store = IncrementalVectorStore(collection_name=collection_name, embeddings=embeddings)
    vector_store = store.sync_codebase(codebase, fallback_splitter, chunk_fn=chunk_fn)

    # 4. Initialize LLM (Requesting JSON output matching our schema)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=api_key,
        temperature=0
    )
    
    # Create a concrete Pydantic wrapper instead of passing list[Violation] directly
    class ViolationListWrapper(BaseModel):
        items: list[Violation]
        
    # Force the model to output a strictly formatted JSON structure
    structured_llm = llm.with_structured_output(ViolationListWrapper)

    all_violations = []

    # ── Build the full rule list across all auditable categories ──
    audit_rules: list[tuple[str, str]] = []  # (category_label, rule_text)
    for rule in rules.barred_uses:
        audit_rules.append(("BARRED USE", rule))
    for rule in rules.conditions:
        audit_rules.append(("CONDITION", rule))
    for rule in rules.attribution_requirements:
        audit_rules.append(("ATTRIBUTION REQUIREMENT", rule))
    for rule in rules.redistribution_terms:
        audit_rules.append(("REDISTRIBUTION TERM", rule))
    
    print(f"\n[Advanced Pipeline] Starting Audit: Checking {len(audit_rules)} rules across all categories...")
    print("-" * 60)

    # 5. Iterative Agentic RAG Audit
    total_rules = len(audit_rules)
    for i, (category, rule) in enumerate(audit_rules, 1):
        if progress_callback:
            progress = 30 + int((i / total_rules) * 60) # Scaled from 30% to 90%
            progress_callback(progress, f"Checking rule {i}/{total_rules}: {rule[:30]}...")

        print(f"Checking [{category}] Rule #{i}: {rule[:60]}...")
        
        # Retrieve Top K suspicious chunks
        if use_hyde:
            print(f"  -> Generating HyDE snippet...")
            search_query = generate_hyde_snippet(rule, llm)
            print(f"  -> HyDE Snippet:\n{search_query}\n")
        else:
            search_query = rule

        retrieved_docs = vector_store.similarity_search(search_query, k=4)
        
        if not retrieved_docs:
            continue
            
        context_list = []
        for d in retrieved_docs:
            src = d.metadata.get('source', 'Unknown File')
            context_list.append(f"--- FILE: {src} ---\n{d.page_content}")
        
        code_context = "\n\n".join(context_list)

        prompt = f"""
        SYSTEM: You are a Senior Software Compliance Auditor analyzing code snippets retrieved via a vector search.
        
        TASK: Compare the specific {category} rule below against the PROVIDED CODE SNIPPETS to definitively determine if the rule is violated.
        
        {category} RULE: "{rule}"
        
        CODE SNIPPETS:
        {code_context}

        INSTRUCTIONS:
        - If the code clearly violates the rule, extract the exact details into the violation schema.
        - If the code is relevant but does NOT violate the rule, OR if the code is completely irrelevant to the rule, return an EMPTY LIST [].
        - Severity must be one of: "high", "medium", "low".
        - Ensure "code_snippet" is brief but specific.
        """

        try:
            # The structured output guarantees returning a wrapper containing a list of Violations
            violation_wrapper = structured_llm.invoke(prompt)
            if violation_wrapper and violation_wrapper.items:
                print(f"  -> Found {len(violation_wrapper.items)} violation(s)!")
                all_violations.extend(violation_wrapper.items)
            else:
                print("  -> Passed. No violations.")
        except Exception as e:
            print(f"--- API Error on Rule #{i}: {e}")
            
    print("-" * 60)
    
    # 6. Generate Summary and compile Report
    is_compliant = len(all_violations) == 0
    if is_compliant:
        summary = "Advanced RAG analysis passed. No specific dataset usage rules were found to be violated in the retrieved code chunks."
    else:
        summary = f"Advanced Agentic RAG detected {len(all_violations)} potential rule violation(s) across the codebase."

    return ComplianceReport(
        violations=all_violations,
        summary=summary,
        is_compliant=is_compliant
    )

if __name__ == "__main__":
    print("This module is now designed to be called programmatically via `analyze_advanced()`.")
