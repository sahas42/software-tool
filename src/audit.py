import os
import io
import json
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.compliance_checker.models import UsageRules, Violation, ComplianceReport

def analyze_advanced(rules: UsageRules, codebase: dict[str, str] | str, api_key: str) -> ComplianceReport:
    """
    Advanced RAG Pipeline:
    Dynamically chunks the codebase in-memory, embeds it, and runs a localized RAG query
    for each barred rule, aggregating the results into a final structured ComplianceReport.
    """
    if not api_key:
        raise ValueError("Google API Key is required for the Advanced Pipeline.")
        
    print(f"\n[Advanced Pipeline] Initializing...")

    # 1. Parse into Langchain Documents
    docs = []
    if isinstance(codebase, dict):
        for filepath, content in codebase.items():
            docs.append(Document(page_content=content, metadata={"source": filepath}))
    else:
        # If codebase is a single string (like from gitingest remote fetch)
        docs.append(Document(page_content=codebase, metadata={"source": "github_repository"}))

    # 2. Smart Chunking (Python focused but works decently for generic text)
    print("[Advanced Pipeline] Chunking codebase...")
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON, chunk_size=1500, chunk_overlap=150
    )
    texts = splitter.split_documents(docs)
    print(f"[Advanced Pipeline] Created {len(texts)} semantic chunks.")

    # 3. Fast In-Memory Vector Store setup
    print("[Advanced Pipeline] Initializing local BGE embeddings and building ephemeral index...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"}
    )
    
    # Create an ephemeral Chroma DB explicitly (no persistent directory)
    vector_store = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        collection_name="ephemeral_source_code"
    )

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
    barred_rules = rules.barred_uses
    
    print(f"\n[Advanced Pipeline] Starting Audit: Checking {len(barred_rules)} barred rules...")
    print("-" * 60)

    # 5. Iterative Agentic RAG Audit
    for i, rule in enumerate(barred_rules, 1):
        print(f"Checking Rule #{i}: {rule[:60]}...")
        
        # Retrieve Top K suspicious chunks
        retrieved_docs = vector_store.similarity_search(rule, k=4)
        
        if not retrieved_docs:
            continue
            
        context_list = []
        for d in retrieved_docs:
            src = d.metadata.get('source', 'Unknown File')
            context_list.append(f"--- FILE: {src} ---\n{d.page_content}")
        
        code_context = "\n\n".join(context_list)

        prompt = f"""
        SYSTEM: You are a Senior Software Compliance Auditor analyzing code snippets retrieved via a vector search.
        
        TASK: Compare the specific barred RULE below against the PROVIDED CODE SNIPPETS to definitively determine if the rule is violated.
        
        BARRED RULE: "{rule}"
        
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