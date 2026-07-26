from src.database.session import engine
from src.database.models import Base

Base.metadata.create_all(bind=engine)
print("Tables créées avec succès dans PostgreSQL.")