# Module de découpage (chunking) des documents en segments de texte
# exploitables pour la génération d'embeddings et la recherche sémantique.

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.ingestion.loader import ExtractedPage


def convert_to_langchain_documents(pages: list[ExtractedPage]) -> list[Document]:
    """
    Convertit les ExtractedPage en objets Document LangChain, format standard attendu par le text splitter
    et par la base vectorielle ChromaDB.
    """
    documents = []
    for page in pages:
        if page.text.strip():  # ignore les pages vides (OCR raté, page blanche, etc.)
            documents.append(Document(
                page_content=page.text,
                metadata=page.metadata
            ))
    return documents

#Découpe les documents en segments (chunks) de taille contrôlée.
def chunk_documents(
    documents: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50 #chevauchement entre chunks consécutifs, pour ne pas couper une idée importante entre deux segments
) -> list[Document]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Ordre de priorité des séparateurs : essaie de couper sur un paragraphe,
        # sinon une phrase, sinon un mot -- pour préserver le sens autant que possible.
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_documents(documents)

    # Ajout d'un identifiant unique de chunk (utile pour le debug et le retour aux sources)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    print(f"{len(documents)} document(s)/page(s) -> {len(chunks)} chunks générés")
    return chunks