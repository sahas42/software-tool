from langchain_huggingface import HuggingFaceEmbeddings
import sys

print("Initializing Jina Embeddings model...")
sys.stdout.flush()

try:
    embeddings = HuggingFaceEmbeddings(
        model_name="jinaai/jina-embeddings-v2-base-code",
        model_kwargs={"device": "cpu"}
    )
    print("SUCCESS: Model loaded successfully!")
except Exception as e:
    print(f"ERROR: Failed to load model: {e}")

sys.stdout.flush()
