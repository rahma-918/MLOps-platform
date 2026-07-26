

from prometheus_client import Counter, Histogram

# Compte le nombre de questions posées, ventilé par usage du reranking/multi-query
rag_questions_total = Counter(
    "rag_questions_total",
    "Nombre total de questions posées au RAG",
    ["use_reranking", "use_multi_query", "has_category_filter"]
)

# Compte les classifications effectuées, par catégorie retournée
classification_total = Counter(
    "classification_total",
    "Nombre total de documents classifiés",
    ["category"]
)

# Mesure le temps passé spécifiquement dans la génération LLM (pas la latence HTTP totale)
llm_generation_duration_seconds = Histogram(
    "llm_generation_duration_seconds",
    "Temps de génération de la réponse par le LLM (hors retrieval/reranking)"
)

# Compte les refus du RAG (questions hors corpus détectées)
rag_refusals_total = Counter(
    "rag_refusals_total",
    "Nombre de fois où le RAG a répondu qu'il ne trouvait pas l'information"
)