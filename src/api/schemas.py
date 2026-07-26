# schemas pydantic definit la structure des requetes et réponses de l'API
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, description="La question à poser au RAG")
    use_multi_query: bool = Field(default=False, description="Active la reformulation multiple de la question")
    use_reranking: bool = Field(default=True, description="Active le reranking des chunks par cross-encoder")
    category_filter: Optional[str] = Field(
        default=None,
        description="Restreint la recherche aux documents de cette catégorie (ex. 'systematic_review_meta_analysis'). Si non fourni, cherche dans tout le corpus."
    )
    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="ID de conversation existante pour poursuivre l'historique. Si non fourni, une nouvelle conversation est créée."
    )
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the adverse events of COVID-19 vaccination in pregnant women?",
                "use_multi_query": False,
                "use_reranking": True,
                "category_filter": "systematic_review_meta_analysis",
                "conversation_id": None
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
    conversation_id: uuid.UUID


class HealthResponse(BaseModel):
    """Réponse de l'endpoint de vérification de santé du service."""
    status: str
    llm_model: str

class ClassifyRequest(BaseModel):
    """Corps de la requête pour classifier un extrait de document."""
    document_excerpt: str = Field(..., min_length=20, description="Extrait représentatif du document (titre, abstract, début d'introduction)")

    class Config:
        json_schema_extra = {
            "example": {
                "document_excerpt": "Systematic Review and Meta-Analysis: Safety of COVID-19 Vaccines Among Pregnant Women..."
            }
        }


class ClassifyResponse(BaseModel):
    """Réponse renvoyée par l'API après classification d'un document."""
    category: str
    confidence: str
    justification: str


class MessageResponse(BaseModel):
    """Représentation d'un message dans une conversation."""
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[list] = None
    category_filter: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True  # permet de construire ce schéma depuis un objet SQLAlchemy


class ConversationResponse(BaseModel):
    """Représentation d'une conversation avec tous ses messages."""
    id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Version allégée d'une conversation, pour lister l'historique sans tous les messages."""
    id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
