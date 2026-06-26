from functools import lru_cache
from langchain_chroma import Chroma
from control_tower.policies.ingest import CHROMA_DIR, COLLECTION, get_embeddings
from langchain_openai import ChatOpenAI
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from control_tower.config import CLASSIFIER_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, RERANKER_MODEL
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    """Open the persisted Chroma index for querying (built by ingest.py)."""
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

@lru_cache(maxsize=1)
def _get_query_llm() -> ChatOpenAI:
    """Cheap model used only to generate alternate phrasings of the query."""
    return ChatOpenAI(
        model=CLASSIFIER_MODEL,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoderReranker:
    model = HuggingFaceCrossEncoder(model_name=RERANKER_MODEL)
    return CrossEncoderReranker(model=model, top_n=3)

def retrieve_policies(query: str, k: int = 4, score_threshold: float = 0.30, policy_type: str | None = None,) -> str:
    """Multi-query retrieval over active policies, above a relevance threshold."""    
    conditions = [{"status": "active"}]
    if policy_type:
        conditions.append({"policy_type": policy_type})
    where = conditions[0] if len(conditions) == 1 else {"$and": conditions}

    # Base retriever: your tuned threshold + metadata filter.
    base = _get_vectorstore().as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": k, "score_threshold": score_threshold, "filter": where},
    )

    # Multi-query: LLM rephrases the query N ways, retrieves each, unions results.
    mqr = MultiQueryRetriever.from_llm(retriever=base, llm=_get_query_llm())

    compressor = _get_reranker() 

    retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=mqr,
    )
    
    results = retriever.invoke(query)
    if not results:
        return "(no matching policy found)"
    
    blocks, seen = [], set()
    for d in results:
        key = (d.metadata.get("doc_id"), d.page_content[:60])
        if key in seen:
            continue
        seen.add(key)
        cite = d.metadata.get("doc_id") or d.metadata.get("source", "").split("/")[-1]
        blocks.append(f"[{cite}]\n{d.page_content.strip()}")
    return "\n\n".join(blocks)