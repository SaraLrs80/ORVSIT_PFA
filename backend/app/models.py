from sqlalchemy import Column, BigInteger, String, DateTime, Text
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy.dialects.postgresql import JSONB 

class Utilisateur(Base):
    __tablename__ = "utilisateur"

    utilisateur_id = Column(BigInteger, primary_key=True)
    nom_complet = Column(String(160), nullable=False)
    email = Column(String(190), unique=True, nullable=False)
    mot_de_passe_hash = Column(String(255), nullable=False)
    role = Column(String, nullable=False, default="analyste")
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
    profil_souhaite = Column(String, nullable=False, default="analyste")
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