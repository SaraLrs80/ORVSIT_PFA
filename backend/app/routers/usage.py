"""
Journal d'usage : le frontend signale ici les actions qu'il vient d'exécuter.

Un export ou une impression se déroulent entièrement dans le navigateur ; le
serveur n'en sait rien. Sans ce signal, le compteur « rapports exportés » de
l'espace d'administration resterait à zéro alors que la fonction est utilisée.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Utilisateur
from ..schemas import EvenementIn
from ..journal import journaliser

router = APIRouter(prefix="/journal", tags=["journal d'usage"])

# Liste fermée des actions qu'un client a le droit d'inscrire.
# Le serveur reste maître de ce qui entre dans le journal : sans cette liste,
# un utilisateur connecté pourrait fabriquer de fausses statistiques.
ACTIONS_AUTORISEES = {"export", "impression"}


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
def enregistrer(
    evenement: EvenementIn,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """
    Enregistre une action de l'utilisateur connecté dans le journal d'usage.

    - **action** : « export » ou « impression »
    - **cible** : facultatif, ce sur quoi portait l'action (ex : « fiche/Tétouan »)
    """
    if evenement.action not in ACTIONS_AUTORISEES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Action non autorisée. Valeurs admises : {sorted(ACTIONS_AUTORISEES)}",
        )
    # On tronque à la largeur de la colonne en base (160 caractères).
    cible = (evenement.cible or "")[:160] or None
    journaliser(db, utilisateur.utilisateur_id, evenement.action, cible)
    db.commit()   # journaliser() ajoute seulement ; c'est à l'appelant de valider