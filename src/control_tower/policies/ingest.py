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

def load_policy_documents() -> list:
    """Load every policy PDF into LangChain Document objects (one per page)."""
    docs = []
    for pdf_path in sorted(POLICY_DIR.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load())
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
    )
    print(f"Indexed {len(chunks)} chunks into Chroma at {CHROMA_DIR}")
    return vs

if __name__ == "__main__":
    build_vectorstore()