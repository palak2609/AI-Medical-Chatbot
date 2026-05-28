"""
Medical Knowledge Ingestion Script
===================================
Adds PDF files from the data/ folder into Pinecone.

Usage:
    python ingest.py                 # ingests all NEW PDFs in data/
    python ingest.py --force         # re-ingests everything (overwrites)
    python ingest.py --list          # show what's already ingested

Free PDF sources to add (download and place in data/):
  - WHO Essential Medicines List:
      https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.01
  - WHO Disease Fact Sheets (search who.int/news-room/fact-sheets)
  - NCBI Bookshelf free textbooks:
      https://www.ncbi.nlm.nih.gov/books/
  - National Health Portal India (nhp.gov.in/disease)

Pinecone FREE TIER limits (serverless):
  - ~$5/month free credits
  - Each query costs ~$0.00001 → ~500,000 free queries/month
  - Each 1K vectors upsertion costs ~$0.05
  - Adding 10K vectors ≈ $0.50 total — well within free credits
"""

import os
import sys
import json
import time
import hashlib
import warnings

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# ─── Config ──────────────────────────────────────────────────────────────────
DATA_DIR      = "data"
STATE_FILE    = os.path.join(DATA_DIR, ".ingested.json")
INDEX_NAME    = "medical-chatbot"
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 100
BATCH_SIZE    = 100   # vectors per Pinecone upsert batch

# Files to always skip (already ingested, or not medical content)
SKIP_FILES = {"medical_history.json", ".ingested.json"}

# Human-readable names for citation display
SOURCE_NAMES = {
    "medical_book.pdf":                 "Gale Encyclopedia of Medicine",
    "who_essential_medicines.pdf":      "WHO Essential Medicines List (2023)",
    "who_model_formulary.pdf":          "WHO Model Formulary",
    "harrison_manual.pdf":              "Harrison's Manual of Medicine",
    "oxford_handbook.pdf":              "Oxford Handbook of Clinical Medicine",
    "first_aid_usmle.pdf":              "First Aid for the USMLE",
    "davidson_principles.pdf":          "Davidson's Principles of Medicine",
}


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read(65536))  # first 64KB is enough for identity check
    return h.hexdigest()


def _extract_chunks(pdf_path: str, filename: str) -> list[Document]:
    """Extract text from PDF and split into chunks with source metadata."""
    reader = PdfReader(pdf_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_docs = []
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        text = text.strip()
        if len(text) < 50:  # skip nearly empty pages
            continue

        chunks = splitter.split_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            if len(chunk.strip()) < 30:
                continue
            all_docs.append(Document(
                page_content=chunk,
                metadata={
                    "source":    filename,
                    "page":      page_num,
                    "chunk":     chunk_idx,
                },
            ))

    return all_docs


def _pretty_name(filename: str) -> str:
    key = filename.lower()
    return SOURCE_NAMES.get(key, os.path.splitext(filename)[0].replace("_", " ").title())


def ingest(force: bool = False):
    state = _load_state()

    # Find all PDFs in data/
    pdf_files = [
        f for f in os.listdir(DATA_DIR)
        if f.lower().endswith(".pdf") and f not in SKIP_FILES
    ]

    if not pdf_files:
        print(f"No PDF files found in {DATA_DIR}/")
        print("Download medical PDFs and place them in the data/ folder, then run again.")
        return

    # Filter to only new files unless --force
    to_ingest = []
    for f in pdf_files:
        path = os.path.join(DATA_DIR, f)
        fhash = _file_hash(path)
        if not force and state.get(f) == fhash:
            print(f"  [skip] Already ingested: {f}")
        else:
            to_ingest.append((f, path, fhash))

    if not to_ingest:
        print("\nAll PDFs are already ingested. Use --force to re-ingest.")
        return

    print(f"\nIngesting {len(to_ingest)} PDF(s) into Pinecone...")

    # Set up embedding model (runs locally, no API key needed)
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Connect to Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(INDEX_NAME)
    store = PineconeVectorStore(index=index, embedding=embeddings)

    for filename, path, fhash in to_ingest:
        print(f"\n  Processing: {filename}")
        print(f"  Display name: {_pretty_name(filename)}")

        chunks = _extract_chunks(path, filename)
        if not chunks:
            print(f"  [warn] No extractable text found. Skipping.")
            continue

        print(f"  Extracted {len(chunks)} chunks from PDF")

        # Upsert in batches to avoid rate limits
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Uploading batch {batch_num}/{total_batches}...", end="\r")
            store.add_documents(batch)
            time.sleep(0.5)  # gentle rate limiting

        print(f"  DONE: {len(chunks)} chunks uploaded for {filename}      ")

        # Mark as ingested
        state[filename] = fhash
        _save_state(state)

    print(f"\nIngestion complete.")

    # Show updated index stats
    stats = index.describe_index_stats()
    print(f"   Total vectors in index: {stats['total_vector_count']:,}")
    print(f"   Index usage: {stats.get('index_fullness', 0)*100:.1f}%")


def list_ingested():
    state = _load_state()
    if not state:
        print("No files tracked yet. Run ingest.py to add PDFs.")
        return
    print("Already ingested files:")
    for filename, fhash in state.items():
        pretty = _pretty_name(filename)
        print(f"  • {filename}  →  '{pretty}'")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--list" in args:
        list_ingested()
    elif "--force" in args:
        print("Force re-ingesting all PDFs...")
        ingest(force=True)
    else:
        ingest(force=False)
