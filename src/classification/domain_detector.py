# src/classification/domain_detector.py
"""
Détecte le domaine d'un document à partir de son extrait.
Utilise soit des mots-clés heuristiques (rapide, gratuit), soit Gemini (précis).
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from src.rag.rate_limiter import rate_limiter

load_dotenv()

# Mots-clés indicateurs par domaine (heuristique rapide, sans appel API)
DOMAIN_KEYWORDS = {
    "medical": [
        "patient", "hospital", "clinical", "vaccine", "disease", "treatment",
        "symptom", "diagnosis", "pharmaceutical", "epidemiology", "cohort",
        "randomized", "meta-analysis", "systematic review", "trial", "drug",
        "efficacy", "adverse event", "mortality", "prevalence", "incidence",
        "santé", "médical", "vaccination", "maladie", "traitement", "patient",
        "essai clinique", "étude de cohorte", "pharmacovigilance"
    ],
    "technical": [
        "algorithm", "API", "software", "database", "framework", "cloud",
        "architecture", "deployment", "code", "programming", "server",
        "infrastructure", "Docker", "Kubernetes", "machine learning", "neural",
        "algorithme", "logiciel", "déploiement", "infrastructure", "code",
        "système", "architecture", "framework", "base de données"
    ],
    "legal": [
        "contract", "agreement", "clause", "liability", "jurisdiction",
        "plaintiff", "defendant", "judgment", "statute", "regulation",
        "compliance", "GDPR", "litigation", "arbitration",
        "contrat", "clause", "responsabilité", "juridiction", "tribunal",
        "jugement", "loi", "règlement", "conformité", "RGPD", "statuts"
    ],
}

DOMAIN_PROMPT = """Analyse cet extrait de document et détermine son domaine principal.
Choisis UNIQUEMENT parmi : medical, technical, legal, general.
Réponds par un seul mot, sans ponctuation.

Extrait :
{excerpt}

Domaine :"""


def detect_domain_heuristic(excerpt: str) -> str:
    """Détection rapide par mots-clés, sans appel API."""
    text_lower = excerpt.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw.lower() in text_lower)
    
    if not scores or max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


def detect_domain_llm(excerpt: str, model_name: str = None) -> str:
    """Détection précise via Gemini (1 appel API rapide)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "general"

    genai.configure(api_key=api_key)
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    model = genai.GenerativeModel(model_name)

    prompt = DOMAIN_PROMPT.format(excerpt=excerpt[:1500])

    rate_limiter.wait_if_needed()
    response = model.generate_content(prompt, generation_config={"temperature": 0})
    
    domain = response.text.strip().lower()
    if domain not in ("medical", "technical", "legal"):
        domain = "general"
    return domain


def detect_domain(excerpt: str, use_llm: bool = True) -> str:
    """
    Détecte le domaine. Par défaut utilise Gemini (précis).
    Si use_llm=False, utilise l'heuristique (instantané, offline).
    """
    if use_llm:
        return detect_domain_llm(excerpt)
    return detect_domain_heuristic(excerpt)