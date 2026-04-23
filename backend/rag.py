import os
import chromadb
from chromadb.utils import embedding_functions

# Use the default sentence transformers embedding function for simplicity locally
# Wait, chromadb's default embedding function requires network/dependencies if not pre-installed.
# To be safe and quick for the pilot, we'll use a very simple embedding function or just the default.
chroma_client = chromadb.PersistentClient(path="./chroma_db")

def init_rag():
    collection = chroma_client.get_or_create_collection(name="google_ads_policy")
    
    # Check if already populated
    if collection.count() > 0:
        print("RAG database already populated.")
        return collection
        
    print("Populating RAG database...")
    try:
        with open("google_ads_policy.md", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("google_ads_policy.md not found. Skipping RAG initialization.")
        return collection

    # Very naive chunking for the pilot
    chunks = content.split("\n\n")
    chunks = [c.strip() for c in chunks if len(c.strip()) > 50]
    
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": "google_ads_policy", "chunk": i} for i in range(len(chunks))]
    
    # Add to collection in batches to avoid size limits
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        collection.add(
            documents=batch_chunks,
            metadatas=batch_metadatas,
            ids=batch_ids
        )
    print(f"Added {len(chunks)} chunks to RAG database.")
    return collection

def query_rag(query: str, n_results: int = 3):
    collection = chroma_client.get_or_create_collection(name="google_ads_policy")
    if collection.count() == 0:
        return ""
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if not results['documents'] or not results['documents'][0]:
        return ""
        
    context_chunks = results['documents'][0]
    return "\n\n---\n\n".join(context_chunks)

if __name__ == "__main__":
    init_rag()
