import getpass
from dotenv import load_dotenv
import os
from langchain_chroma import Chroma
import bs4
from pathlib import Path
from langchain_community.document_loaders import WebBaseLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4.filter import SoupStrainer
from langchain_community.document_loaders import PyPDFLoader

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_GEMINI_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_GEMINI_API_KEY not found in .env file")

os.environ["GOOGLE_API_KEY"] = api_key


embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")


vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
)


script_dir = Path(__file__).resolve().parent
# This looks for the first file ending in .pdf
pdf_files = list(script_dir.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(f"No PDF files found in {script_dir}")

# Pick the first PDF found
target_pdf = pdf_files[0]
print(f"Loading PDF: {target_pdf.name}")

loader = PyPDFLoader(str(target_pdf))
docs = loader.load()

print(f"Loaded {len(docs)} pages from PDF.")


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # chunk size (characters)
    chunk_overlap=200,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)
all_splits = text_splitter.split_documents(docs)

print(f"Split blog post into {len(all_splits)} sub-documents.")


document_ids = vector_store.add_documents(documents=all_splits)

print(document_ids[:3])
