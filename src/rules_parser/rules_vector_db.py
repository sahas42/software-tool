import os
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# 1. Setup Environment
current_file_dir = Path(__file__).resolve().parent
root_dir = current_file_dir.parent.parent
env_path = root_dir / ".env"

load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
if not api_key:
    raise ValueError(f"GOOGLE_GEMINI_API_KEY not found in {env_path}")

os.environ["GOOGLE_API_KEY"] = api_key

# 2. Initialize Embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# 3. Initialize Vector Store
persist_db_path = current_file_dir / "chroma_langchain_db"
vector_store = Chroma(
    collection_name="source_code_collection",
    embedding_function=embeddings,
    persist_directory=str(persist_db_path),
)

# 4. Load Documents
target_dir = root_dir / "fetched_content"
if not target_dir.exists():
    raise FileNotFoundError(f"Could not find: {target_dir}")

txt_files = list(target_dir.glob("*.txt"))
all_docs = []
for txt_path in txt_files:
    try:
        loader = TextLoader(str(txt_path), encoding="utf-8")
        all_docs.extend(loader.load())
    except Exception as e:
        print(f"Error loading {txt_path.name}: {e}")

# 5. Split and Batch Add (to avoid Quota Error)
if all_docs:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150, add_start_index=True
    )
    all_splits = text_splitter.split_documents(all_docs)

    total_chunks = len(all_splits)
    # Gemini Free Tier limit is ~100 requests/min. We'll use batches of 90.
    batch_size = 90

    print(f"Found {len(txt_files)} files. Split into {total_chunks} chunks.")
    print(f"Adding chunks in batches of {batch_size} to avoid rate limits...")

    for i in range(0, total_chunks, batch_size):
        batch = all_splits[i : i + batch_size]
        vector_store.add_documents(documents=batch)

        remaining = total_chunks - (i + len(batch))
        print(f"Indexed {i + len(batch)}/{total_chunks} chunks. {remaining} left...")

        if remaining > 0:
            # Wait 60 seconds between batches to reset the 1-minute quota
            print("Waiting 60 seconds to reset API quota...")
            time.sleep(60)

    print(f"Indexing complete. Data saved to {persist_db_path}")
