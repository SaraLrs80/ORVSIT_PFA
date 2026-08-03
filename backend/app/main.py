"""
Point d'entrée de l'API ORVSIT.

On lance le serveur avec :  uvicorn app.main:app --reload
(depuis le dossier backend/, avec le venv activé)

Documentation interactive auto-générée : http://localhost:8000/docs
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from .routers import auth, demandes, admin, territoires, overview, fiche, comparer, explorer
from .database import get_db

app = FastAPI(title="API ORVSIT", version="0.1.0")

# --- CORS ---
# Le frontend (Vite) tourne sur http://localhost:5173, l'API sur :8000.
# Par sécurité, un navigateur bloque par défaut les appels entre origines
# différentes. On autorise explicitement le frontend à appeler l'API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)#ajoute toutes les routes du router auth à l'application principale. Donc toutes les routes définies dans auth.py seront accessibles via l'API.
app.include_router(demandes.router)#ajoute toutes les routes du router demandes à l'application principale. Donc toutes les routes définies dans demandes.py seront accessibles via l'API.
app.include_router(admin.router)#routes de l'espace admin (réservées aux administrateurs).
app.include_router(territoires.router)#routes liées aux territoires (réservées aux utilisateurs connectés).
app.include_router(overview.router)#vue d'ensemble régionale (lit referential.idt_territoire).
app.include_router(fiche.router)#fiche territoriale : toutes les données d'une province ou d'une commune.
app.include_router(comparer.router)#comparaison de territoires. 
app.include_router(explorer.router)#exploration des données.

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Vérifie que l'API répond ET qu'elle est bien connectée à la base.
    Depends(get_db) = FastAPI ouvre une session, nous la passe, puis la ferme.
    SELECT 1 est une requête minimale qui réussit seulement si la base répond.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connectée à orvsit_app"}
