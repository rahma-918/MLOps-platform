#Module de génération des représentations vectorielles (embeddings).
#Utilise un modèle HuggingFace via l'interface standardisée de LangChain.

from langchain_community.embeddings import HuggingFaceEmbeddings

# Charge un modèle d'embeddings HuggingFace
def get_embedding_model(
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
):

    print(f"Chargement du modèle d'embeddings : {model_name}")
    print("(le premier chargement peut prendre du temps, le modèle est téléchargé et mis en cache localement)")

    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},  # passe à "cuda" si un GPU compatible est disponible
        encode_kwargs={"normalize_embeddings": True}  # normalisation -> meilleure similarité cosinus
    )

    print("Modèle d'embeddings chargé avec succès.\n")
    return embedding_model