# module de construction de la chaine RAG complète
# Retriever (ChromaDB) -> Prompt -> LLM (Gemini) -> Réponse générée
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langdetect import detect

from src.vectorstore.chroma_store import load_vectorstore
from src.ingestion.embedder import get_embedding_model
from src.rag.multi_query import multi_query_retrieve
from src.rag.rate_limiter import rate_limiter
from src.rag.reranker import rerank_documents

load_dotenv()


RAG_PROMPT_TEMPLATE = """Tu es un assistant qui répond à des questions à partir du contexte fourni ci-dessous, extrait de documents scientifiques.

Règles :
- Base ta réponse uniquement sur les informations présentes dans le contexte ci-dessous.
- Si le contexte contient des informations partiellement pertinentes (ex. plusieurs chiffres liés à la question mais pas un chiffre unique et global), synthétise-les plutôt que de refuser de répondre.
- Ne réponds "Je ne trouve pas cette information dans les documents fournis" que si le contexte ne contient VRAIMENT aucune donnée en lien avec la question.
- Ne complète jamais avec des connaissances générales extérieures au contexte fourni.
- IMPORTANT : Rédige ta réponse ENTIÈREMENT en {answer_language}, quelle que soit la langue du contexte fourni.
- Cite les sources utilisées (nom du fichier) à la fin de ta réponse.

Contexte :
{context}

Question : {question}

Réponse (en {answer_language}) :"""


LANGUAGE_NAMES = {
    "en": "anglais",
    "fr": "français",
    "es": "espagnol",
    "de": "allemand",
}


def detect_question_language(question: str) -> str:
    """
    Détecte la langue de la question posée, pour forcer explicitement le LLM
    à répondre dans cette même langue (plus fiable que de compter sur le LLM
    pour déduire la langue depuis un prompt qui est lui-même en français).

    Returns:
        Le nom de la langue en français (ex. "anglais"), pour l'insérer
        directement et clairement dans le prompt.
    """
    try:
        lang_code = detect(question)
    except Exception:
        lang_code = "en"  # repli par défaut si la détection échoue (question trop courte, etc.)

    return LANGUAGE_NAMES.get(lang_code, "anglais")


def format_docs_for_prompt(docs) -> str:
    formatted_chunks = []
    for doc in docs:
        source = doc.metadata.get("source_file", "inconnu")
        page = doc.metadata.get("page_number", "?")
        formatted_chunks.append(
            f"[Source : {source}, page/section {page}]\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(formatted_chunks)


def build_rag_chain(k: int = 5):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY manquante. Vérifie que ton fichier .env contient "
            "bien GEMINI_API_KEY=ta_clé et qu'il est à la racine du projet."
        )

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    llm = genai.GenerativeModel(model_name)

    embedding_model = get_embedding_model()
    vectorstore = load_vectorstore(embedding_model)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    # On retourne aussi model_name, pour que ask() puisse le réutiliser
    # sans jamais le recoder en dur ailleurs dans le module.
    return llm, retriever, vectorstore, model_name


def ask(question: str, llm, retriever, vectorstore, model_name: str,
        show_sources: bool = True, use_multi_query: bool = True,
        use_reranking: bool = True, category_filter: str = None, k: int = 20):
    print(f"\n Question : {question}")
    print("-" * 60)

    # --- Retrieval, avec ou sans filtre par catégorie ---
    if category_filter:
        # Recherche directe filtrée par métadonnée : ignore le multi-query
        # dans ce cas pour rester simple (le filtre s'applique telle quelle
        # sur la question originale).
        docs = vectorstore.similarity_search(
            question, k=k, filter={"category": category_filter}
        )
    elif use_multi_query:
        docs = multi_query_retrieve(question, retriever, model_name, n_variants=3)
    else:
        docs = retriever.invoke(question)

    if use_reranking:
        docs = rerank_documents(question, docs, top_k=8)

    context = format_docs_for_prompt(docs)
    answer_language = detect_question_language(question)

    final_prompt = RAG_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
        answer_language=answer_language
    )

    rate_limiter.wait_if_needed()
    response = llm.generate_content(final_prompt, generation_config={"temperature": 0})
    answer = response.text

    print(f"\n Réponse :\n{answer}")

    if show_sources:
        sources = set(
            f"{doc.metadata.get('source_file')} (page/section {doc.metadata.get('page_number')})"
            for doc in docs
        )
        print(f"\n Sources consultées ({len(docs)} chunks) :")
        for source in sorted(sources):
            print(f"  - {source}")