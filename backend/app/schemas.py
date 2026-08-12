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


# --- Assistant conversationnel ---------------------------------------------

class QuestionIn(BaseModel):
    """Ce que le navigateur envoie.

    `conversation_id` est facultatif : absent, une conversation s'ouvre.
    L'état — dernier territoire, dernier indicateur — ne transite PAS par le
    navigateur ; il est lu en base à partir de cet identifiant. Une conversation
    survit donc à un rechargement de page.
    """
    question: str
    conversation_id: int | None = None


class ReponseOut(BaseModel):
    """Ce que l'utilisateur reçoit.

    On rend la réponse et sa provenance. La branche et le motif de refus sont
    exposés parce qu'ils sont honnêtes : ils disent POURQUOI l'assistant a
    répondu ainsi, et l'interface peut les afficher discrètement.

    `message_id` sert à donner un avis sur cette réponse précise.

    Ce qu'on ne rend pas : les faits transmis au modèle et le brouillon avant
    reformulation. Utiles au débogage, sans intérêt pour l'utilisateur.
    """
    conversation_id: int
    message_id: int
    reponse: str
    branche: str | None = None
    refus: str | None = None
    source: str | None = None
    millesime: str | None = None
    territoire: str | None = None
    duree_ms: int | None = None


class ConversationOut(BaseModel):
    conversation_id: int
    titre: str | None = None
    date_creation: datetime
    date_maj: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    """Une ligne du fil : une question ou une réponse, selon `role`."""
    message_id: int
    role: str
    contenu: str
    branche: str | None = None
    refus: str | None = None
    date_envoi: datetime

    model_config = {"from_attributes": True}


class RenommerIn(BaseModel):
    titre: str


class AvisIn(BaseModel):
    utile: bool
    commentaire: str | None = None

class EvenementIn(BaseModel):
    """
    Ce que le frontend envoie pour tracer une action.
    `action` est contrôlée côté serveur contre une liste fermée : on ne laisse
    pas le navigateur décider de ce qui entre dans le journal d'usage.
    `cible` est facultative et sert à préciser quoi (ex: "fiche/Tétouan").
    """
    action: str
    cible: str | None = None