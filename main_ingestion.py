# main_ingestion.py
"""
Script d'ingestion : Chargement -> Chunking -> Embeddings -> Stockage vectoriel
"""
from src.classification.classifier import classify_document
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

def enrich_chunks_with_category(chunks):
    """
    Classifie chaque document source une seule fois (à partir de ses
    premiers chunks), puis applique cette catégorie à TOUS les chunks
    de ce document
    """
    # Regroupe les chunks par document source
    chunks_by_source = {}
    for chunk in chunks:
        source = chunk.metadata["source_file"]
        chunks_by_source.setdefault(source, []).append(chunk)

    category_by_source = {}
    for source, source_chunks in chunks_by_source.items():
        # Utilise les 2-3 premiers chunks (triés par page/section) comme extrait
        sorted_chunks = sorted(source_chunks, key=lambda c: c.metadata.get("page_number", 0))
        excerpt = "\n".join(c.page_content for c in sorted_chunks[:3])

        print(f"  Classification de {source}...")
        result = classify_document(excerpt)
        category_by_source[source] = result["category"]
        print(f"    -> {result['category']} (confiance: {result['confidence']})")

    # Applique la catégorie à chaque chunk de son document
    for chunk in chunks:
        source = chunk.metadata["source_file"]
        chunk.metadata["category"] = category_by_source[source]

    return chunks

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

    # enrichissement avec la catégorie
    print("\n[3.5/4] Classification des documents pour enrichissement des métadonnées...")
    chunks = enrich_chunks_with_category(chunks)

    # 4. Stockage vectoriel
    print("\n[4/4] Génération et stockage des vecteurs dans ChromaDB...")
    build_vectorstore(chunks, embedding_model)

    print("\n✅ Ingestion terminée. Base vectorielle prête dans 'chroma_db/'.")