import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# 1. Setup Environment Paths (Cross-platform using Pathlib)
current_file_dir = Path(__file__).resolve().parent
root_dir = current_file_dir.parent.parent
env_path = root_dir / ".env"

load_dotenv(dotenv_path=env_path)

# 2. Initialize Local Embeddings
print("Loading local embedding model (BGE-Small)...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
)

# 3. Initialize Qdrant Vector Store
url = os.getenv("QDRANT_URL")
api_key = os.getenv("QDRANT_API_KEY")
client = QdrantClient(url=url, api_key=api_key) if url else QdrantClient(location=":memory:")

collection_name = "source_code_collection"

# Ensure collection exists
if not client.collection_exists(collection_name):
    print(f"Creating collection '{collection_name}'...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(size=384, distance=rest.Distance.COSINE), # BGE-Small is 384
    )

vector_store = QdrantVectorStore(
    client=client,
    collection_name=collection_name,
    embedding=embeddings,
)

# 4. Target the fetched_content folder
target_dir = root_dir / "fetched_content"

if not target_dir.exists():
    print(f"Error: Could not find directory at {target_dir}")
    exit(1)

# Find all .txt files
txt_files = list(target_dir.glob("*.txt"))

if not txt_files:
    print(f"No .txt files found in {target_dir}")
    all_docs = []
else:
    print(f"Found {len(txt_files)} files in {target_dir.name}/")
    all_docs = []
    for txt_path in txt_files:
        try:
            loader = TextLoader(str(txt_path), encoding="utf-8")
            all_docs.extend(loader.load())
        except Exception as e:
            print(f"Error loading {txt_path.name}: {e}")

# 5. Standard Splitting and Fast Indexing
if all_docs:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150, add_start_index=True
    )

    all_splits = text_splitter.split_documents(all_docs)

    print(f"Adding {len(all_splits)} chunks to Qdrant...")
    vector_store.add_documents(documents=all_splits)
    print(f"Indexing complete. Database: {url}")
else:
    print("Nothing to index.")
