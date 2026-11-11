from collections import defaultdict
from typing import Dict, List, Any

import chromadb
import requests
from sentence_transformers import SentenceTransformer

from core.config import settings

_client = chromadb.PersistentClient(path=str(settings.chroma_path))
_collection = _client.get_or_create_collection(name=settings.collection_name)
_embedder = SentenceTransformer(settings.embedding_model)


def index_document_chunks(document_id: str, original_filename: str, storage_path: str, chunks: List[Dict]) -> None:
    if not chunks:
        raise ValueError("Aucun chunk à indexer.")

    texts = [chunk["text"] for chunk in chunks]
    ids = [f"{document_id}:{chunk['chunk_id']}" for chunk in chunks]
    embeddings = _embedder.encode(texts, normalize_embeddings=True).tolist()
    metadatas = [
        {
            "document_id": document_id,
            "filename": original_filename,
            "storage_path": storage_path,
            "chunk_id": chunk["chunk_id"],
        }
        for chunk in chunks
    ]

    _collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)


def list_indexed_documents() -> List[Dict[str, Any]]:
    payload = _collection.get(include=["metadatas"])
    grouped = defaultdict(lambda: {"document_id": None, "filename": None, "storage_path": None, "chunks": 0})

    for metadata in payload.get("metadatas", []):
        if not metadata:
            continue
        doc_id = metadata.get("document_id")
        if not doc_id:
            continue
        record = grouped[doc_id]
        record["document_id"] = doc_id
        record["filename"] = metadata.get("filename")
        record["storage_path"] = metadata.get("storage_path")
        record["chunks"] += 1

    return list(grouped.values())


def process_query(query: str, document_context: str = "all") -> Dict[str, Any]:
    query_embedding = _embedder.encode([query], normalize_embeddings=True).tolist()[0]

    where = None
    if document_context and document_context.lower() != "all":
        where = {"document_id": document_context}

    result = _collection.query(
        query_embeddings=[query_embedding],
        n_results=settings.top_k_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    if not documents:
        return {
            "answer": "Aucun contenu pertinent n'a été trouvé dans les documents indexés.",
            "citations": [],
            "mode": "empty",
        }

    citations = []
    context_blocks = []
    for idx, text in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        citations.append({
            "rank": idx + 1,
            "document_id": metadata.get("document_id"),
            "filename": metadata.get("filename"),
            "chunk_id": metadata.get("chunk_id"),
            "score": distance,
            "excerpt": text[:500],
        })
        context_blocks.append(
            f"[Source {idx + 1}] file={metadata.get('filename')} chunk={metadata.get('chunk_id')}\n{text}"
        )

    llm_answer = generate_answer_with_ollama(query, "\n\n".join(context_blocks))
    if llm_answer:
        return {
            "answer": llm_answer,
            "citations": citations,
            "mode": "ollama",
        }

    fallback = build_extractive_answer(query, citations)
    return {
        "answer": fallback,
        "citations": citations,
        "mode": "extractive",
    }


def generate_answer_with_ollama(query: str, context: str) -> str | None:
    prompt = f"""You are a logistics compliance analyst.
Answer only from the provided context.
If the answer is not in the context, say clearly that the information is not found.
Respond in French.

Question:
{query}

Context:
{context}
"""

    try:
        response = requests.post(
            settings.ollama_url,
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        answer = (data.get("response") or "").strip()
        return answer or None
    except Exception:
        return None


def build_extractive_answer(query: str, citations: List[Dict[str, Any]]) -> str:
    intro = f"Résultats trouvés pour : '{query}'."
    bullets = []
    for citation in citations[:3]:
        bullets.append(
            f"- {citation['filename']} ({citation['chunk_id']}) : {citation['excerpt'][:280].replace(chr(10), ' ')}"
        )
    return intro + "\n" + "\n".join(bullets)
