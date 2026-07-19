"""RAG over downloaded PDFs: chunk -> embed (Ollama) -> SQLite vector store -> cited answers."""
import json
import logging
import math
import os
import sqlite3

import requests

logger = logging.getLogger(__name__)

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DB_PATH = "rag_index.db"


def chunk_text(text, chunk_size=1000, overlap=150):
    """Split text into overlapping chunks."""
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    step = chunk_size - overlap
    return [text[i:i + chunk_size] for i in range(0, len(text), step) if text[i:i + chunk_size]]


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class RagStore:
    """SQLite-backed vector store: (doc, chunk, embedding) rows."""

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, doc TEXT, chunk TEXT, embedding TEXT)"
        )
        self.conn.commit()

    def add_document(self, doc, chunks, embeddings):
        """Insert chunks for a document, replacing any previous version."""
        self.conn.execute("DELETE FROM chunks WHERE doc = ?", (doc,))
        self.conn.executemany(
            "INSERT INTO chunks (doc, chunk, embedding) VALUES (?, ?, ?)",
            [(doc, c, json.dumps(e)) for c, e in zip(chunks, embeddings)],
        )
        self.conn.commit()

    def has_document(self, doc):
        return self.conn.execute("SELECT 1 FROM chunks WHERE doc = ? LIMIT 1", (doc,)).fetchone() is not None

    def top_k(self, query_embedding, k=4):
        """Return the k most similar chunks as (doc, chunk, score), best first."""
        rows = self.conn.execute("SELECT doc, chunk, embedding FROM chunks").fetchall()
        scored = [(doc, chunk, cosine_similarity(query_embedding, json.loads(emb))) for doc, chunk, emb in rows]
        scored.sort(key=lambda t: t[2], reverse=True)
        return scored[:k]

    def close(self):
        self.conn.close()


def embed_texts(texts, model=DEFAULT_EMBED_MODEL):
    """Embed each text via Ollama. Raises on API failure."""
    embeddings = []
    for text in texts:
        response = requests.post(OLLAMA_EMBED_URL, json={"model": model, "prompt": text}, timeout=60)
        response.raise_for_status()
        embeddings.append(response.json()["embedding"])
    return embeddings


def index_pdfs(pdf_paths, db_path=DB_PATH, embed_model=DEFAULT_EMBED_MODEL, progress_callback=None):
    """Extract, chunk, embed and store each PDF. Returns total chunks indexed."""
    import asyncio
    from parse import process_pdf_files

    texts = asyncio.run(process_pdf_files(pdf_paths))
    store = RagStore(db_path)
    total = 0
    try:
        for i, (path, text) in enumerate(zip(pdf_paths, texts)):
            if progress_callback:
                progress_callback(i + 1, len(pdf_paths))
            if not text:
                logger.warning(f"No text extracted from {path}; skipping")
                continue
            chunks = chunk_text(text)
            embeddings = embed_texts(chunks, embed_model)
            store.add_document(os.path.basename(path), chunks, embeddings)
            total += len(chunks)
    finally:
        store.close()
    return total


def retrieve(question, db_path=DB_PATH, k=4, embed_model=DEFAULT_EMBED_MODEL):
    """Embed the question and return the k most relevant chunks."""
    query_embedding = embed_texts([question], embed_model)[0]
    store = RagStore(db_path)
    try:
        return store.top_k(query_embedding, k)
    finally:
        store.close()


def build_rag_prompt(question, retrieved, history=None):
    """Build the answer prompt from retrieved chunks and optional chat history."""
    context = "\n\n".join(f"[Source: {doc}]\n{chunk}" for doc, chunk, _ in retrieved)
    history_text = ""
    if history:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:]) + "\n\n"
    return f"""Answer the question using ONLY the sources below. Cite the source name in brackets (e.g. [report.pdf]) after each claim. If the answer is not in the sources, say so plainly.

Sources:
{context}

{history_text}Question: {question}

Answer:"""
