# schemas pydantic definit la structure des requetes et réponses de l'API

from pydantic import BaseModel, Field
from typing import Optional


class AskRequest(BaseModel):
    """Corps de la requête envoyée par le client pour poser une question au RAG."""
    question: str = Field(..., min_length=3, description="La question à poser au RAG")
    use_multi_query: bool = Field(default=False, description="Active la reformulation multiple de la question")
    use_reranking: bool = Field(default=True, description="Active le reranking des chunks par cross-encoder")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the adverse events of COVID-19 vaccination in pregnant women?",
                "use_multi_query": False,
                "use_reranking": True
            }
        }


class SourceInfo(BaseModel):
    """Information sur une source citée dans la réponse."""
    source_file: str
    page_or_section: str


class AskResponse(BaseModel):
    """Réponse renvoyée par l'API après traitement d'une question."""
    question: str
    answer: str
    sources: list[SourceInfo]
    language_detected: str


class HealthResponse(BaseModel):
    """Réponse de l'endpoint de vérification de santé du service."""
    status: str
    llm_model: str