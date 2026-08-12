from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import DemandeAcces
from ..schemas import DemandeAccesCreate, DemandeAccesOut

router = APIRouter(prefix="/demandes", tags=["demandes"])

@router.post("/", response_model=DemandeAccesOut, status_code=201)
def create_demande(demande: DemandeAccesCreate, db: Session = Depends(get_db)):
    """
    Crée une nouvelle demande d'accès.

    - **nom_complet**: Nom complet du demandeur
    - **email**: Email du demandeur
    - **organisation**: Organisation du demandeur (optionnel)
    - **profil_souhaite**: Profil souhaité (par défaut "analyste")
    - **motif**: Motif de la demande (optionnel)
    """
    nouvelle_demande = DemandeAcces(
        nom_complet=demande.nom_complet,
        email=demande.email,
        organisation=demande.organisation,
        profil_souhaite=demande.profil_souhaite,
        motif=demande.motif,
        #statut="en attente"
    )
    db.add(nouvelle_demande)
    db.commit()
    db.refresh(nouvelle_demande)
    return nouvelle_demande