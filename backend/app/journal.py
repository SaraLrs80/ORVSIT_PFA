from .models import JournalUsage

def journaliser(db, utilisateur_id, action, cible=None):
    """Ajoute une ligne au journal d'usage (le commit est fait par l'appelant)."""
    db.add(JournalUsage(utilisateur_id=utilisateur_id, action=action, cible=cible))