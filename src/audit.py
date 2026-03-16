import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI


current_file_dir = Path(__file__).resolve().parent
root_dir = current_file_dir.parent
env_path = root_dir / ".env"

if load_dotenv(dotenv_path=env_path):
    print(f"---Loaded environment variables from {env_path}")
else:
    print(f"---Warning: Could not find .env file at {env_path}. Falling back to system variables.")

print("Initializing local BGE embeddings...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"}
)

persist_db_path = current_file_dir / "rules_parser/chroma_langchain_db"
if not persist_db_path.exists():
    print(f" Error: Database folder not found at {persist_db_path}. Run ingestion first!")
    exit(1)

vector_store = Chroma(
    collection_name="source_code_collection",
    embedding_function=embeddings,
    persist_directory=str(persist_db_path),
)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(" Error: GOOGLE_API_KEY not found in .env or system environment.")
    exit(1)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=api_key,
    temperature=0
)

def run_compliance_audit(yaml_path):
    """Parses rules and checks the codebase for each one."""
    if not Path(yaml_path).exists():
        print(f" Error: YAML file not found at {yaml_path}")
        return

    with open(yaml_path, 'r') as f:
        rules_data = yaml.safe_load(f)
  
    barred_rules = rules_data.get('barred_uses', [])
    
    print(f"\n Starting Audit: Checking {len(barred_rules)} rules against codebase...")
    print("-" * 60)

    for i, rule in enumerate(barred_rules, 1):
        print(f"Checking Rule #{i}: {rule[:60]}...")
        docs = vector_store.similarity_search(rule, k=4)
        context_list = []
        for d in docs:
            src = d.metadata.get('source', 'Unknown File')
            context_list.append(f"[File: {Path(src).name}]\n{d.page_content}")
        
        code_context = "\n\n".join(context_list)

        prompt = f"""
        SYSTEM: You are a Senior Software Compliance Auditor.
        TASK: Compare the RULE below against the PROVIDED CODE SNIPPETS.

        RULE: "{rule}"

        CODE SNIPPETS:
        {code_context}

        INSTRUCTIONS:
        1. If the code clearly violates the rule, result is VIOLATION.
        2. If the code is relevant but follows the rule, result is PASS.
        3. If the code has nothing to do with this rule topic, result is NEUTRAL.

        FORMAT:
        RESULT: [STATUS]
        REASON: (Brief explanation)
        """

        try:
            response = llm.invoke(prompt)
            print(f"\n{response.content}")
        except Exception as e:
            print(f"---API Error on Rule #{i}: {e}")
            
        print("-" * 60)

if __name__ == "__main__":
    rules_yaml_path = root_dir / "examples/rules.yaml" 
    run_compliance_audit(rules_yaml_path)