#Module de gestion du stockage vectoriel avec ChromaDB.

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


def build_vectorstore(
    chunks: list[Document],
    embedding_model,
    persist_directory: str = "chroma_db",
    collection_name: str = "documents_sante_publique"
) -> Chroma:
    """
    Crée une base vectorielle ChromaDB à partir des chunks et la persiste sur disque.

    Args:
        chunks: liste de Document (chunks) à vectoriser
        embedding_model: modèle d'embeddings (depuis embedder.py)
        persist_directory: dossier local où ChromaDB stocke ses données
        collection_name: nom de la collection (utile si tu gères plusieurs corpus)

    Returns:
        L'objet Chroma prêt pour la recherche sémantique.
    """
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_directory,
        collection_name=collection_name
    )

    print(f"Base vectorielle créée : {len(chunks)} vecteurs stockés dans '{persist_directory}'")
    print(f"Collection : '{collection_name}'")
    return vectorstore


def load_vectorstore(
    embedding_model,
    persist_directory: str = "chroma_db",
    collection_name: str = "documents_sante_publique"
) -> Chroma:
    """
    Recharge une base vectorielle existante depuis le disque
    (utile pour ne pas re-générer les embeddings à chaque exécution).

    Args:
        embedding_model: le même modèle d'embeddings utilisé à la création
        persist_directory: dossier où la base a été sauvegardée
        collection_name: nom de la collection à charger

    Returns:
        L'objet Chroma rechargé.
    """
    return Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_model,
        collection_name=collection_name
    )