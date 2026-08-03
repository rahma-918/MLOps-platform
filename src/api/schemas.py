# schemas pydantic definit la structure des requetes et réponses de l'API
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # minutes


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    use_multi_query: bool = Field(default=False)
    use_reranking: bool = Field(default=True)
    category_filter: Optional[str] = Field(default=None)
    document_id_filter: Optional[str] = Field(
        default=None,
        description="Restreint la recherche à un document uploadé précis (retourné par /documents/upload)."
    )
    domain_filter: Optional[str] = Field(default=None, description="Force le domaine de classification")
    conversation_id: Optional[uuid.UUID] = Field(default=None)
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the adverse events of COVID-19 vaccination in pregnant women?",
                "use_multi_query": False,
                "use_reranking": True,
                "category_filter": "systematic_review_meta_analysis",
                "domain_filter": None,
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
    document_excerpt: str = Field(..., min_length=20)
    forced_domain: Optional[str] = Field(default=None, description="Force un domaine : medical, general, technical, legal")
    use_llm_domain: bool = Field(default=True, description="Utilise Gemini pour détecter le domaine (sinon heuristique rapide)")

    class Config:
        json_schema_extra = {
            "example": {
                "document_excerpt": "Systematic Review and Meta-Analysis...",
                "forced_domain": None,
                "use_llm_domain": True
            }
        }


class ClassifyResponse(BaseModel):
    category: str
    confidence: str
    justification: str
    domain: str = "general"  


class MessageResponse(BaseModel):
    """Représentation d'un message dans une conversation."""
    id: uuid.UUID
    role: str
    content: str
    sources: Optional[list] = None
    category_filter: Optional[str] = None
    document_id_filter: Optional[str] = None
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

class DocumentUploadResponse(BaseModel):
    """Réponse après upload et traitement d'un document."""
    document_id: str
    filename: str
    category: str
    confidence: str
    chunks_count: int


class UploadedDocumentInfo(BaseModel):
    """Résumé d'un document uploadé, pour lister ceux disponibles."""
    document_id: str
    filename: str
    category: str