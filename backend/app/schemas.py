from pydantic import BaseModel
from datetime import datetime

class LoginRequest(BaseModel):
    email: str
    mot_de_passe: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class UtilisateurOut(BaseModel):
    utilisateur_id: int
    nom_complet: str
    email: str
    role: str
    organisation: str | None = None
    statut: str
    derniere_connexion: datetime | None = None
    model_config = {
        "from_attributes": True} # autorise FastAPI à construire ce schéma directement depuis ton objet SQLAlchemy
 
class UtilisateurUpdate(BaseModel):
    role: str | None = None
    organisation: str | None = None
    statut: str | None = None
    
class UtilisateurCreate(BaseModel):
    nom_complet: str
    email: str
    role: str = "analyste"
    organisation: str | None = None
    
class DemandeAccesCreate(BaseModel):
    """Ce que le client envoie via le formulaire public."""
    nom_complet: str
    email: str
    organisation: str | None = None
    profil_souhaite: str = "analyste"
    motif: str | None = None


class DemandeAccesOut(BaseModel):
    """Ce que l'API renvoie pour confirmer l'enregistrement."""
    demande_id: int
    nom_complet: str
    email: str
    organisation: str | None = None
    profil_souhaite: str
    motif: str | None = None
    statut: str
    date_demande: datetime

    model_config = {"from_attributes": True}


class ApprobationOut(BaseModel):
    """Réponse renvoyée quand l'admin approuve une demande (compte créé)."""
    message: str
    utilisateur_id: int
    email: str

    
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    nouveau_mot_de_passe: str

