# src/rag/multi_query.py
import google.generativeai as genai
from src.rag.rate_limiter import rate_limiter

QUERY_GENERATION_PROMPT = """Tu es un assistant qui aide à améliorer la recherche documentaire.
Génère {n} reformulations différentes de la question suivante, en changeant le vocabulaire,
l'angle ou le niveau de détail, tout en gardant le même sens.
Réponds uniquement avec les {n} reformulations, une par ligne, sans numérotation ni commentaire.

Question originale : {question}
"""


def generate_query_variants(question: str, llm_model_name: str, n: int = 3) -> list[str]:
    model = genai.GenerativeModel(llm_model_name)
    prompt = QUERY_GENERATION_PROMPT.format(n=n, question=question)

    rate_limiter.wait_if_needed()
    response = model.generate_content(prompt, generation_config={"temperature": 0.7})
    variants = [line.strip() for line in response.text.split("\n") if line.strip()]

    return variants[:n]


def multi_query_retrieve(question: str, retriever, llm_model_name: str, n_variants: int = 3):
    all_queries = [question] + generate_query_variants(question, llm_model_name, n_variants)

    print(f"  Requêtes utilisées pour la recherche :")
    for q in all_queries:
        print(f"    - {q}")

    seen_content = set()
    unique_docs = []

    for query in all_queries:
        docs = retriever.invoke(query)
        for doc in docs:
            if doc.page_content not in seen_content:
                seen_content.add(doc.page_content)
                unique_docs.append(doc)

    return unique_docs