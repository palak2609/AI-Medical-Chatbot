from dotenv import load_dotenv
import os

from src.prompt import system_prompt

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_groq import ChatGroq

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")

# Human-readable source names (matches ingest.py's SOURCE_NAMES)
_SOURCE_DISPLAY = {
    "medical_book.pdf":                 "Gale Encyclopedia of Medicine",
    "who_essential_medicines.pdf":      "WHO Essential Medicines List (2023)",
    "who_model_formulary.pdf":          "WHO Model Formulary",
    "harrison_manual.pdf":              "Harrison's Manual of Medicine",
    "oxford_handbook.pdf":              "Oxford Handbook of Clinical Medicine",
    "first_aid_usmle.pdf":              "First Aid for the USMLE",
    "davidson_principles.pdf":          "Davidson's Principles of Medicine",
}


def _pretty_source(raw: str) -> str:
    """Turn a file path stored in metadata into a readable citation."""
    name = os.path.basename(raw).lower()
    return _SOURCE_DISPLAY.get(name, os.path.splitext(os.path.basename(raw))[0].replace("_", " ").title())


# Embeddings (local, no API key)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Pinecone setup
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "medical-chatbot"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)

# Vector store + retriever
docsearch = PineconeVectorStore(index=index, embedding=embeddings)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 4})

# LLM
chatModel = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="llama-3.1-8b-instant")

# Prompt template (context injected manually so we can label sources)
_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

_chain = _prompt | chatModel | StrOutputParser()


def ask_rag(query: str) -> dict:
    """
    Run RAG query and return response + deduplicated source citations.
    Returns: {"response": str, "sources": list[str]}
    """
    docs = retriever.invoke(query)

    # Build labelled context so LLM sees where each passage comes from
    context_parts = []
    seen_sources = []
    for i, doc in enumerate(docs, 1):
        raw_src  = doc.metadata.get("source", "Medical Reference")
        page     = doc.metadata.get("page")
        label    = _pretty_source(raw_src)
        citation = label + (f", p.{page}" if page else "")

        context_parts.append(f"[Reference {i} — {citation}]\n{doc.page_content}")

        if label not in seen_sources:
            seen_sources.append(label)

    context = "\n\n".join(context_parts) if context_parts else "No specific reference retrieved."

    response = _chain.invoke({"context": context, "input": query})

    return {"response": response, "sources": seen_sources}
