"""
La porte d'entrée de l'assistant conversationnel.

Quatre routes, toutes réservées aux utilisateurs connectés :

    POST /assistant/question                poser une question
    GET  /assistant/conversations           ses conversations, la plus récente d'abord
    GET  /assistant/conversation/{id}       le fil d'une conversation
    POST /assistant/message/{id}/avis       dire si la réponse a été utile

CE QUE CETTE COUCHE NE FAIT PAS
Elle ne décide rien. Toute l'intelligence est dans le moteur : elle reçoit une
question, retrouve la conversation, en déduit l'état, appelle le moteur,
enregistre l'échange et rend la réponse. Si elle prenait des décisions, on
aurait deux endroits où chercher pourquoi l'assistant a répondu ceci plutôt que
cela.

L'ÉTAT NE SE STOCKE PAS, IL SE LIT
Le dernier territoire et le dernier indicateur ne sont recopiés nulle part :
ils se lisent dans les références du dernier message de l'assistant. Une seule
vérité, donc aucune contradiction possible entre deux colonnes.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..assistant.moteur import MODELE, repondre
from ..database import get_db, get_dwh
from ..deps import get_current_user
from ..journal import journaliser
from ..models import (Conversation, Message, MessageFeedback, MessageReference,
                      Utilisateur)
from ..schemas import (AvisIn, ConversationOut, MessageOut, QuestionIn,
                       RenommerIn, ReponseOut)

router = APIRouter(prefix="/assistant", tags=["assistant"])

LONGUEUR_MAXIMALE = 500      # au-delà, ce n'est plus une question
LONGUEUR_TITRE = 80


def _conversation(db: Session, utilisateur: Utilisateur, conversation_id):
    """Retrouve la conversation demandée, ou en ouvre une nouvelle.

    Le contrôle du propriétaire n'est pas une formalité : les conversations
    sont numérotées, et sans lui il suffirait de changer le chiffre dans
    l'adresse pour lire les questions de quelqu'un d'autre. Les questions
    d'une personne disent ce qu'elle prépare et sur quoi elle travaille.
    """
    if conversation_id is None:
        conversation = Conversation(utilisateur_id=utilisateur.utilisateur_id)
        db.add(conversation)
        db.flush()                      # pour obtenir l'identifiant tout de suite
        return conversation

    conversation = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id).first()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation introuvable")
    if conversation.utilisateur_id != utilisateur.utilisateur_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Cette conversation ne vous appartient pas")
    return conversation


def _etat(db: Session, conversation_id: int) -> dict:
    """L'état de la conversation, DÉDUIT des références déjà enregistrées.

    C'est ce qui donne un sens à « et pour Larache ? » : on retrouve le dernier
    indicateur consulté et on change seulement de territoire.

    On ne lit PAS les références du dernier message, mais la référence la plus
    récente de CHAQUE type. La nuance est décisive : un refus ne cite ni
    indicateur ni territoire, donc il ne porte aucune référence. Lire le seul
    dernier message revenait à perdre tout le contexte dès qu'une question
    intermédiaire avait été refusée — et c'est précisément ce qui arrive dans
    une vraie conversation.

    Le contexte n'est pas « la dernière chose dite », c'est « la dernière chose
    dont on a effectivement parlé ».
    """
    lignes = (db.query(MessageReference)
              .join(Message, Message.message_id == MessageReference.message_id)
              .filter(Message.conversation_id == conversation_id)
              .order_by(MessageReference.message_id.desc())
              .limit(20).all())

    etat = {}
    for r in lignes:                       # du plus récent au plus ancien
        if r.type_entite == "territoire" and "territoire_id" not in etat:
            etat["territoire_id"] = r.entite_id
            etat["territoire_nom"] = r.libelle
        elif r.type_entite == "indicateur" and "indicateur_id" not in etat:
            etat["indicateur_id"] = r.entite_id
        if "territoire_id" in etat and "indicateur_id" in etat:
            break

    # Une précision en attente : l'assistant a demandé « la commune ou la
    # province ? » et la question d'origine doit être rejouée avec la réponse.
    # On ne la retient QUE si elle est le dernier échange : une attente vieille
    # de trois messages n'attend plus rien.
    dernier = (db.query(Message)
               .filter(Message.conversation_id == conversation_id,
                       Message.role == "assistant")
               .order_by(Message.message_id.desc()).first())
    if dernier is not None and dernier.branche == "question":
        attente = (db.query(MessageReference)
                   .filter(MessageReference.message_id == dernier.message_id,
                           MessageReference.type_entite.like("attente_%"))
                   .first())
        if attente is not None:
            etat["attente"] = {
                "question": attente.libelle,
                "type": attente.type_entite.removeprefix("attente_"),
            }
    return etat


@router.post("/question", response_model=ReponseOut)
def poser(
    entree: QuestionIn,
    db: Session = Depends(get_db),
    dwh: Session = Depends(get_dwh),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """
    Pose une question à l'assistant.

    - **question** : la question, telle qu'elle est écrite
    - **conversation_id** : facultatif ; absent, une conversation s'ouvre
    """
    question = (entree.question or "").strip()
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La question est vide")
    if len(question) > LONGUEUR_MAXIMALE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Question trop longue ({len(question)} caractères, "
            f"{LONGUEUR_MAXIMALE} au maximum)")

    conversation = _conversation(db, utilisateur, entree.conversation_id)
    if not conversation.titre:
        conversation.titre = question[:LONGUEUR_TITRE]

    # La question est enregistrée AVANT d'être traitée : si le moteur échoue,
    # on saura quelle question l'a mis en défaut.
    db.add(Message(conversation_id=conversation.conversation_id,
                   role="user", contenu=question))
    db.flush()

    debut = time.time()
    trace = repondre(dwh, question, etat=_etat(db, conversation.conversation_id))
    duree_ms = int((time.time() - debut) * 1000)

    reponse = Message(
        conversation_id=conversation.conversation_id,
        role="assistant",
        contenu=trace.get("reponse") or "",
        modele=MODELE if trace.get("reformulation") else None,
        branche=trace.get("branche"),
        refus=trace.get("refus"),
        reformulation=str(trace.get("reformulation") or "")[:80] or None,
        duree_ms=duree_ms,
    )
    db.add(reponse)
    db.flush()

    # La traçabilité : ce que cette réponse cite. Une réponse sans référence
    # est une réponse sans source, et cela se voit en base.
    etat = trace.get("etat") or {}
    if etat.get("territoire_id"):
        db.add(MessageReference(message_id=reponse.message_id,
                                type_entite="territoire",
                                entite_id=etat["territoire_id"],
                                libelle=etat.get("territoire_nom")))
    if trace.get("indicateur"):
        db.add(MessageReference(message_id=reponse.message_id,
                                type_entite="indicateur",
                                entite_id=trace["indicateur"],
                                libelle=trace.get("source")))

    # La question restée sans réponse, quand l'assistant demande une précision.
    # Sans elle, la réponse de l'utilisateur — « les communes » — arriverait
    # seule et n'aurait aucun sens.
    attente = trace.get("attente")
    if attente and attente.get("question"):
        # Le TYPE d'attente est porté par le nom de l'entité — attente_niveau
        # ou attente_indicateur. Le perdre reviendrait à interpréter « la
        # commune » comme un nom d'indicateur, ou l'inverse.
        db.add(MessageReference(
            message_id=reponse.message_id,
            type_entite=f"attente_{attente.get('type', 'niveau')}",
            entite_id=0, libelle=attente["question"][:200]))

    conversation.date_maj = func.now()
    journaliser(db, utilisateur.utilisateur_id, "question_ia",
                (trace.get("branche") or "")[:160])
    db.commit()

    return {
        "conversation_id": conversation.conversation_id,
        "message_id": reponse.message_id,
        "reponse": trace.get("reponse") or "",
        "branche": trace.get("branche"),
        "refus": trace.get("refus"),
        "source": trace.get("source"),
        "millesime": trace.get("millesime"),
        "territoire": trace.get("territoire") or etat.get("territoire_nom"),
        "duree_ms": duree_ms,
    }


@router.get("/conversations", response_model=list[ConversationOut])
def mes_conversations(
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """Les conversations de l'utilisateur connecté, la plus récente d'abord."""
    return (db.query(Conversation)
            .filter(Conversation.utilisateur_id == utilisateur.utilisateur_id)
            .order_by(Conversation.date_maj.desc())
            .limit(50).all())


@router.get("/conversation/{conversation_id}", response_model=list[MessageOut])
def fil(
    conversation_id: int,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """Le fil d'une conversation, du plus ancien au plus récent."""
    _conversation(db, utilisateur, conversation_id)      # contrôle du propriétaire
    return (db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.date_envoi, Message.message_id).all())


@router.patch("/conversation/{conversation_id}", response_model=ConversationOut)
def renommer(
    conversation_id: int,
    entree: RenommerIn,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """Renomme une conversation.

    Le titre par défaut est la première question, tronquée. Utile pour
    retrouver un fil, mais rarement le nom qu'on lui aurait donné.
    """
    conversation = _conversation(db, utilisateur, conversation_id)
    titre = (entree.titre or "").strip()
    if not titre:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le titre est vide")
    conversation.titre = titre[:LONGUEUR_TITRE]
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversation/{conversation_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def supprimer(
    conversation_id: int,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """
    Supprime une conversation et tout ce qui s'y rattache.

    On efface explicitement les avis, les références puis les messages, au lieu
    de s'en remettre aux suppressions en cascade : seule la clé étrangère de
    `message` vers `conversation` en déclare une. Compter sur un comportement
    qu'on n'a pas déclaré, c'est laisser la base décider à notre place.
    """
    _conversation(db, utilisateur, conversation_id)      # propriétaire

    ids = [m.message_id for m in db.query(Message.message_id)
           .filter(Message.conversation_id == conversation_id)]
    if ids:
        (db.query(MessageFeedback)
         .filter(MessageFeedback.message_id.in_(ids))
         .delete(synchronize_session=False))
        (db.query(MessageReference)
         .filter(MessageReference.message_id.in_(ids))
         .delete(synchronize_session=False))
        (db.query(Message)
         .filter(Message.conversation_id == conversation_id)
         .delete(synchronize_session=False))
    (db.query(Conversation)
     .filter(Conversation.conversation_id == conversation_id)
     .delete(synchronize_session=False))
    db.commit()


@router.post("/message/{message_id}/avis", status_code=status.HTTP_204_NO_CONTENT)
def donner_un_avis(
    message_id: int,
    avis: AvisIn,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(get_current_user),
):
    """
    Dire si une réponse a été utile.

    C'est le seul canal d'évaluation qui vienne de vrais usagers plutôt que
    d'un jeu de test écrit à l'avance. Les réponses jugées inutiles sont les
    meilleures candidates à l'enrichissement de ce jeu.
    """
    message = db.query(Message).filter(Message.message_id == message_id).first()
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message introuvable")
    _conversation(db, utilisateur, message.conversation_id)   # propriétaire
    if message.role != "assistant":
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "On ne donne un avis que sur une réponse")

    db.add(MessageFeedback(message_id=message_id,
                           utilisateur_id=utilisateur.utilisateur_id,
                           utile=avis.utile,
                           commentaire=(avis.commentaire or "").strip() or None))
    db.commit()
