from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from control_tower.config import EMBEDDING_MODEL
import shutil, json, uuid

# Resolve data/policies/ relative to the repo root, so it works from any cwd.
POLICY_DIR = Path(__file__).resolve().parents[3] / "data" / "policies"

CHROMA_DIR = Path(__file__).resolve().parents[3] / ".chroma"
COLLECTION = "policies"

PARENT_DOCSTORE_PATH = Path(__file__).resolve().parents[3] / ".parent_docstore.json"
CHILD_DOCSTORE_PATH = Path(__file__).resolve().parents[3] / ".child_docstore.json"

def _load_catalog() -> dict:
    """Filename -> metadata, produced by scripts/generate_policies.py (the 'catalog')."""
    catalog_path = POLICY_DIR / "catalog.json"
    return json.loads(catalog_path.read_text()) if catalog_path.exists() else {}


def load_policy_documents() -> list:
    """Load every policy PDF, enriching each with metadata joined from the catalog."""
    catalog = _load_catalog()
    docs = []
    for pdf_path in sorted(POLICY_DIR.glob("*.pdf")):
        extra = catalog.get(pdf_path.name, {})
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
    """Build vectorstore with parent-child mapping.
    Stores:
    - child chunks in Chroma
    - parent chunks in .parent_docstore.json
    """
    docs = load_policy_documents()

    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)

    if PARENT_DOCSTORE_PATH.exists():
        PARENT_DOCSTORE_PATH.unlink()
    
    if CHILD_DOCSTORE_PATH.exists():
        CHILD_DOCSTORE_PATH.unlink()

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3500,
        chunk_overlap=500,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    parent_docs = parent_splitter.split_documents(docs)

    child_docs = []
    child_ids = []
    parent_store = {}
    child_store = {}

    for parent_index, parent_doc in enumerate(parent_docs):
        source = parent_doc.metadata.get("source", "unknown")
        source_file = Path(source).name if source != "unknown" else "unknown"
        page = parent_doc.metadata.get("page", "unknown")
        doc_id = parent_doc.metadata.get("doc_id", "unknown_doc")
        parent_id = f"{doc_id}:{source_file}:page_{page}:parent_{parent_index}"

        parent_doc.metadata["source_file"] = source_file
        parent_doc.metadata["parent_id"] = parent_id
        parent_doc.metadata["chunk_type"] = "parent"

        parent_store[parent_id] = {
            "page_content": parent_doc.page_content,
            "metadata": parent_doc.metadata,
        }

        children = child_splitter.split_documents([parent_doc])
        for child_index, child_doc in enumerate(children):
            child_id = f"{parent_id}:child_{child_index}"
            child_doc.metadata["source_file"] = source_file
            child_doc.metadata["parent_id"] = parent_id
            child_doc.metadata["child_id"] = child_id
            child_doc.metadata["chunk_type"] = "child"
            child_docs.append(child_doc)
            child_ids.append(child_id)

            child_store[child_id] = {
                "page_content": child_doc.page_content,
                "metadata": child_doc.metadata,
            }

    PARENT_DOCSTORE_PATH.write_text(json.dumps(parent_store, indent=2),
                                    encoding="utf-8",
    )

    CHILD_DOCSTORE_PATH.write_text(
        json.dumps(child_store, indent=2),
        encoding="utf-8",
    )

    vs = Chroma.from_documents(
        documents=child_docs,
        ids=child_ids,
        embedding=get_embeddings(),
        collection_name=COLLECTION,
        persist_directory=str(CHROMA_DIR),
        collection_metadata={"hnsw:space": "cosine"},    # clean 0–1 relevance scores
    )

    print(f"Loaded {len(docs)} PDF pages")
    print(f"Created {len(parent_docs)} parent chunks")
    print(f"Indexed {len(child_docs)} child chunks into Chroma at {CHROMA_DIR}")
    print(f"Saved parent docstore at {PARENT_DOCSTORE_PATH}")
    print(f"Saved child docstore at {CHILD_DOCSTORE_PATH}")

    return vs

if __name__ == "__main__":
    build_vectorstore()