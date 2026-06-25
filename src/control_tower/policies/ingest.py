from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from control_tower.config import EMBEDDING_MODEL
import shutil

# Resolve data/policies/ relative to the repo root, so it works from any cwd.
POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policies"

CHROMA_DIR = Path(__file__).resolve().parents[3] / ".chroma"
COLLECTION = "policies"

# Business metadata per policy doc — enables filtering + richer citations.
POLICY_META = {
    "Refund_and_Replacement_Policy.pdf":   {"doc_id": "POL-CX-001", "policy_type": "refund", "version": "1.0", "status": "active"},
    "Shipping_Delay_Compensation_Policy.pdf": {"doc_id": "POL-CX-002", "policy_type": "delay",  "version": "1.0", "status": "active"},
    "Fraud_Review_Policy.pdf":             {"doc_id": "POL-CX-003", "policy_type": "fraud",  "version": "1.0", "status": "active"},
}


def load_policy_documents() -> list:
    """Load every policy PDF into LangChain Document objects (one per page), enriched with business metadata."""
    docs = []
    for pdf_path in sorted(POLICY_DIR.glob("*.pdf")):
        extra = POLICY_META.get(pdf_path.name, {})
        loader = PyPDFLoader(str(pdf_path)).load()
        for d in loader:
            d.metadata.update(extra)
        docs.extend(loader)
    return docs

def chunk_documents(docs: list) -> list:
    """Split documents into overlapping chunks for embedding/retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_documents(docs)

def get_embeddings() -> HuggingFaceEmbeddings:
    """Local embedding model — downloads once, then runs offline, no API key."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def build_vectorstore() -> Chroma:
    """Load → chunk → embed → persist into Chroma. Idempotent: resets first."""
    chunks = chunk_documents(load_policy_documents())
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION,
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},    # clean 0–1 relevance scores
    )
    print(f"Indexed {len(chunks)} chunks into Chroma at {CHROMA_DIR}")
    return vs

if __name__ == "__main__":
    build_vectorstore()