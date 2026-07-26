#Module de classification zero-shot de documents scientifiques, via l'API Gemini

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from src.rag.rate_limiter import rate_limiter

load_dotenv()

# Taxonomie des catégories possibles, avec leur description -- cette
# description est injectée dans le prompt pour aider le LLM à bien
# distinguer les catégories proches (ex. revue systématique vs méta-analyse).
TAXONOMY = {
    "systematic_review_meta_analysis": "Revue systématique incluant une méta-analyse : synthèse de plusieurs études avec calcul statistique groupé (odds ratio, risque relatif, forest plot...)",
    "systematic_review": "Revue systématique sans méta-analyse formelle : synthèse qualitative structurée de plusieurs études, sans calcul statistique combiné",
    "narrative_review": "Revue narrative ou de littérature non systématique : synthèse générale d'un sujet sans méthodologie de recherche systématique documentée (pas de PRISMA, pas de critères d'inclusion/exclusion formels)",
    "randomized_controlled_trial": "Essai clinique randomisé contrôlé (RCT) : intervention testée avec répartition aléatoire des participants entre groupes",
    "cohort_study": "Étude de cohorte : suivi d'un groupe de participants dans le temps (prospective ou rétrospective) pour observer la survenue d'événements",
    "cross_sectional_study": "Étude transversale : collecte de données à un instant T, sans suivi dans le temps (ex. enquête, sondage, prévalence)",
    "case_control_study": "Étude cas-témoins : comparaison entre un groupe ayant l'issue étudiée et un groupe n'ayant pas cette issue",
    "case_report": "Étude de cas ou série de cas cliniques individuels, sans groupe de comparaison",
    "clinical_guideline": "Recommandation clinique officielle ou guideline émise par une société savante, un ministère, ou une organisation de santé",
    "editorial_commentary": "Éditorial, commentaire, lettre à l'éditeur, ou opinion d'expert, sans données originales de recherche",
    "technical_report": "Rapport technique ou institutionnel (ex. rapport de surveillance épidémiologique, rapport gouvernemental)",
    "other": "Tout autre type de document ne correspondant à aucune des catégories ci-dessus",
}


CLASSIFICATION_PROMPT_TEMPLATE = """You are an assistant specialized in classifying medical scientific documents.

Here are the possible categories, with their definitions:
{categories_description}

Here is an excerpt from the document to classify (title, abstract, and beginning of introduction/methods):

{document_excerpt}

Respond ONLY in the following JSON format, with no text before or after:
{{
  "category": "<one of the categories exactly as written above>",
  "confidence": "<high|medium|low>",
  "justification": "<one short sentence explaining your choice>"
}}
"""


def build_categories_description() -> str:
    """Formate la taxonomie en texte lisible pour le prompt."""
    return "\n".join(f"- {key} : {desc}" for key, desc in TAXONOMY.items())


def classify_document(document_excerpt: str, model_name: str = None) -> dict:
    """
    Classifie un document à partir d'un extrait représentatif (idéalement
    le titre, l'abstract, et le début de l'introduction)

    Args:
        document_excerpt: extrait de texte représentatif du document
        model_name: nom du modèle Gemini à utiliser (par défaut, lit .env)

    Returns:
        Dictionnaire avec les clés "category", "confidence", "justification".
        En cas d'erreur de parsing, "category" vaut "other" par défaut.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY manquante dans .env")

    genai.configure(api_key=api_key)
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    model = genai.GenerativeModel(model_name)

    prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
        categories_description=build_categories_description(),
        document_excerpt=document_excerpt[:3000],  # limite pour ne pas envoyer un document entier
    )

    rate_limiter.wait_if_needed()
    response = model.generate_content(prompt, generation_config={"temperature": 0})

    raw_text = response.text.strip()

    # Nettoyage : Gemini peut parfois entourer le JSON de balises markdown
    # (```json ... ```) malgré la consigne -- on les retire si présentes.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json", "", 1).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f" Échec du parsing JSON de la réponse : {raw_text[:200]}")
        result = {
            "category": "other",
            "confidence": "low",
            "justification": "Erreur de parsing de la réponse du modèle",
        }

    # Validation : si le modèle a halluciné une catégorie inexistante,
    # on retombe sur "other" plutôt que de propager une valeur invalide.
    if result.get("category") not in TAXONOMY:
        print(f" Catégorie inconnue retournée : {result.get('category')}, repli sur 'other'")
        result["category"] = "other"

    return result