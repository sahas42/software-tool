import hashlib
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
import os

def get_file_hash(content: str) -> str:
    """Returns the SHA-256 hash of the content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def get_qdrant_client() -> QdrantClient:
    """Initializes and returns a QdrantClient based on environment variables."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if url:
        return QdrantClient(url=url, api_key=api_key)
    return QdrantClient(location=":memory:")

class IncrementalVectorStore:
    def __init__(self, collection_name: str, embeddings: Embeddings):
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.client = get_qdrant_client()
        
        # We need the embedding dimension to create the collection if it doesn't exist.
        # This is a bit tricky with LangChain because it doesn't always expose it.
        # But we can try to embed a dummy string.
        try:
            sample_vector = self.embeddings.embed_query("dummy")
            vector_size = len(sample_vector)
        except Exception:
            vector_size = 768  # Fallback for Jina
            
        # Ensure collection exists
        if not self.client.collection_exists(self.collection_name):
            print(f"[VectorStore] Creating collection '{self.collection_name}' with size {vector_size}...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
            )
        
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    def sync_codebase(self, codebase: Dict[str, str], splitter, chunk_fn=None):
        """
        Incrementally synchronizes the codebase with the vector store.
        1. Identifies changed/new/deleted files.
        2. Updates the vector store accordingly.
        """
        print(f"[Incremental Indexing] Syncing {len(codebase)} files with collection '{self.collection_name}'...")
        
        # 1. Fetch all existing file hashes for this repo from the metadata
        # In Qdrant, we can use scroll to get all points if needed, 
        # but it's better to store a 'manifest' or just query per file.
        # For simplicity and robustness, we'll check each file.
        
        for filepath, content in codebase.items():
            current_hash = get_file_hash(content)
            
            # Check if this file with this hash already exists in the collection
            # We use a filter to find chunks for this source AND hash
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=rest.Filter(
                    must=[
                        rest.FieldCondition(key="metadata.source", match=rest.MatchValue(value=filepath)),
                        rest.FieldCondition(key="metadata.file_hash", match=rest.MatchValue(value=current_hash)),
                    ]
                ),
                limit=1,
                with_payload=False,
            )
            
            points, _ = search_result
            if points:
                # File is unchanged, skip
                # print(f"  -> {filepath} (unchanged)")
                continue
            
            # File is new or changed. 
            # First, delete old chunks for this file (if any)
            print(f"  -> {filepath} (updating/adding)")
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=rest.FilterSelector(
                    filter=rest.Filter(
                        must=[
                            rest.FieldCondition(key="metadata.source", match=rest.MatchValue(value=filepath)),
                        ]
                    )
                ),
            )
            
            # Create new chunks — use custom chunk_fn if provided, else default splitter
            metadata = {"source": filepath, "file_hash": current_hash}
            if chunk_fn is not None:
                chunks = chunk_fn(filepath, content, metadata)
                # Ensure file_hash is in all chunk metadata
                for c in chunks:
                    c.metadata["file_hash"] = current_hash
            else:
                doc = Document(page_content=content, metadata=metadata)
                chunks = splitter.split_documents([doc])
            
            # Add to vector store
            self.vector_store.add_documents(chunks)

        # 2. Handle deleted files (files in Qdrant but not in current codebase)
        # Fetch all unique sources currently in the collection
        # This is a bit expensive if there are millions of chunks, 
        # but for most codebases it's fine.
        
        all_sources = set()
        offset = None
        while True:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=["metadata.source"], # Match LangChain structure
                with_vectors=False,
            )
            points, offset = scroll_result
            for p in points:
                if p.payload and "metadata" in p.payload and "source" in p.payload["metadata"]:
                    all_sources.add(p.payload["metadata"]["source"])
            if offset is None:
                break
        
        deleted_files = all_sources - set(codebase.keys())
        for filepath in deleted_files:
            if filepath == "github_repository" and "github_repository" not in codebase:
                 # Special case for gitingest digest
                 pass
            elif filepath != "github_repository":
                print(f"  -> {filepath} (deleted)")
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=rest.FilterSelector(
                        filter=rest.Filter(
                            must=[
                                rest.FieldCondition(key="metadata.source", match=rest.MatchValue(value=filepath)),
                            ]
                        )
                    ),
                )
        
        print(f"[Incremental Indexing] Sync complete.")
        return self.vector_store
