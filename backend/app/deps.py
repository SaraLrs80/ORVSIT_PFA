from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import Utilisateur
from .security import decode_access_token

bearer = HTTPBearer()   # sait extraire le jeton de l'en-tête Authorization

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Utilisateur:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:                       # jeton invalide ou expiré
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide ou expiré")

    user_id = payload.get("sub")
    if user_id is None:                        # jeton sans identité
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide")
    utilisateur = db.query(Utilisateur).filter(
        Utilisateur.utilisateur_id == int(user_id)
    ).first()
    if payload.get("type") != "access":           # jeton de rafraîchissement utilisé par erreur
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "type de Token invalide")
    if utilisateur is None:                    # utilisateur supprimé entre-temps
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur non trouvé")
    if utilisateur.statut != "actif":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé. Contactez l'administrateur.")
    return utilisateur


def get_current_admin(
    utilisateur: Utilisateur = Depends(get_current_user),
) -> Utilisateur:
    """
    Gardien « admin uniquement ».
    Il RÉUTILISE get_current_user (donc : jeton valide + utilisateur existant),
    puis vérifie en plus le rôle. Si ce n'est pas un admin -> 403 (interdit).
    Une route qui écrit Depends(get_current_admin) est ainsi réservée aux admins.
    """
    if utilisateur.role != "administrateur":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Accès réservé aux administrateurs"
        )
    return utilisateur