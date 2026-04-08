import os
import fitz  # pymupdf
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb

load_dotenv()

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "documents"   # one shared collection for all uploaded docs
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        for block in blocks:
            if block[6] == 0:  # text block only
                text = block[4].strip()
                if text:
                    full_text += text + "\n\n"
    doc.close()
    return full_text


def split_text_into_chunks(text: str) -> list[str]:
    """
    Split text into overlapping chunks.
    RecursiveCharacterTextSplitter tries paragraph breaks first (\n\n),
    then sentence breaks (\n), then word breaks, then characters.
    This keeps semantically related content together.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(text)
    print(f"Split into {len(chunks)} chunks.")
    return chunks


def document_already_ingested(doc_name: str) -> bool:
    """
    Check if a document has already been ingested into ChromaDB.

    This prevents accidentally embedding the same PDF twice, which would
    double all its chunks and skew retrieval results toward that document.

    We query Chroma's metadata filter for any chunk whose 'source'
    equals the document name. If we find one, it's already ingested.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        # 'where' is Chroma's metadata filter syntax — like SQL WHERE clause
        results = collection.get(where={"source": doc_name}, limit=1)
        return len(results["ids"]) > 0
    except Exception:
        return False


def list_ingested_documents() -> list[str]:
    """
    Returns all unique document names currently stored in ChromaDB.
    Used by the GET /documents endpoint so the frontend can show
    what has been uploaded.
    We fetch all chunk metadata and extract unique 'source' values.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        # get() with include=["metadatas"] returns metadata without vectors
        results = collection.get(include=["metadatas"])
        sources = set()
        for meta in results["metadatas"]:
            if meta and "source" in meta:
                sources.add(meta["source"])
        return sorted(list(sources))
    except Exception:
        return []


def delete_document(doc_name: str) -> bool:
    """
    Deletes all chunks belonging to a specific document from ChromaDB.
    Chroma's delete() with a 'where' filter removes all entries
    matching that metadata condition.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        collection.delete(where={"source": doc_name})
        print(f"Deleted all chunks for: {doc_name}")
        return True
    except Exception as e:
        print(f"Failed to delete {doc_name}: {e}")
        return False


def embed_and_store(chunks: list[str], doc_name: str) -> None:
    """
    Embeds each chunk and stores it in the shared ChromaDB collection.
    Each chunk gets metadata: {"source": doc_name, "chunk_index": i}
    This metadata enables:
    1. Showing which document each answer came from (source cards)
    2. Filtering searches to a specific document
    3. Deleting a document's chunks when re-ingesting
    """
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    metadatas = [
        {"source": doc_name, "chunk_index": i}
        for i in range(len(chunks))
    ]
    Chroma.from_texts(
        texts=chunks,
        embedding=embeddings_model,
        metadatas=metadatas,
        persist_directory=CHROMA_DB_PATH,
        collection_name=COLLECTION_NAME
    )
    print(f"Stored {len(chunks)} chunks for '{doc_name}'.")


def ingest_pdf(pdf_path: str, doc_name: str) -> dict:
    """
    Master ingestion function: PDF → text → chunks → embeddings → ChromaDB.
    Checks for duplicates and re-ingests if the file already exists.
    """
    if document_already_ingested(doc_name):
        print(f"'{doc_name}' already ingested — replacing with fresh version.")
        delete_document(doc_name)

    print(f"\n--- Starting ingestion for: {doc_name} ---")
    text = extract_text_from_pdf(pdf_path)
    print(f"Extracted {len(text)} characters.")
    chunks = split_text_into_chunks(text)
    embed_and_store(chunks, doc_name)
    print(f"--- Ingestion complete for: {doc_name} ---\n")

    return {
        "document": doc_name,
        "total_characters": len(text),
        "total_chunks": len(chunks),
        "status": "ingested successfully"
    }
