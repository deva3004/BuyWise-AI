# app/rag.py
import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from app.models import SellerPolicy

CHROMA_PATH = "./chroma_data"
COLLECTION_NAME = "seller_policies"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# character-based chunking: no reliable section headers across sellers,
# so fixed-size windows with overlap are the only strategy that doesn't
# assume clean formatting. Overlap keeps a sentence that straddles a
# chunk boundary from losing its surrounding context entirely.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
_client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection() -> Collection:
    return _client.get_or_create_collection(COLLECTION_NAME)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def embed_policy(policy: SellerPolicy, collection: Collection | None = None) -> int:
    """Chunk a SellerPolicy's text, embed each chunk, and upsert into Chroma.
    Returns the number of chunks written. Metadata carries policy_id/seller_id
    so a retrieval hit can always be traced back to its Postgres row and the
    index can be rebuilt from Postgres alone.
    """
    collection = collection or get_collection()
    chunks = chunk_text(policy.policy_text)

    embeddings = _embedding_model.encode(chunks).tolist()
    ids = [f"policy-{policy.policy_id}-chunk-{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "policy_id": policy.policy_id,
            "seller_id": policy.seller_id,
            "policy_type": policy.policy_type,
            "category": policy.category or "",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    return len(chunks)


def retrieve_policy_chunks(
    query: str,
    n_results: int = 3,
    collection: Collection | None = None,
) -> list[dict]:
    collection = collection or get_collection()
    query_embedding = _embedding_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
    )

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []

    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(documents, metadatas)
    ]
