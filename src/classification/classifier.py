# src/classification/classifier.py
"""
Module de classification zero-shot générique.
1. Détecte le domaine du document
2. Charge la taxonomie appropriée
3. Classifie dans la catégorie la plus pertinente
"""

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from src.rag.rate_limiter import rate_limiter
from src.classification.taxonomies import TAXONOMIES, DEFAULT_TAXONOMY
from src.classification.domain_detector import detect_domain

load_dotenv()


def build_prompt(taxonomy: dict, document_excerpt: str) -> str:
    """Construit le prompt de classification pour une taxonomie donnée."""
    categories_description = "\n".join(
        f"- {key} : {desc}" for key, desc in taxonomy.items()
    )
    
    return f"""You are an assistant specialized in classifying documents.

Here are the possible categories, with their definitions:
{categories_description}

Here is an excerpt from the document to classify (title, abstract, and beginning):

{document_excerpt[:3000]}

Respond ONLY in the following JSON format, with no text before or after:
{{
  "category": "<one of the categories exactly as written above>",
  "confidence": "<high|medium|low>",
  "justification": "<one short sentence explaining your choice>"
}}
"""


def classify_document(
    document_excerpt: str,
    model_name: str = None,
    forced_domain: str = None,
    use_llm_domain: bool = True
) -> dict:
    """
    Classifie un document de manière générique.
    
    Args:
        document_excerpt: extrait représentatif (titre + abstract + début)
        model_name: modèle Gemini à utiliser
        forced_domain: force un domaine spécifique (medical, general, technical, legal)
                        Si None, détection automatique.
        use_llm_domain: si True, utilise Gemini pour détecter le domaine.
                        Si False, heuristique rapide (offline).
    
    Returns:
        dict avec "category", "confidence", "justification", "domain"
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY manquante dans .env")

    # --- Étape 1 : Détection du domaine ---
    if forced_domain and forced_domain in TAXONOMIES:
        domain = forced_domain
    else:
        domain = detect_domain(document_excerpt, use_llm=use_llm_domain)
    
    taxonomy = TAXONOMIES.get(domain, TAXONOMIES[DEFAULT_TAXONOMY])
    
    print(f"  [Classification] Domaine détecté : {domain} ({len(taxonomy)} catégories)")

    # --- Étape 2 : Classification dans la taxonomie du domaine ---
    genai.configure(api_key=api_key)
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    model = genai.GenerativeModel(model_name)

    prompt = build_prompt(taxonomy, document_excerpt)

    rate_limiter.wait_if_needed()
    response = model.generate_content(prompt, generation_config={"temperature": 0})

    raw_text = response.text.strip()

    # Nettoyage markdown
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"  Échec parsing JSON : {raw_text[:200]}")
        result = {
            "category": "other",
            "confidence": "low",
            "justification": "Erreur de parsing de la réponse du modèle",
        }

    # Validation catégorie
    if result.get("category") not in taxonomy:
        print(f"  Catégorie inconnue : {result.get('category')}, repli sur 'other'")
        result["category"] = "other"

    # Enrichissement du résultat
    result["domain"] = domain
    return result


def classify_batch(excerpts: list[str], **kwargs) -> list[dict]:
    """
    Classifie plusieurs documents en séquence.
    Utile pour l'ingestion par lot.
    """
    results = []
    for i, excerpt in enumerate(excerpts):
        print(f"[{i+1}/{len(excerpts)}] Classification...")
        results.append(classify_document(excerpt, **kwargs))
    return results