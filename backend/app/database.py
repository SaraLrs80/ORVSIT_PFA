"""
Connexion à la base de données avec SQLAlchemy.

- engine        : la connexion « physique » à PostgreSQL (créée une seule fois).
- SessionLocal  : une fabrique de « sessions ». Une session = une conversation
                  avec la base le temps d'une requête (lire/écrire puis fermer).
- Base          : la classe de base dont hériteront nos modèles (tables).
- get_db()      : fournit une session à une route, puis la referme proprement,
                  même en cas d'erreur (grâce au try/finally).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# pool_pre_ping=True : vérifie que la connexion est encore vivante avant de
# l'utiliser (évite des erreurs si PostgreSQL a coupé une connexion inactive).
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """Dépendance FastAPI : ouvre une session, la donne à la route, puis la ferme."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

engine_dwh = create_engine(settings.warehouse_url, pool_pre_ping=True)
SessionDWH = sessionmaker(bind=engine_dwh, autoflush=False, autocommit=False)

def get_dwh():
    """Dépendance FastAPI : ouvre une session, la donne à la route, puis la ferme."""
    db = SessionDWH()
    try:
        yield db
    finally:
        db.close()