"""
Fallback implementation without ChromaDB/sentence-transformers.
Uses simple keyword matching and text extraction for demo purposes.
This version works on Windows without PyTorch dependencies.
"""

import re
from typing import Dict, List, Any
from collections import defaultdict


class SimpleVectorStore:
    """Simple in-memory store with basic similarity search."""
    
    def __init__(self):
        self.documents = {}  # document_id -> {filename, chunks}
        
    def add_document(self, doc_id: str, filename: str, text_chunks: List[str]):
        if not text_chunks:
            raise ValueError("No chunks to index.")
            
        self.documents[doc_id] = {
            "document_id": doc_id,
            "filename": filename,
            "chunks": text_chunks
        }
        
    def search(self, query: str, document_context: str = "all", top_k: int = 5) -> Dict[str, Any]:
        if not self.documents:
            return {
                "answer": "Aucun contenu pertinent n'a été trouvé dans les documents indexés.",
                "citations": [],
                "mode": "empty"
            }
        
        # Simple keyword-based matching (replace with vector search when available)
        query_terms = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())[:10]
        
        scored_chunks = []
        for doc_id, data in self.documents.items():
            if document_context and document_context != "all":
                if data["document_id"] != document_context:
                    continue
                    
            # Score chunks based on keyword matches
            for chunk_idx, text in enumerate(data["chunks"]):
                text_lower = text.lower()
                
                # Count term matches
                match_count = sum(1 for term in query_terms if term in text_lower)
                
                # Boost score based on multiple matches
                score = len(query_terms) / (len(text_lower) + 1) * (match_count + 0.5)
                
                scored_chunks.append({
                    "chunk_id": f"{doc_id}:chunk-{chunk_idx}",
                    "text": text[:500],
                    "score": score,
                    "filename": data["filename"],
                    "document_id": doc_id
                })
        
        if not scored_chunks:
            return {
                "answer": f"Aucun résultat trouvé pour : '{query}'.",
                "citations": [],
                "mode": "empty"
            }
            
        # Sort by score and take top_k
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        results = scored_chunks[:top_k]
        
        # Build answer from retrieved chunks
        excerpts = [c["text"] for c in results]
        intro = f"Résultats trouvés pour : '{query}'."
        
        bullets = []
        for i, citation in enumerate(results[:3], 1):
            excerpt_preview = citation["text"][:280].replace(chr(10), ' ')
            bullets.append(f"- {citation['filename']} ({citation['chunk_id']}) : {excerpt_preview}")
            
        answer = intro + "\n" + "\n".join(bullets) if bullets else "Aucun résultat détaillé disponible."
        
        return {
            "answer": answer,
            "citations": [
                {
                    "rank": i+1,
                    "document_id": c["document_id"],
                    "filename": c["filename"],
                    "chunk_id": c["chunk_id"],
                    "score": round(c["score"], 4),
                    "excerpt": c["text"][:500]
                } for i, c in enumerate(results)
            ],
            "mode": "simple_search"
        }


# Global store instance
_store = SimpleVectorStore()


def index_document_chunks(document_id: str, original_filename: str, storage_path: str, chunks: List[Dict]) -> None:
    if not chunks:
        raise ValueError("Aucun chunk à indexer.")
        
    texts = [chunk["text"] for chunk in chunks]
    _store.add_document(
        document_id=document_id,
        filename=original_filename,
        text_chunks=texts
    )


def list_indexed_documents() -> List[Dict[str, Any]]:
    result = []
    for doc_data in _store.documents.values():
        record = {
            "document_id": doc_data["document_id"],
            "filename": doc_data["filename"],
            "storage_path": "",  # Not tracked in simple version
            "chunks": len(doc_data.get("chunks", []))
        }
        result.append(record)
    return sorted(result, key=lambda x: x["filename"] or "")


def process_query(query: str, document_context: str = "all") -> Dict[str, Any]:
    try:
        response = _store.search(
            query=query.strip(),
            document_context=document_context.strip() if document_context else "all",
            top_k=5
        )
        return {"status": "success", "response": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {exc}")


def generate_answer_with_ollama(query: str, context: str) -> str | None:
    """Placeholder - returns None to use extractive fallback."""
    return None


def build_extractive_answer(query: str, citations: List[Dict[str, Any]]) -> str:
    intro = f"Résultats trouvés pour : '{query}'."
    bullets = []
    for citation in citations[:3]:
        excerpt_preview = citation.get('excerpt', 'Aucun extrait')[:280].replace(chr(10), ' ')
        bullets.append(f"- {citation['filename']} ({citation['chunk_id']}) : {excerpt_preview}")
    return intro + "\n" + "\n".join(bullets) if bullets else "Aucune réponse disponible."


def load_demo_documents() -> List[Dict]:
    from core.document_parser import ingest_stored_pdf, sanitize_filename
    
    demo_files = sorted(Path(__file__).parent.parent / 'demo' / '*.pdf').glob('*.pdf')
    if not demo_files:
        raise ValueError("Aucun document de démonstration n'a été trouvé.")

    loaded = []
    for demo_file in demo_files:
        original_filename = sanitize_filename(demo_file.name)
        document_id = f"demo-{demo_file.stem.lower().replace(' ', '-') }"
        
        # Copy to storage and ingest
        import shutil
        from pathlib import Path as P
        storage_path = P(__file__).parent.parent / 'data' / 'documents' / f"{document_id}_{original_filename}"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(demo_file, storage_path)
        
        loaded.append(ingest_stored_pdf(storage_path=storage_path, original_filename=original_filename, document_id=document_id))
    
    return loaded

