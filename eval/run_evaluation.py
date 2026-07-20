"""
Exécute le RAG sur le jeu de données de référence (golden_dataset) et calcule
des métriques automatiques. Chaque exécution est trackée comme un run MLflow,
avec les paramètres de configuration et les métriques obtenues.
"""

import csv
from datetime import datetime
import mlflow
from langdetect import detect

from src.rag.rag_chain import build_rag_chain
from eval.golden_dataset import GOLDEN_DATASET

REFUSAL_MARKERS = [
    "cannot find", "can not find", "do not find", "don't find",
    "does not contain", "doesn't contain",
    "not provided in", "no information", "not available in",
    "je ne trouve pas", "ne contient pas", "n'est pas fourni",
    "n'ai pas trouvé", "aucune information",
]

mlflow.set_tracking_uri("sqlite:///mlflow.db")
# Nom de l'experiment MLflow : regroupe tous les runs d'évaluation du RAG
mlflow.set_experiment("RAG_evaluation")


def contains_fragment(text: str, fragment: str) -> bool:
    if fragment is None:
        return None
    return fragment.lower() in text.lower()


def contains_refusal(text: str) -> bool:
    text_lower = text.lower()
    return any(marker in text_lower for marker in REFUSAL_MARKERS)


def check_language_match(question: str, answer: str) -> bool:
    try:
        return detect(question) == detect(answer)
    except Exception:
        return None


def run_evaluation(use_multi_query: bool = False, use_reranking: bool = True, k: int = 20, rerank_top_k: int = 8):
    llm, retriever, model_name = build_rag_chain(k=k)

    from src.rag.rag_chain import format_docs_for_prompt, RAG_PROMPT_TEMPLATE, detect_question_language
    from src.rag.multi_query import multi_query_retrieve
    from src.rag.rate_limiter import rate_limiter
    from src.rag.reranker import rerank_documents

    results = []

    for item in GOLDEN_DATASET:
        print(f"\n[{item['id']}] {item['question']}")

        if use_multi_query:
            docs = multi_query_retrieve(item["question"], retriever, model_name, n_variants=3)
        else:
            docs = retriever.invoke(item["question"])

        if use_reranking:
            docs = rerank_documents(item["question"], docs, top_k=rerank_top_k)

        context = format_docs_for_prompt(docs)
        answer_language = detect_question_language(item["question"])
        final_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context, question=item["question"], answer_language=answer_language
        )

        rate_limiter.wait_if_needed()
        response = llm.generate_content(final_prompt, generation_config={"temperature": 0})
        answer = response.text

        sources_used = [doc.metadata.get("source_file") for doc in docs]

        fragment_found = contains_fragment(answer, item["expected_fragment"])
        source_found = (
            item["expected_source"] in sources_used
            if item["expected_source"] else None
        )
        refusal_detected = contains_refusal(answer)
        language_ok = check_language_match(item["question"], answer)

        if item["category"] == "refusal":
            success = refusal_detected
            hallucination = not refusal_detected
        else:
            success = bool(fragment_found)
            hallucination = False

        results.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "success": success,
            "hallucination": hallucination,
            "fragment_found": fragment_found,
            "source_found": source_found,
            "language_ok": language_ok,
            "answer_full": answer,
            "answer_preview": answer[:150].replace("\n", " "),
        })

        print(f"  -> succès: {success} | hallucination: {hallucination} | langue OK: {language_ok}")

    return results, model_name


def compute_summary_metrics(results: list[dict]) -> dict:
    """
    Calcule les métriques agrégées à partir des résultats détaillés, sous
    forme de dictionnaire plat (nom_metrique -> valeur), directement
    exploitable par mlflow.log_metrics().
    """
    metrics = {}

    categories = set(r["category"] for r in results)
    for category in categories:
        subset = [r for r in results if r["category"] == category]
        rate = sum(r["success"] for r in subset) / len(subset) * 100
        metrics[f"success_rate_{category}"] = rate

    # Métriques globales, toutes catégories confondues
    metrics["overall_success_rate"] = sum(r["success"] for r in results) / len(results) * 100
    metrics["hallucination_rate"] = sum(r["hallucination"] for r in results) / len(results) * 100

    lang_checked = [r for r in results if r["language_ok"] is not None]
    if lang_checked:
        metrics["language_consistency_rate"] = sum(r["language_ok"] for r in lang_checked) / len(lang_checked) * 100

    return metrics


def print_summary(metrics: dict):
    print("\n" + "=" * 70)
    print("RÉSUMÉ DE L'ÉVALUATION")
    print("=" * 70)
    for name, value in metrics.items():
        print(f"{name} : {value:.0f}%")


def save_results_to_csv(results: list[dict], filename: str = None):
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval/results_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nRésultats détaillés sauvegardés dans : {filename}")
    return filename


if __name__ == "__main__":
    # Paramètres de configuration de cette évaluation -- ce sont eux qui
    # seront trackés par MLflow, pour pouvoir comparer différentes configs
    # entre elles plus tard dans l'interface MLflow.
    config = {
        "k": 20,
        "rerank_top_k": 8,
        "use_multi_query": False,
        "use_reranking": True,
        "chunk_size": 500,       # doit rester cohérent avec ta config d'ingestion actuelle
        "chunk_overlap": 50,
        "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
    }

    with mlflow.start_run(run_name="reranking_k20to8_v2"):
        # 1. On enregistre tous les paramètres de configuration du run
        mlflow.log_params(config)

        # 2. On exécute l'évaluation
        results, model_name = run_evaluation(
            use_multi_query=config["use_multi_query"],
            use_reranking=config["use_reranking"],
            k=config["k"],
            rerank_top_k=config["rerank_top_k"],
        )
        mlflow.log_param("llm_model", model_name)

        # 3. On calcule et enregistre les métriques
        metrics = compute_summary_metrics(results)
        mlflow.log_metrics(metrics)
        print_summary(metrics)

        # 4. On sauvegarde le CSV détaillé et on l'attache au run comme artefact
        csv_path = save_results_to_csv(results)
        mlflow.log_artifact(csv_path)

        print(f"\n Run MLflow enregistré. Lance 'mlflow ui' pour visualiser les résultats.")