import re
import shutil
import uuid
from pathlib import Path
from typing import List, Dict

import fitz
import pytesseract
from PIL import Image
from fastapi import UploadFile

from core.config import settings
from core.semantic_engine import index_document_chunks


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename).strip("._")
    return cleaned or f"document_{uuid.uuid4().hex}.pdf"


async def ingest_document(file: UploadFile) -> Dict:
    filename = sanitize_filename(file.filename or "document.pdf")
    document_id = uuid.uuid4().hex
    storage_path = settings.documents_path / f"{document_id}_{filename}"

    content = await file.read()
    if not content:
        raise ValueError("Le fichier est vide.")

    storage_path.write_bytes(content)
    return ingest_stored_pdf(storage_path=storage_path, original_filename=filename, document_id=document_id)


def load_demo_documents() -> List[Dict]:
    demo_files = sorted(settings.demo_path.glob('*.pdf'))
    if not demo_files:
        raise ValueError("Aucun document de démonstration n'a été trouvé.")

    loaded = []
    for demo_file in demo_files:
        original_filename = sanitize_filename(demo_file.name)
        document_id = f"demo-{demo_file.stem.lower().replace(' ', '-') }"
        storage_path = settings.documents_path / f"{document_id}_{original_filename}"
        shutil.copyfile(demo_file, storage_path)
        loaded.append(
            ingest_stored_pdf(
                storage_path=storage_path,
                original_filename=original_filename,
                document_id=document_id,
            )
        )
    return loaded


def ingest_stored_pdf(storage_path: Path, original_filename: str, document_id: str) -> Dict:
    extracted_text = extract_text_from_pdf(storage_path)
    if len(extracted_text.strip()) < 50:
        raise ValueError("Impossible d'extraire suffisamment de texte du PDF.")

    chunks = chunk_text(extracted_text, CHUNK_SIZE, CHUNK_OVERLAP)
    index_document_chunks(
        document_id=document_id,
        original_filename=original_filename,
        storage_path=str(storage_path),
        chunks=chunks,
    )

    return {
        "document_id": document_id,
        "filename": original_filename,
        "stored_at": str(storage_path),
        "chunks_indexed": len(chunks),
        "characters_extracted": len(extracted_text),
    }


def extract_text_from_pdf(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    page_texts: List[str] = []

    for page in doc:
        text = page.get_text("text") or ""
        page_texts.append(text)

    combined = "\n".join(page_texts).strip()
    if len(combined) >= settings.min_text_length_for_direct_pdf or not settings.enable_ocr:
        doc.close()
        return normalize_text(combined)

    ocr_texts: List[str] = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_texts.append(pytesseract.image_to_string(image, lang="eng+fra"))

    doc.close()
    merged = combined + "\n" + "\n".join(ocr_texts)
    return normalize_text(merged)


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[Dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size doit être supérieur à overlap")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[Dict] = []
    current = ""
    idx = 0

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append({"chunk_id": f"chunk-{idx}", "text": current})
            idx += 1

        if len(paragraph) <= chunk_size:
            current = paragraph
        else:
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                segment = paragraph[start:end].strip()
                if segment:
                    chunks.append({"chunk_id": f"chunk-{idx}", "text": segment})
                    idx += 1
                start += chunk_size - overlap
            current = ""

    if current:
        chunks.append({"chunk_id": f"chunk-{idx}", "text": current})

    return chunks
