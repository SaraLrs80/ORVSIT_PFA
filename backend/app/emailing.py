"""
Envoi d'e-mails.

Deux modes, choisis automatiquement :
  - MODE CONSOLE (par défaut, dev) : si SMTP_HOST est vide dans le .env, on affiche
    simplement l'e-mail dans la console. Pratique pour tester sans configurer SMTP.
  - MODE RÉEL : si les réglages SMTP sont renseignés, on envoie un vrai e-mail.

Le reste de l'application appelle toujours envoyer_email(...) sans se soucier du mode.
"""

import smtplib
from email.message import EmailMessage

from .config import settings


def envoyer_email(destinataire: str, sujet: str, corps: str) -> None:
    # --- Mode console (aucun serveur SMTP configuré) ---
    if not settings.SMTP_HOST:
        print("=" * 64)
        print("[E-MAIL simulé]")
        print(f"À      : {destinataire}")
        print(f"Sujet  : {sujet}")
        print("-" * 64)
        print(corps)
        print("=" * 64)
        return

    # --- Mode réel (envoi SMTP) ---
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(corps)

    # smtplib.SMTP ouvre la connexion ; starttls() la chiffre (port 587).
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as serveur:
        serveur.starttls()
        serveur.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        serveur.send_message(message)
