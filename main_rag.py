from src.rag.rag_chain import build_rag_chain, ask

if __name__ == "__main__":
    print("Construction de la chaîne RAG (connexion à Gemini, chargement de la base)...")
    llm, retriever, vectorstore, model_name = build_rag_chain(k=20)

    questions = [
        "What are the adverse events of COVID-19 vaccination in pregnant women?",
        "What is the recurrence rate of CIN2+ after HPV vaccination?",
        "What was the mean monthly vaccine wastage rate in Nigeria?",
        "What are the side effects of the malaria vaccine?",
    ]

    for question in questions:
        ask(question, llm, retriever, vectorstore, model_name, use_multi_query=True)
        print("\n" + "=" * 60)