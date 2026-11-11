from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Logistics Document Compliance API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    cors_origins_raw: str = Field(
        default="http://localhost:8080,http://127.0.0.1:8080,http://localhost:5500",
        alias="CORS_ORIGINS",
    )

    data_dir: str = Field(default="../data", alias="DATA_DIR")
    documents_dir: str = Field(default="../data/documents", alias="DOCUMENTS_DIR")
    chroma_dir: str = Field(default="../data/chroma", alias="CHROMA_DIR")
    collection_name: str = Field(default="logistics_documents", alias="COLLECTION_NAME")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    top_k_results: int = Field(default=5, alias="TOP_K_RESULTS")
    min_text_length_for_direct_pdf: int = Field(default=500, alias="MIN_TEXT_LENGTH_FOR_DIRECT_PDF")

    ollama_url: str = Field(default="http://localhost:11434/api/generate", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama3.1", alias="OLLAMA_MODEL")
    enable_ocr: bool = Field(default=True, alias="ENABLE_OCR")

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def documents_path(self) -> Path:
        return Path(self.documents_dir).resolve()

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir).resolve()


settings = Settings()
settings.documents_path.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)
