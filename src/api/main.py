# API FASTAPI exposant le RAG
# le modèle d'embeddings et la connexion au LLM sont chargés une seule fois au démarrage du serveur

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import time
from src.api.metrics import (
    rag_questions_total, classification_total,
    llm_generation_duration_seconds, rag_refusals_total
)
from src.api.schemas import AskRequest, AskResponse, SourceInfo, HealthResponse, ClassifyRequest, ClassifyResponse
from src.rag.rag_chain import build_rag_chain, format_docs_for_prompt, RAG_PROMPT_TEMPLATE, detect_question_language
from src.rag.multi_query import multi_query_retrieve
from src.rag.reranker import rerank_documents
from src.rag.rate_limiter import rate_limiter
from src.classification.classifier import classify_document
from sqlalchemy.orm import Session
from fastapi import Depends
from src.database.session import get_db
from src.database import crud
from src.api.schemas import ConversationResponse, ConversationSummary

# Dictionnaire partagé qui contiendra les ressources chargées une seule fois
# au démarrage (llm, retriever, model_name), accessible à toutes les requêtes.
rag_resources = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Bloc de démarrage/arrêt de l'application. Le code avant le `yield`
    s'exécute une seule fois au lancement du serveur (ici : chargement du
    modèle d'embeddings, connexion à ChromaDB, initialisation de Gemini).
    Le code après `yield` s'exécuterait à l'arrêt du serveur (rien à faire
    ici pour l'instant).
    """
    print("Démarrage de l'API : chargement du RAG (embeddings, ChromaDB, Gemini)...")
    llm, retriever, vectorstore, model_name = build_rag_chain(k=20)
    rag_resources["llm"] = llm
    rag_resources["retriever"] = retriever
    rag_resources["model_name"] = model_name
    rag_resources["vectorstore"] = vectorstore
    print("RAG prêt. API disponible.")

    yield  # sépare entre démarrage et arret de serveur

    print("Arrêt de l'API.")
    rag_resources.clear()


app = FastAPI(
    title="API RAG - Plateforme MLOps Santé Publique",
    description="API exposant un système RAG (Retrieval-Augmented Generation) sur un corpus de documents scientifiques de santé publique.",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrumentation automatique : ajoute un endpoint /metrics qui expose
# des métriques standard (latence par endpoint, nombre de requêtes,
# codes de statut HTTP...) sans avoir à les coder manuellement.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Vérifie que l'API est démarrée et que le RAG est bien chargé."""
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé")
    return HealthResponse(status="ok", llm_model=rag_resources["model_name"])


@app.post("/ask", response_model=AskResponse, tags=["RAG"])
def ask_question(request: AskRequest, db: Session = Depends(get_db)):
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé, réessayez dans quelques instants")

    llm = rag_resources["llm"]
    retriever = rag_resources["retriever"]
    model_name = rag_resources["model_name"]
    vectorstore = rag_resources["vectorstore"]

    # --- Gestion de la conversation ---
    if request.conversation_id:
        conversation = crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
    else:
        # Crée une nouvelle conversation, titrée avec le début de la question
        conversation = crud.create_conversation(db, title=request.question[:100])

    rag_questions_total.labels(
        use_reranking=str(request.use_reranking),
        use_multi_query=str(request.use_multi_query),
        has_category_filter=str(request.category_filter is not None)
    ).inc()

    try:
        if request.category_filter:
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

        # --- Sauvegarde des 2 messages (question + réponse) ---
        crud.add_message(db, conversation.id, role="user", content=request.question,
                          category_filter=request.category_filter)
        crud.add_message(db, conversation.id, role="assistant", content=answer,
                          sources=[s.model_dump() for s in unique_sources])

        return AskResponse(
            question=request.question,
            answer=answer,
            sources=unique_sources,
            language_detected=answer_language,
            conversation_id=conversation.id,
        )

    except Exception as e:
        print(f"Erreur lors du traitement de la question : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors du traitement de la question")

@app.post("/classify", response_model=ClassifyResponse, tags=["Classification"])
def classify_endpoint(request: ClassifyRequest):
    try:
        result = classify_document(request.document_excerpt)

        # Incrémente le compteur par catégorie retournée
        classification_total.labels(category=result["category"]).inc()

        return ClassifyResponse(
            category=result["category"],
            confidence=result["confidence"],
            justification=result["justification"],
        )
    except Exception as e:
        print(f"Erreur lors de la classification : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la classification")

@app.post("/conversations", response_model=ConversationSummary, tags=["Conversations"])
def create_new_conversation(db: Session = Depends(get_db)):
    """Crée une nouvelle conversation vide, à laquelle rattacher des messages ensuite."""
    conversation = crud.create_conversation(db)
    return conversation


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Conversations"])
def get_conversation_history(conversation_id: str, db: Session = Depends(get_db)):
    """Récupère une conversation complète avec tout son historique de messages."""
    conversation = crud.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation


@app.get("/conversations", response_model=list[ConversationSummary], tags=["Conversations"])
def list_all_conversations(db: Session = Depends(get_db)):
    """Liste toutes les conversations existantes (sans authentification pour l'instant)."""
    return crud.list_conversations(db)