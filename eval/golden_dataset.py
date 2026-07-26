#Jeu de données de référence pour l'évaluation du RAG.

GOLDEN_DATASET = [
    # --- Questions factuelles avec réponse précise attendue dans le corpus ---
    {
        "id": "Q1",
        "question": "What are the adverse events of COVID-19 vaccination in pregnant women?",
        "expected_fragment": "injection site pain",
        "expected_source": "article1.pdf",
        "category": "factual",
    },
    {
        "id": "Q2",
        "question": "What is the recurrence rate of CIN2+ after HPV vaccination?",
        "expected_fragment": "3.0%",
        "expected_source": "article4.pdf",
        "category": "factual",
    },
    {
        "id": "Q3",
        "question": "What was the lowest vaccine wastage rate reported in Nigeria?",
        "expected_fragment": "18%",
        "expected_source": "article3.docx",
        "category": "factual",
    },
    {
        "id": "Q4",
        "question": "What percentage of vaccinators were familiar with the multi-dose vial policy?",
        "expected_fragment": "55%",
        "expected_source": "article3.docx",
        "category": "factual",
    },
    {
        "id": "Q5",
        "question": "What was the pooled odds ratio for preterm delivery after COVID-19 vaccination?",
        "expected_fragment": "0.62",
        "expected_source": "article1.pdf",
        "category": "factual",
    },
    {
        "id": "Q6",
        "question": "What percentage of studies reported positive efficacy outcomes of influenza vaccination in cancer patients?",
        "expected_fragment": "seven",
        "expected_source": "article2-Scanned.pdf",
        "category": "factual",
    },

    # --- Questions hors corpus : le RAG doit refuser, pas halluciner ---
    {
        "id": "R1",
        "question": "What are the side effects of the malaria vaccine?",
        "expected_fragment": None,  # aucune réponse valide attendue
        "expected_source": None,
        "category": "refusal",
    },
    {
        "id": "R2",
        "question": "What is the recommended dosage of paracetamol for children?",
        "expected_fragment": None,
        "expected_source": None,
        "category": "refusal",
    },
    {
        "id": "R3",
        "question": "Quels sont les traitements recommandés contre la tuberculose ?",
        "expected_fragment": None,
        "expected_source": None,
        "category": "refusal",
    },

    # --- Questions en français, pour tester la cohérence linguistique ---
    {
        "id": "F1",
        "question": "Quel est le taux de récidive du CIN2+ après vaccination HPV ?",
        "expected_fragment": "3,0",  
        "expected_source": "article4.pdf",
        "category": "factual_fr",
    },

    # questions ciblant explicitement des données de tableaux

{
    "id": "T1",
    "question": "What was the odds ratio for headache as an adverse event?",
    "expected_fragment": "3.05",
    "expected_source": "article1.pdf",
    "category": "table_extraction",  # nouvelle catégorie dédiée
},
{
    "id": "T2",
    "question": "What was the odds ratio for low birth weight after COVID-19 vaccination?",
    "expected_fragment": "0.88",
    "expected_source": "article1.pdf",
    "category": "table_extraction",
},
{
    "id": "T3",
    "question": "How many pregnant women received the vaccine in Gandhi et al. 2022 study?",
    "expected_fragment": "247",
    "expected_source": "article1.pdf",
    "category": "table_extraction",
},

{
    "id": "Q7",
    "question": "What was the effect of text messaging reminders on influenza vaccine uptake?",
    "expected_fragment": "9%",  
    "expected_source": "rct_txt4flujab.pdf",
    "category": "factual",
},
{
    "id": "Q8",
    "question": "What adverse event was reported in the myocardial injury case report following COVID-19 vaccination?",
    "expected_fragment": "congestive heart failure", 
    "expected_source": "case_report_myocardial_injury.pdf",
    "category": "factual",
},
]