import os
import uuid
import time
from datetime import timedelta
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
from fastapi import Request
from fastapi.responses import JSONResponse

from src.api.metrics import (
    rag_questions_total, classification_total,
    llm_generation_duration_seconds, rag_refusals_total
)
from src.api.schemas import (
    AskRequest, AskResponse, SourceInfo, HealthResponse,
    ClassifyRequest, ClassifyResponse, UserCreate, UserLogin,
    Token, UserResponse, ConversationResponse, ConversationSummary,
    DocumentUploadResponse
)
from src.core.security import (
    create_access_token, create_refresh_token, decode_token,
    get_current_user, get_optional_user
)
from src.rag.rag_chain import build_rag_chain, format_docs_for_prompt, RAG_PROMPT_TEMPLATE, detect_question_language
from src.rag.multi_query import multi_query_retrieve
from src.rag.reranker import rerank_documents
from src.rag.rate_limiter import rate_limiter
from src.classification.classifier import classify_document
from src.database.session import get_db
from src.database import crud
from src.database.models import User, Message
from src.ingestion.loader import load_document
from src.ingestion.chunker import convert_to_langchain_documents, chunk_documents

import tempfile
from pathlib import Path

SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
rag_resources = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Démarrage de l'API : chargement du RAG...")
    llm, retriever, vectorstore, model_name = build_rag_chain(k=20)
    rag_resources["llm"] = llm
    rag_resources["retriever"] = retriever
    rag_resources["model_name"] = model_name
    rag_resources["vectorstore"] = vectorstore
    print("RAG prêt.")
    yield
    print("Arrêt de l'API.")
    rag_resources.clear()


app = FastAPI(
    title="API RAG - Plateforme MLOps Santé Publique",
    version="1.1.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Garantit que même une erreur 500 non gérée renvoie les headers CORS,
    pour que le frontend puisse lire le vrai message d'erreur.
    """
    print(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"},
        headers={
            "Access-Control-Allow-Origin": allowed_origins[0] if allowed_origins else "*",
            "Access-Control-Allow-Credentials": "true",
        },
    )

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
print(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,   # ← IMPORTANT pour les cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])


# ============================================================
# AUTH
# ============================================================

@app.post("/auth/register", response_model=UserResponse, tags=["Auth"])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    user = crud.create_user(db, payload.email, payload.password, payload.full_name)
    return user


@app.post("/auth/login", response_model=Token, tags=["Auth"])
def login(response: Response, payload: UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,           # ← passe à True en production (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 3600,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30,
    }


@app.post("/auth/refresh", response_model=Token, tags=["Auth"])
def refresh(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    user = crud.get_user(db, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur invalide")

    new_access = create_access_token({"sub": str(user.id)})
    return {"access_token": new_access, "token_type": "bearer", "expires_in": 30}


@app.post("/auth/logout", tags=["Auth"])
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"detail": "Déconnecté"}


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ============================================================
# HEALTH
# ============================================================

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé")
    return HealthResponse(status="ok", llm_model=rag_resources["model_name"])


# ============================================================
# RAG / ASK
# ============================================================

@app.post("/ask", response_model=AskResponse, tags=["RAG"])
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),   # ← protégé
):
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé")

    llm = rag_resources["llm"]
    retriever = rag_resources["retriever"]
    model_name = rag_resources["model_name"]
    vectorstore = rag_resources["vectorstore"]

    # --- Conversation (appartient forcément à l'utilisateur) ---
    if request.conversation_id:
        conversation = crud.get_conversation(
            db, request.conversation_id, user_id=current_user.id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
    else:
        conversation = crud.create_conversation(
            db, user_id=current_user.id, title=request.question[:100]
        )

    # --- Récupération du document_id_filter depuis l'historique ---
    document_id_filter = request.document_id_filter
    if not document_id_filter and request.conversation_id:
        last_user_msg = db.query(Message).filter(
            Message.conversation_id == conversation.id,
            Message.role == "user"
        ).order_by(Message.created_at.desc()).first()
        if last_user_msg and last_user_msg.document_id_filter:
            document_id_filter = last_user_msg.document_id_filter

    rag_questions_total.labels(
        use_reranking=str(request.use_reranking),
        use_multi_query=str(request.use_multi_query),
        has_category_filter=str(request.category_filter is not None),
        has_document_filter=str(document_id_filter is not None)
    ).inc()

    try:
        if document_id_filter:
            docs = vectorstore.similarity_search(
                request.question, k=20, filter={"document_id": document_id_filter}
            )
        elif request.category_filter:
            docs = vectorstore.similarity_search(
                request.question, k=20, filter={"category": request.category_filter}
            )
        elif request.use_multi_query:
            docs = multi_query_retrieve(request.question, retriever, model_name, n_variants=3)
        else:
            docs = retriever.invoke(request.question)

        if request.use_reranking:
            docs = rerank_documents(request.question, docs, top_k=8)

        context = format_docs_for_prompt(docs)
        answer_language = detect_question_language(request.question)
        final_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context, question=request.question, answer_language=answer_language
        )

        rate_limiter.wait_if_needed()
        start_time = time.time()
        response = llm.generate_content(final_prompt, generation_config={"temperature": 0})
        llm_generation_duration_seconds.observe(time.time() - start_time)

        answer = response.text
        if "cannot find" in answer.lower() or "ne trouve pas" in answer.lower():
            rag_refusals_total.inc()

        sources = [
            SourceInfo(
                source_file=doc.metadata.get("source_file", "inconnu"),
                page_or_section=str(doc.metadata.get("page_number", "?"))
            )
            for doc in docs
        ]
        unique_sources = list({(s.source_file, s.page_or_section): s for s in sources}.values())

        crud.add_message(
            db, conversation.id, role="user", content=request.question,
            category_filter=request.category_filter,
            document_id_filter=document_id_filter,
        )
        crud.add_message(
            db, conversation.id, role="assistant", content=answer,
            sources=[s.model_dump() for s in unique_sources],
            category_filter=request.category_filter,
            document_id_filter=document_id_filter,
        )

        return AskResponse(
            question=request.question,
            answer=answer,
            sources=unique_sources,
            language_detected=answer_language,
            conversation_id=conversation.id,
        )

    except Exception as e:
        print(f"Erreur lors du traitement de la question : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")


# ============================================================
# CLASSIFICATION
# ============================================================

@app.post("/classify", response_model=ClassifyResponse, tags=["Classification"])
def classify_endpoint(request: ClassifyRequest):
    try:
        result = classify_document(
            request.document_excerpt,
            forced_domain=request.forced_domain,  
            use_llm_domain=request.use_llm_domain  
        )

        classification_total.labels(
            category=result["category"],
            domain=result["domain"] 
        ).inc()

        return ClassifyResponse(
            category=result["category"],
            confidence=result["confidence"],
            justification=result["justification"],
            domain=result["domain"],  # ← nouveau champ
        )
    except Exception as e:
        print(f"Erreur lors de la classification : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne")


# ============================================================
# CONVERSATIONS (protégées)
# ============================================================

@app.post("/conversations", response_model=ConversationSummary, tags=["Conversations"])
def create_new_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = crud.create_conversation(db, user_id=current_user.id)
    return conversation


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = crud.get_conversation(db, conversation_id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation


@app.get("/conversations", response_model=list[ConversationSummary], tags=["Conversations"])
def list_all_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.list_conversations(db, user_id=current_user.id)


@app.get("/categories", tags=["Classification"])
def get_available_categories(domain: str = None):
    """
    Retourne les catégories disponibles.
    Si 'domain' est fourni (medical, general, technical, legal), retourne la taxonomie de ce domaine.
    Sinon retourne la taxonomie médicale par défaut (rétrocompatibilité).
    """
    from src.classification.taxonomies import TAXONOMIES, TAXONOMY
    
    if domain and domain in TAXONOMIES:
        taxonomy = TAXONOMIES[domain]
    else:
        taxonomy = TAXONOMY  # medical par défaut
    
    return [{"value": key, "label": desc} for key, desc in taxonomy.items()]


# ============================================================
# DOCUMENT UPLOAD 
# ============================================================
@app.post("/documents/upload", response_model=DocumentUploadResponse, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """
    Reçoit un document (PDF, DOCX, image), l'extrait, le classifie, le découpe
    en chunks et l'ajoute à la base vectorielle avec un identifiant unique,
    permettant ensuite de restreindre une recherche RAG à ce seul document.
    """
    if "vectorstore" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé, réessayez dans quelques instants")

    extension = Path(file.filename).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : {extension}. Formats acceptés : {', '.join(SUPPORTED_UPLOAD_EXTENSIONS)}"
        )

    document_id = str(uuid.uuid4())

    # Sauvegarde temporaire du fichier (loader.py travaille sur un chemin disque,
    # pas directement sur un flux en mémoire)
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. Extraction (réutilise le pipeline d'ingestion existant)
        pages = load_document(tmp_path, ocr_lang="fra")
        for page in pages:
            page.metadata["source_file"] = file.filename  # nom d'origine, pas le nom temporaire

        # 2. Classification (à partir des 2-3 premiers segments)
        sorted_pages = sorted(pages, key=lambda p: p.metadata.get("page_number", 0))
        excerpt = "\n".join(p.text for p in sorted_pages[:3])
        classification = classify_document(excerpt)

        # 3. Chunking
        documents = convert_to_langchain_documents(pages)
        chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

        # 4. Enrichissement des métadonnées : catégorie + identifiant unique
        # de document, pour permettre plus tard de filtrer /ask sur CE document précis
        for chunk in chunks:
            chunk.metadata["category"] = classification["category"]
            chunk.metadata["document_id"] = document_id

        # 5. Stockage dans la base vectorielle existante (ajout, pas de reset)
        vectorstore = rag_resources["vectorstore"]
        vectorstore.add_documents(chunks)

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            category=classification["category"],
            confidence=classification["confidence"],
            chunks_count=len(chunks),
        )

    except Exception as e:
        print(f"Erreur lors de l'upload du document : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du traitement du document")

    finally:
        Path(tmp_path).unlink(missing_ok=True)