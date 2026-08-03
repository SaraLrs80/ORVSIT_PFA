from app.database import SessionLocal
from app.models import Utilisateur
from app.security import hash_password

db = SessionLocal() # Ouvre une session de base de données
# On évite de créer deux fois le même email
existe = db.query(Utilisateur).filter(Utilisateur.email == "admin@orvsit.ma").first()
if existe:
    print("Ce compte existe déjà, id =", existe.utilisateur_id)
else:
    admin = Utilisateur(
        nom_complet="Admin ORVSIT",
        email="admin@orvsit.ma",
        mot_de_passe_hash=hash_password("Admin123!"),   # ← ta fonction
        role="administrateur",
        statut="actif",
    )
    db.add(admin)        # prépare l'insertion
    db.commit()          # exécute réellement l'INSERT en base
    db.refresh(admin)    # récupère l'id généré par PostgreSQL
    print("Admin créé, id =", admin.utilisateur_id)

db.close()

