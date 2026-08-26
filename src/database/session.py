import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Priorité à DATABASE_URL si explicitement fournie (cas Docker Compose,
# où elle est déjà résolue correctement via ${...} au niveau du compose file).
# Sinon, la construire à partir des variables individuelles (cas Kubernetes,
# plus robuste que de dépendre de l'ordre d'injection des env vars dans le Pod).
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "postgres-service")
    port = os.getenv("POSTGRES_PORT", "5432")

    if not all([user, password, db]):
        raise ValueError(
            "Configuration base de données manquante : fournis soit DATABASE_URL, "
            "soit POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB."
        )
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()