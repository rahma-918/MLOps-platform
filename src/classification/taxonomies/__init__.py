# src/classification/taxonomies/__init__.py
from .medical import MEDICAL_TAXONOMY
from .general import GENERAL_TAXONOMY
from .technical import TECHNICAL_TAXONOMY
from .legal import LEGAL_TAXONOMY

# Registre des taxonomies disponibles
TAXONOMIES = {
    "medical": MEDICAL_TAXONOMY,
    "general": GENERAL_TAXONOMY,
    "technical": TECHNICAL_TAXONOMY,
    "legal": LEGAL_TAXONOMY,
}

# Taxonomie par défaut si le domaine n'est pas détecté
DEFAULT_TAXONOMY = "general"

TAXONOMY = MEDICAL_TAXONOMY