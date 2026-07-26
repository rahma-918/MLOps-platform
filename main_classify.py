# Classifie chaque document présent dans la base vectorielle

from src.ingestion.embedder import get_embedding_model
from src.vectorstore.chroma_store import load_vectorstore
from src.classification.classifier import classify_document

embedding_model = get_embedding_model()
vectorstore = load_vectorstore(embedding_model)

collection = vectorstore.get()
documents = collection["documents"]
metadatas = collection["metadatas"]

# Regroupe les chunks par document source
chunks_by_source = {}
for text, meta in zip(documents, metadatas):
    source = meta["source_file"]
    page = meta.get("page_number", 0)
    chunks_by_source.setdefault(source, []).append((page, text))

print("=" * 70)
print("CLASSIFICATION DES DOCUMENTS")
print("=" * 70)

results = {}
for source, chunks in chunks_by_source.items():
    # Trie par numéro de page/section et prend les 2-3 premiers chunks
    # (typiquement titre + abstract + début d'introduction)
    chunks_sorted = sorted(chunks, key=lambda x: x[0])
    excerpt = "\n".join(text for _, text in chunks_sorted[:3])

    print(f"\n[{source}]")
    result = classify_document(excerpt)
    results[source] = result

    print(f"  Catégorie : {result['category']}")
    print(f"  Confiance : {result['confidence']}")
    print(f"  Justification : {result['justification']}")

print("\n" + "=" * 70)
print("RÉSUMÉ")
print("=" * 70)
for source, result in results.items():
    print(f"{source} -> {result['category']} ({result['confidence']})")