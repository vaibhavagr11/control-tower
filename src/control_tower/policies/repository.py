from functools import lru_cache
import json
from langchain_chroma import Chroma
from langchain_core.documents import Document
from control_tower.policies.ingest import CHROMA_DIR, COLLECTION, get_embeddings, PARENT_DOCSTORE_PATH, CHILD_DOCSTORE_PATH
from langchain_openai import ChatOpenAI
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from control_tower.config import CLASSIFIER_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, RERANKER_MODEL, RERANK_SCORE_MIN
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.retrievers import BM25Retriever


@lru_cache(maxsize=1)
def _get_vectorstore() -> Chroma:
    """Open the persisted Chroma index for querying (built by ingest.py)."""
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

@lru_cache(maxsize=1)
def _get_child_store() -> dict:
    """Load ingested child chunks created by ingest.py."""
    return json.loads(CHILD_DOCSTORE_PATH.read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def _get_parent_store() -> dict:
    """Load parent chunks created by ingest.py."""
    return json.loads(PARENT_DOCSTORE_PATH.read_text(encoding="utf-8"))

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

@lru_cache(maxsize=1)
def _get_active_chunks() -> tuple[Document, ...]:
    """
    Active child chunks for BM25.
    These come from ingest output, so they already have parent_id and child_id.
    """
    child_store = _get_child_store()
    chunks = []

    for child_id, child_data in child_store.items():
        metadata = child_data["metadata"]

        if metadata.get("status") != "active":
            continue

        chunks.append(
            Document(
                page_content=child_data["page_content"],
                metadata=metadata,
            )
        )

    return tuple(chunks)

def _children_to_parents(child_docs: list[Document]) -> list[Document]:
    """
    Convert retrieved child chunks into their parent chunks.
    Chroma/BM25 finds small child chunks.
    Each child chunk has metadata['parent_id'].
    We use that parent_id to fetch the larger parent chunk from .parent_docstore.json.
    """
    parent_store = _get_parent_store()
    parent_docs = []
    seen_parent_ids = set()

    for child_doc in child_docs:
        parent_id = child_doc.metadata.get("parent_id")

        if not parent_id:
            continue
        if parent_id in seen_parent_ids:
            continue
        parent_data = parent_store.get(parent_id)
        if not parent_data:
            continue
        parent_docs.append(
            Document(
                page_content=parent_data["page_content"],
                metadata = {
                    **parent_data["metadata"],
                    "parent_id": parent_id,
                    "retrieved_from_child_id": child_doc.metadata.get("child_id"),
                },
            )
        )
        seen_parent_ids.add(parent_id)

    return parent_docs

def _add_anchor_parent_docs(parent_docs: list[Document]) -> list[Document]:
    """
    Add early rule-definition parent chunks for any policy doc already retrieved.

    Why:
    Retrieval often finds example pages because examples repeat rule names.
    But the actual rule text usually lives near the beginning of the policy.
    """

    parent_store = _get_parent_store()

    existing_parent_ids = {
        doc.metadata.get("parent_id")
        for doc in parent_docs
        if doc.metadata.get("parent_id")
    }

    retrieved_doc_ids = {
        doc.metadata.get("doc_id")
        for doc in parent_docs
        if doc.metadata.get("doc_id")
    }

    extra_docs = []

    for parent_id, parent_data in parent_store.items():
        metadata = parent_data["metadata"]
        doc_id = metadata.get("doc_id")
        page = metadata.get("page")

        if doc_id not in retrieved_doc_ids:
            continue

        if parent_id in existing_parent_ids:
            continue

        # Pull early pages because policy rule definitions usually live there.
        if page not in [0, 1, "0", "1"]:
            continue

        extra_docs.append(
            Document(
                page_content=parent_data["page_content"],
                metadata={
                    **metadata,
                    "parent_id": parent_id,
                    "added_as_anchor_parent": True,
                },
            )
        )

    return parent_docs + extra_docs

def _rerank_and_gate(query: str, docs: list[Document], top_n: int) -> list[Document]:

    """Score parent docs with cross-encoder, remove weak matches, and sort strongest first."""
    if not docs:
        return []
    scores = _get_reranker().model.score(
        [(query, doc.page_content) for doc in docs]
    )

    scored_docs = list(zip(docs, scores))

    # Gate weak matches.
    scored_docs = [
        (doc, score)
        for doc, score in scored_docs
        if score >= (RERANK_SCORE_MIN)
    ]

    # Sort strongest first.
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _score in scored_docs[:top_n]]

def retrieve_policy_docs(
    query: str,
    k: int = 3,
    score_threshold: float = 0.30,
    policy_type: str | None = None,
) -> list[Document]:
    """
    Hybrid child retrieval → parent expansion → parent reranking.

    Flow:
    1. Chroma retrieves semantic child chunks.
    2. BM25 retrieves lexical child chunks.
    3. Ensemble combines both child retrievers.
    4. Child chunks are mapped to parent chunks.
    5. Parent chunks are reranked and gated.
    """

    conditions = [{"status": "active"}]

    if policy_type:
        conditions.append({"policy_type": policy_type})

    where = conditions[0] if len(conditions) == 1 else {"$and": conditions}

    # Semantic retrieval over child chunks in Chroma.
    base_child_retriever = _get_vectorstore().as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": max(k * 8, 24),
            "score_threshold": score_threshold,
            "filter": where,
        },
    )

    mqr = MultiQueryRetriever.from_llm(
        retriever=base_child_retriever,
        llm=_get_query_llm(),
    )

    # Lexical retrieval over ingested child chunks.
    # These chunks now have parent_id, so they can be expanded to parents.
    bm25 = BM25Retriever.from_documents(list(_get_active_chunks()))
    bm25.k = max(k * 8, 24)

    hybrid = EnsembleRetriever(
        retrievers=[bm25, mqr],
        weights=[0.4, 0.6],
    )

    # Retrieve child chunks.
    child_results = hybrid.invoke(query)

    # Expand child chunks to parent chunks.
    parent_results = _children_to_parents(child_results)
    ranked_parent_results = _rerank_and_gate(query, parent_results, top_n=max(k, 5))
    final_results = _add_anchor_parent_docs(ranked_parent_results)

    # Rerank and gate parent chunks.
    return final_results

def retrieve_policies(query: str, k: int = 3, score_threshold: float = 0.30, policy_type: str | None = None,) -> str:
    
    """Format retrieved parent policy docs into the prompt string (used by the resolver)."""
    results = retrieve_policy_docs(query, k, score_threshold, policy_type)
    
    if not results:
        return "(no matching policy found)"
    
    blocks, seen = [], set()
    for d in results:
        key = (d.metadata.get("doc_id"), d.metadata.get("parent_id"))
        if key in seen:
            continue
        seen.add(key)
        cite = d.metadata.get("doc_id") or d.metadata.get("source_file") or d.metadata.get("source", "").split("/")[-1]
        blocks.append(f"[{cite}]\n{d.page_content.strip()}")
    return "\n\n".join(blocks)