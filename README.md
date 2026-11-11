# Logistics Compliance System

A production-ready starter project for logistics document compliance audits using **FastAPI**, **ChromaDB**, **SentenceTransformers**, optional **OCR**, and a **Vanilla JS vintage terminal UI**.

## Features

- PDF upload and ingestion
- Text extraction from digital PDFs
- Optional OCR fallback for scanned PDFs
- Chunking and vector indexing with ChromaDB
- Semantic search over uploaded documents
- Optional local LLM answer generation via Ollama
- Vintage terminal frontend in Vanilla JS
- Dockerized backend + static frontend
- Persistent storage for uploaded files and vector index

## Project structure

```text
logistics-compliance-system/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── core/
│       ├── __init__.py
│       ├── config.py
│       ├── document_parser.py
│       └── semantic_engine.py
├── frontend/
│   ├── index.html
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── css/
│   │   └── vintage-terminal.css
│   └── js/
│       └── app.js
├── data/
│   ├── chroma/
│   └── documents/
├── .env.example
├── .gitignore
└── docker-compose.yml
```

## API

### Health
`GET /health`

### Upload a document
`POST /api/v1/documents/upload`

Multipart form-data:
- `file`: PDF file

### Query the audit engine
`POST /api/v1/audit/query`

```json
{
  "query": "What are the payment terms in the uploaded contract?",
  "document_context": "all"
}
```

### List indexed documents
`GET /api/v1/documents`

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
Open `frontend/index.html` directly in a browser for quick testing, or serve it with a static server.

## Docker

```bash
docker compose up --build
```

Frontend: `http://localhost:8080`
Backend: `http://localhost:8000/docs`

## Environment variables

Copy `.env.example` to `.env` if desired.

- `APP_NAME`
- `APP_VERSION`
- `CORS_ORIGINS`
- `DATA_DIR`
- `DOCUMENTS_DIR`
- `CHROMA_DIR`
- `COLLECTION_NAME`
- `EMBEDDING_MODEL`
- `TOP_K_RESULTS`
- `MIN_TEXT_LENGTH_FOR_DIRECT_PDF`
- `OLLAMA_URL`
- `OLLAMA_MODEL`
- `ENABLE_OCR`

## Notes

- If **Ollama** is available and the configured model is installed, answers are generated with contextual grounding from retrieved chunks.
- If Ollama is not running, the API falls back to an extractive answer using retrieved passages.
- OCR uses `pytesseract` and `tesseract-ocr` in Docker.

## Suggested next steps

- Add authentication
- Add per-document metadata filters
- Add citation highlighting in the frontend
- Add asynchronous background processing for large files
- Add test suite and CI/CD workflow
