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

def retrieve_policies(query: str, k: int = 4, score_threshold: float = 0.25, policy_type: str | None = None,) -> str:
    """Retrieve the most relevant ACTIVE policy passages above a relevance threshold."""
    # Hard constraints (metadata filter): only active policies, optionally one type.
    conditions = [{"status": "active"}]
    if policy_type:
        conditions.append({"policy_type": policy_type})
    where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
    retriever = _get_vectorstore().as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": k, "score_threshold": score_threshold, "filter": where},
    )
    results = retriever.invoke(query)
    if not results:
        return "(no matching policy found)"
    blocks = []
    for d in results:
        cite = d.metadata.get("doc_id") or d.metadata.get("source", "").split("/")[-1]
        blocks.append(f"[{cite}]\n{d.page_content.strip()}")
    return "\n\n".join(blocks)