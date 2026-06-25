from functools import lru_cache
from langchain_chroma import Chroma
from control_tower.policies.ingest import CHROMA_DIR, COLLECTION, get_embeddings

@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    """Open the persisted Chroma index for querying (built by ingest.py)."""
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

def retrieve_policies(query: str, k: int = 3) -> str:
    """Return the top-k most relevant policy passages for a natural-language query."""
    results = _get_vectorstore().similarity_search(query, k=k)
    if not results:
        return "(no matching policy found)"
    blocks = []
    for d in results:
        source = d.metadata.get("source", "").split("/")[-1]
        blocks.append(f"[{source}]\n{d.page_content.strip()}")
    return "\n\n".join(blocks)