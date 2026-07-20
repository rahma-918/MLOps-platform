# API FASTAPI exposant le RAG
# le modèle d'embeddings et la connexion au LLM sont chargés une seule fois au démarrage du serveur

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from src.api.schemas import AskRequest, AskResponse, SourceInfo, HealthResponse
from src.rag.rag_chain import build_rag_chain, format_docs_for_prompt, RAG_PROMPT_TEMPLATE, detect_question_language
from src.rag.multi_query import multi_query_retrieve
from src.rag.reranker import rerank_documents
from src.rag.rate_limiter import rate_limiter

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
    llm, retriever, model_name = build_rag_chain(k=20)
    rag_resources["llm"] = llm
    rag_resources["retriever"] = retriever
    rag_resources["model_name"] = model_name
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


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Vérifie que l'API est démarrée et que le RAG est bien chargé."""
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé")
    return HealthResponse(status="ok", llm_model=rag_resources["model_name"])


@app.post("/ask", response_model=AskResponse, tags=["RAG"])
def ask_question(request: AskRequest):
    """
    Pose une question au RAG et retourne une réponse générée à partir du
    corpus de documents, avec les sources utilisées.
    """
    if "llm" not in rag_resources:
        raise HTTPException(status_code=503, detail="RAG non initialisé, réessayez dans quelques instants")

    llm = rag_resources["llm"]
    retriever = rag_resources["retriever"]
    model_name = rag_resources["model_name"]

    try:
        # 1. Retrieval
        if request.use_multi_query:
            docs = multi_query_retrieve(request.question, retriever, model_name, n_variants=3)
        else:
            docs = retriever.invoke(request.question)

        # 2. Reranking
        if request.use_reranking:
            docs = rerank_documents(request.question, docs, top_k=8)

        # 3. Construction du prompt
        context = format_docs_for_prompt(docs)
        answer_language = detect_question_language(request.question)
        final_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context, question=request.question, answer_language=answer_language
        )

        # 4. Génération
        rate_limiter.wait_if_needed()
        response = llm.generate_content(final_prompt, generation_config={"temperature": 0})
        answer = response.text

        # 5. Construction de la réponse structurée
        sources = [
            SourceInfo(
                source_file=doc.metadata.get("source_file", "inconnu"),
                page_or_section=str(doc.metadata.get("page_number", "?"))
            )
            for doc in docs
        ]
        # Déduplication des sources (plusieurs chunks peuvent venir du même fichier/page)
        unique_sources = list({(s.source_file, s.page_or_section): s for s in sources}.values())

        return AskResponse(
            question=request.question,
            answer=answer,
            sources=unique_sources,
            language_detected=answer_language,
        )

    except Exception as e:
        # Ne jamais laisser fuiter une erreur interne brute vers le client ;
        # on la logue côté serveur et on renvoie un message générique + code HTTP adapté.
        print(f"Erreur lors du traitement de la question : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors du traitement de la question")