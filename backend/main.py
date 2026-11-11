from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.document_parser import ingest_document
from core.semantic_engine import process_query, list_indexed_documents

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API de traitement et d'audit des documents de la supply chain.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question de conformité à poser au moteur.")
    document_context: str = Field(default="all", description="Filtre par document_id, ou 'all'.")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/api/v1/documents")
def get_documents():
    try:
        return {"status": "success", "documents": list_indexed_documents()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    try:
        status = await ingest_document(file)
        return {
            "status": "success",
            "filename": file.filename,
            "message": "Document indexé avec succès.",
            "document": status,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/audit/query")
def query_compliance(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="La requête ne peut être vide.")

    try:
        response = process_query(request.query.strip(), request.document_context.strip())
        return {"status": "success", "response": response}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur interne lors du traitement de la requête: {exc}")
