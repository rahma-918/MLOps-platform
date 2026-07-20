# main_ingestion.py
"""
Script d'ingestion : Chargement -> Chunking -> Embeddings -> Stockage vectoriel
"""

from src.ingestion.loader import load_all_documents
from src.ingestion.chunker import convert_to_langchain_documents, chunk_documents
from src.ingestion.embedder import get_embedding_model
from src.vectorstore.chroma_store import build_vectorstore
import shutil
from pathlib import Path


def reset_vectorstore(persist_directory: str = "chroma_db"):
    path = Path(persist_directory)
    if path.exists():
        shutil.rmtree(path)
        print(f"Ancienne base vectorielle '{persist_directory}' supprimée avant nouvelle ingestion.")
    else:
        print(f"Aucune base vectorielle existante trouvée dans '{persist_directory}' (premier lancement).")


if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE D'INGESTION DOCUMENTAIRE")
    print("=" * 60)

    # 0. Nettoyage de la base vectorielle précédente
    reset_vectorstore()

    # 1. Chargement (extraction texte natif + OCR si besoin)
    print("\n[1/4] Chargement des documents...")
    pages = load_all_documents("data/raw", ocr_lang="fra")

    # 2. Conversion + Chunking
    print("\n[2/4] Découpage en segments...")
    documents = convert_to_langchain_documents(pages)
    chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

    # 3. Génération des embeddings
    print("\n[3/4] Chargement du modèle d'embeddings...")
    embedding_model = get_embedding_model()

    # 4. Stockage vectoriel
    print("\n[4/4] Génération et stockage des vecteurs dans ChromaDB...")
    build_vectorstore(chunks, embedding_model)

    print("\n✅ Ingestion terminée. Base vectorielle prête dans 'chroma_db/'.")
    print("Utilise test_search.py pour interroger la base.")