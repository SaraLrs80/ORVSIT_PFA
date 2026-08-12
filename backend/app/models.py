from sqlalchemy import (Column, BigInteger, Boolean, Integer, String, DateTime,
                        Text)
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy.dialects.postgresql import JSONB 

class Utilisateur(Base):
    __tablename__ = "utilisateur"

    utilisateur_id = Column(BigInteger, primary_key=True)
    nom_complet = Column(String(160), nullable=False)
    email = Column(String(190), unique=True, nullable=False)
    mot_de_passe_hash = Column(String(255), nullable=False)
    role = Column(String, nullable=False, default="utilisateur")
    organisation = Column(String(160))
    statut = Column(String, nullable=False, default="actif")
    date_creation = Column(DateTime(timezone=True), server_default=func.now()) #c'est la base qui gere l'heure
    derniere_connexion = Column(DateTime(timezone=True))
    
class DemandeAcces(Base):
    __tablename__ = "demande_acces"

    demande_id      = Column(BigInteger, primary_key=True)
    nom_complet     = Column(String(160), nullable=False)
    email           = Column(String(190), nullable=False)   # pas unique : on peut redemander
    organisation    = Column(String(160))
    profil_souhaite = Column(String, nullable=False, default="utilisateur")
    motif           = Column(Text)
    statut          = Column(String, nullable=False, default="en_attente")
    date_demande    = Column(DateTime(timezone=True), server_default=func.now())

    # Remplis plus tard par l'admin lors du traitement (nullable pour l'instant)
    traite_par       = Column(BigInteger)
    date_traitement  = Column(DateTime(timezone=True))
    utilisateur_cree = Column(BigInteger)
    
class JournalUsage(Base):
    __tablename__ = "journal_usage"

    evenement_id   = Column(BigInteger, primary_key=True)
    utilisateur_id = Column(BigInteger)              # référence vers utilisateur
    action         = Column(String(80), nullable=False)
    cible          = Column(String(160))
    details        = Column(JSONB)
    date_evenement = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    """Un fil de discussion avec l'assistant.

    Aucune colonne d'état ici — ni dernier territoire, ni dernier indicateur.
    Ces informations se lisent dans les MessageReference du dernier message de
    l'assistant. Les recopier créerait deux vérités qui finiraient par se
    contredire.
    """
    __tablename__ = "conversation"

    conversation_id = Column(BigInteger, primary_key=True)
    utilisateur_id  = Column(BigInteger, nullable=False)
    titre           = Column(String(200))
    date_creation   = Column(DateTime(timezone=True), server_default=func.now())
    date_maj        = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    """Un message du fil : une question OU une réponse.

    `role` vaut « user », « assistant » ou « system ». C'est le type
    `role_message` — sans rapport avec `utilisateur.role`, qui dit les droits
    de la personne. Deux colonnes du même nom, deux notions différentes.

    Les quatre dernières colonnes sont la trace du moteur, ajoutées à côté de
    `modele` et `tokens` qui sont déjà des métadonnées de génération.
    """
    __tablename__ = "message"

    message_id      = Column(BigInteger, primary_key=True)
    conversation_id = Column(BigInteger, nullable=False)
    role            = Column(String, nullable=False)
    contenu         = Column(Text, nullable=False)
    modele          = Column(String(80))
    tokens          = Column(Integer)
    date_envoi      = Column(DateTime(timezone=True), server_default=func.now())

    branche         = Column(String(20))
    refus           = Column(String(30))
    reformulation   = Column(String(80))
    duree_ms        = Column(Integer)


class MessageReference(Base):
    """Ce qu'une réponse cite : un indicateur, un territoire.

    C'est la traçabilité par construction. Une réponse sans référence est une
    réponse sans source — et cela se voit dans la base, pas seulement à
    l'écran.
    """
    __tablename__ = "message_reference"

    reference_id = Column(BigInteger, primary_key=True)
    message_id   = Column(BigInteger, nullable=False)
    type_entite  = Column(String(40), nullable=False)   # indicateur | territoire
    entite_id    = Column(BigInteger, nullable=False)
    libelle      = Column(String(200))


class MessageFeedback(Base):
    """L'avis de l'utilisateur sur une réponse.

    Le seul canal d'évaluation qui vienne de vrais usagers plutôt que d'un jeu
    de test écrit à l'avance. Les réponses jugées inutiles sont les meilleures
    candidates à l'enrichissement du jeu d'évaluation.
    """
    __tablename__ = "message_feedback"

    feedback_id    = Column(BigInteger, primary_key=True)
    message_id     = Column(BigInteger, nullable=False)
    utilisateur_id = Column(BigInteger)
    utile          = Column(Boolean)
    commentaire    = Column(Text)
    date_feedback  = Column(DateTime(timezone=True), server_default=func.now())