"""
Configuration de la connexion à PostgreSQL et gestion des sessions
SQLAlchemy (une session = une transaction de travail avec la base).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag_user:rag_password@localhost:5432/rag_platform"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Générateur de session, utilisé comme dépendance FastAPI (Depends).
    Garantit que la session est bien fermée après chaque requête, même
    en cas d'erreur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()