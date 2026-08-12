from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Utilisateur
from ..security import decode_access_token, hash_password, verify_password, create_access_token
from ..schemas import ForgotPasswordRequest, LoginRequest, LoginResponse, ResetPasswordRequest, UtilisateurOut
from ..deps import get_current_user
from datetime import datetime, timedelta, timezone
from ..emailing import envoyer_email
from ..journal import journaliser 

router = APIRouter(prefix="/auth", tags=["auth"])#router c'est un objet qui va contenir toutes les routes liées à l'authentification. On peut le monter dans l'application principale avec app.include_router(router).

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authentifie un utilisateur et retourne un token JWT.

    - **email**: Email de l'utilisateur
    - **mot_de_passe**: Mot de passe de l'utilisateur
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == request.email).first()
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect")
    
    if not verify_password(request.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect")
    if utilisateur.statut != "actif":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé. Contactez l'administrateur.")
    access_token = create_access_token(data={"sub": str(utilisateur.utilisateur_id), "role": utilisateur.role, "type": "access"})
    utilisateur.derniere_connexion = datetime.now(timezone.utc)
    journaliser(db, utilisateur.utilisateur_id, "connexion")   # ← trace la connexion
    db.commit()
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UtilisateurOut) #pour savoir qui est l'utilisateur actuellement connecté, on peut faire un GET sur /auth/me avec le token dans l'en-tête Authorization.
def read_current_user(current_user: Utilisateur = Depends(get_current_user)):
    """
    Retourne les informations de l'utilisateur actuellement authentifié.
    """
    return current_user

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Endpoint pour la réinitialisation du mot de passe.
    - **email**: Email de l'utilisateur qui a oublié son mot de passe
    """
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == data.email).first()
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    token_reset = create_access_token(data={"sub": str(utilisateur.utilisateur_id), "type": "reset"}, expires_delta=timedelta(minutes=30))
    lien_reset = f"http://localhost:5173/reset-password?token={token_reset}"
    envoyer_email(utilisateur.email, "Réinitialisation du mot de passe", f"Click sur le lien pour réinitialiser votre mot de passe : {lien_reset}")
    # Ici, vous pouvez générer un token de réinitialisation et l'envoyer par email à l'utilisateur.
    # Pour simplifier, nous ne faisons que retourner un message.
    return {"message": "Si un compte existe pour cet e-mail, un lien de réinitialisation a été envoyé."}

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Endpoint pour la réinitialisation du mot de passe.
    - **token**: Token de réinitialisation reçu par email
    - **nouveau_mot_de_passe**: Nouveau mot de passe choisi par l'utilisateur
    """
    payload = decode_access_token(data.token)
    # decode_access_token renvoie None si le jeton est illisible OU expiré.
    # Sans ce test, la ligne suivante plante et l'API répond 500 au lieu de 400.
    if payload is None or payload.get("type") not in ("reset", "invitation"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Lien invalide ou expiré")
    user_id = payload.get("sub")
    utilisateur = db.query(Utilisateur).filter(Utilisateur.utilisateur_id == int(user_id)).first()
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    
    utilisateur.mot_de_passe_hash = hash_password(data.nouveau_mot_de_passe)
    db.commit()
    
    return {"message": "Mot de passe réinitialisé avec succès."}