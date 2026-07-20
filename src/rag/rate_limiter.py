# src/rag/rate_limiter.py
"""
Utilitaire simple pour respecter le quota gratuit de l'API Gemini.
Ajoute une pause automatique entre deux appels si nécessaire.
"""

import time


class RateLimiter:
    def __init__(self, min_seconds_between_calls: float = 4.5):
        # gemini-2.5-flash-lite : ~15-30 requêtes/minute selon la source
        # 4.5s de marge = ~13 requêtes/minute max, prudent et sûr
        self.min_seconds_between_calls = min_seconds_between_calls
        self.last_call_time = 0

    def wait_if_needed(self):
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_seconds_between_calls:
            wait_time = self.min_seconds_between_calls - elapsed
            print(f"  (pause de {wait_time:.1f}s pour respecter le quota API)")
            time.sleep(wait_time)
        self.last_call_time = time.time()


# Instance unique partagée par tout le module RAG, pour que le compteur
# de temps soit cohérent entre tous les appels (génération de reformulations
# ET génération de la réponse finale).
rate_limiter = RateLimiter()