# src/rag/reranker.py
"""
Reranking des chunks retrouvés par le retriever, via un modèle cross-encoder.
Le retriever fait un premier tri rapide et large (k élevé), le cross-encoder
affine ensuite le classement en évaluant chaque paire (question, chunk)
précisément, avant de ne garder que les meilleurs.
"""

from sentence_transformers import CrossEncoder

_reranker_model = None


def get_reranker():
    global _reranker_model
    if _reranker_model is None:
        # Modèle multilingue (entraîné sur mMARCO, incluant le français),
        # cohérent avec le corpus mixte anglais/français du projet.
        # ms-marco-MiniLM-L-6-v2 (utilisé initialement) est anglais uniquement
        # et donnerait un reranking peu fiable sur les questions en français.
        _reranker_model = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    return _reranker_model


def rerank_documents(question: str, docs: list, top_k: int = 8):
    """
    Reclasse les documents retrouvés selon leur pertinence réelle par rapport
    à la question, via un cross-encoder, et ne garde que les top_k meilleurs.

    Args:
        question: la question posée
        docs: liste de Document retrouvés par le retriever (idéalement un pool
              large, ex. k=20-30, pour laisser au cross-encoder de la matière
              à trier -- le reranking ne peut qu'ordonner ce qu'il reçoit, pas
              retrouver un chunk absent du pool initial)
        top_k: nombre de documents à garder après reclassement

    Returns:
        Liste de Document, triée par pertinence décroissante, tronquée à top_k.
    """
    if not docs:
        return docs

    reranker = get_reranker()

    pairs = [(question, doc.page_content) for doc in docs]
    scores = reranker.predict(pairs)

    scored_docs = list(zip(docs, scores))
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, score in scored_docs[:top_k]]