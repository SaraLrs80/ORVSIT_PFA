"""
Routes de l'espace administrateur.
TOUTES sont protégées par Depends(get_current_admin) : accessibles seulement
à un utilisateur connecté ayant le rôle "administrateur".
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_admin
from ..models import Utilisateur, DemandeAcces, JournalUsage
from ..security import hash_password, create_access_token
from ..schemas import DemandeAccesOut, ApprobationOut, UtilisateurOut,UtilisateurUpdate, UtilisateurCreate
from ..emailing import envoyer_email

router = APIRouter(prefix="/admin", tags=["admin"])


# --- 1. Lister les demandes d'accès ---
# `statut` est un paramètre de requête FACULTATIF (ex: /admin/demandes?statut=en_attente).
# response_model=list[DemandeAccesOut] : on renvoie une LISTE de demandes.
@router.get("/demandes", response_model=list[DemandeAccesOut])
def lister_demandes(
    statut: str | None = None,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    requete = db.query(DemandeAcces)
    if statut:  # si l'admin filtre (ex: seulement "en_attente")
        requete = requete.filter(DemandeAcces.statut == statut)
    # les plus récentes d'abord
    return requete.order_by(DemandeAcces.date_demande.desc()).all()


# --- 2. Approuver une demande -> créer le compte utilisateur ---
# {demande_id} est un paramètre de CHEMIN : /admin/demandes/3/approuver
@router.post("/demandes/{demande_id}/approuver", response_model=ApprobationOut)
def approuver_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    demande = db.query(DemandeAcces).filter(
        DemandeAcces.demande_id == demande_id
    ).first()
    if demande is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    if demande.statut != "en_attente":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Demande déjà traitée")

    # Un compte existe-t-il déjà avec cet email ?
    if db.query(Utilisateur).filter(Utilisateur.email == demande.email).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Un compte existe déjà avec cet email"
        )

    # On génère un mot de passe temporaire aléatoire (l'admin le communiquera).
    mot_de_passe_temp_inutilisable = hash_password(secrets.token_urlsafe(12))  # jamais en clair

    nouvel_utilisateur = Utilisateur(
        nom_complet=demande.nom_complet,
        email=demande.email,
        mot_de_passe_hash=mot_de_passe_temp_inutilisable,  # jamais en clair
        role=demande.profil_souhaite,
        organisation=demande.organisation,
        statut="actif",
    )
    db.add(nouvel_utilisateur)
    db.flush()  # exécute l'INSERT sans finaliser -> on récupère l'id tout de suite
    #on cree le token d'invitation
    token_invitation = create_access_token(
        data={"sub": str(nouvel_utilisateur.utilisateur_id), "type": "invitation"},
        expires_delta=timedelta(hours=48),
    )
    lien_invitation = f"http://localhost:5173/reset-password?token={token_invitation}"
    envoyer_email(
        nouvel_utilisateur.email,
        "Votre compte ORVSIT a été créé",
        f"Bonjour {nouvel_utilisateur.nom_complet},\n\n"
        f"Votre compte a été créé avec le profil '{nouvel_utilisateur.role}'.\n"
        f"Veuillez cliquer sur le lien suivant pour définir votre mot de passe : {lien_invitation}\n\n"
        "Ce lien expirera dans 48 heures.\n\n"
        "Cordialement,\nL'équipe ORVSIT",
    )
    # On met à jour la demande (tracé de qui a traité, quand, quel compte créé)
    demande.statut = "approuvee"
    demande.traite_par = admin.utilisateur_id
    demande.date_traitement = datetime.now(timezone.utc)
    demande.utilisateur_cree = nouvel_utilisateur.utilisateur_id

    db.commit()  # valide les DEUX changements ensemble (création + mise à jour)
    db.refresh(nouvel_utilisateur)

    return {
        "message": "Demande approuvée, compte créé.",
        "utilisateur_id": nouvel_utilisateur.utilisateur_id,
        "email": nouvel_utilisateur.email,
    }


# --- 3. Rejeter une demande ---
@router.post("/demandes/{demande_id}/rejeter", response_model=DemandeAccesOut)
def rejeter_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    demande = db.query(DemandeAcces).filter(
        DemandeAcces.demande_id == demande_id
    ).first()
    if demande is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    if demande.statut != "en_attente":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Demande déjà traitée")

    demande.statut = "rejetee"
    demande.traite_par = admin.utilisateur_id
    demande.date_traitement = datetime.now(timezone.utc)

    db.commit()
    db.refresh(demande)
    return demande

@router.get("/utilisateurs", response_model=list[UtilisateurOut])
def lister_utilisateurs(
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    """
    Liste tous les utilisateurs du système.
    Accessible uniquement aux administrateurs.
    """
    return db.query(Utilisateur).order_by(Utilisateur.date_creation.desc()).all()

@router.patch("/utilisateurs/{utilisateur_id}", response_model=UtilisateurOut)
def mettre_a_jour_utilisateur(
    utilisateur_id: int,
    update_data: UtilisateurUpdate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    """
    Met à jour les informations d'un utilisateur.
    Accessible uniquement aux administrateurs.
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.utilisateur_id == utilisateur_id).first()
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    # Mettre à jour les champs si fournis
    if update_data.role is not None:
        utilisateur.role = update_data.role
    if update_data.organisation is not None:
        utilisateur.organisation = update_data.organisation
    if update_data.statut is not None:
        utilisateur.statut = update_data.statut

    db.commit()
    db.refresh(utilisateur) #db.refresh(objet) resynchronise l'objet Python avec la ligne réelle en base
    return utilisateur

@router.delete("/utilisateurs/{utilisateur_id}", status_code=204)
def supprimer_utilisateur(
    utilisateur_id: int,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    """
    Supprime un utilisateur du système.
    Accessible uniquement aux administrateurs.
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.utilisateur_id == utilisateur_id).first()
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    if utilisateur.utilisateur_id == admin.utilisateur_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vous ne pouvez pas supprimer votre propre compte")
    db.delete(utilisateur)
    db.commit()
    
@router.post("/utilisateurs/ajouter", response_model=UtilisateurOut, status_code=201)
def ajouter_utilisateur(
    nouvel_utilisateur: UtilisateurCreate,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    """
    Ajoute un nouvel utilisateur au système.
    Accessible uniquement aux administrateurs.
    """
    # Vérifier si l'email existe déjà
    if db.query(Utilisateur).filter(Utilisateur.email == nouvel_utilisateur.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un utilisateur avec cet email existe déjà")

    # Générer un mot de passe temporaire aléatoire
    mot_de_passe_temp_inutilisable = hash_password(secrets.token_urlsafe(12))  # jamais en clair

    utilisateur = Utilisateur(
        nom_complet=nouvel_utilisateur.nom_complet,
        email=nouvel_utilisateur.email,
        mot_de_passe_hash=mot_de_passe_temp_inutilisable,  # jamais en clair
        role=nouvel_utilisateur.role,
        organisation=nouvel_utilisateur.organisation,
        statut="actif",
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur) #pour obtenir l'id généré par la base de données

    # Créer un token d'invitation pour définir le mot de passe
    token_invitation = create_access_token(
        data={"sub": str(utilisateur.utilisateur_id), "type": "invitation"},
        expires_delta=timedelta(hours=48),
    )
    lien_invitation = f"http://localhost:5173/reset-password?token={token_invitation}"
    envoyer_email(
        utilisateur.email,
        "Votre compte ORVSIT a été créé",
        f"Bonjour {utilisateur.nom_complet},\n\n"
        f"Votre compte a été créé avec le profil '{utilisateur.role}'.\n"
        f"Veuillez cliquer sur le lien suivant pour définir votre mot de passe : {lien_invitation}\n\n"
        "Ce lien expirera dans 48 heures.\n\n"
        "Cordialement,\nL'équipe ORVSIT",
    )
    return utilisateur


# --- Statistiques d'usage (supervision) ---
# Renvoie les 4 compteurs de la maquette + l'usage des 7 derniers jours.
@router.get("/statistiques")
def statistiques(
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(get_current_admin),
):
    maintenant = datetime.now(timezone.utc)
    il_y_a_30j = maintenant - timedelta(days=30)

    # Petit raccourci : compter les événements d'un type d'action (depuis une date)
    def compter(action, depuis=None):
        q = db.query(JournalUsage).filter(JournalUsage.action == action)
        if depuis is not None:
            q = q.filter(JournalUsage.date_evenement >= depuis)
        return q.count()

    connexions_30j = compter("connexion", il_y_a_30j)
    rapports_exportes = compter("export", il_y_a_30j)
    questions_ia = compter("question_ia", il_y_a_30j)
    utilisateurs_actifs = (
        db.query(Utilisateur).filter(Utilisateur.statut == "actif").count()
    )

    # Usage des 7 derniers jours (du plus ancien au plus récent)
    JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    usage_hebdo = []
    for i in range(6, -1, -1):
        jour = (maintenant - timedelta(days=i)).date()
        debut = datetime(jour.year, jour.month, jour.day, tzinfo=timezone.utc)
        fin = debut + timedelta(days=1)

        def compter_jour(action):
            return (
                db.query(JournalUsage)
                .filter(
                    JournalUsage.action == action,
                    JournalUsage.date_evenement >= debut,
                    JournalUsage.date_evenement < fin,
                )
                .count()
            )

        usage_hebdo.append(
            {
                "jour": JOURS[jour.weekday()],
                "connexions": compter_jour("connexion"),
                "exports": compter_jour("export"),
            }
        )

    return {
        "connexions_30j": connexions_30j,
        "utilisateurs_actifs": utilisateurs_actifs,
        "rapports_exportes": rapports_exportes,
        "questions_ia": questions_ia,
        "usage_hebdo": usage_hebdo,
    }