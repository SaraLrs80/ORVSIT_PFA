"""
Configuration de l'application.

On lit les réglages depuis le fichier .env situé à la RACINE du projet
(PROJET_PFA/.env), pour ne pas dupliquer les identifiants. pydantic-settings
se charge de lire le fichier et de convertir les valeurs (ex: DB_PORT en entier).
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# __file__ = .../backend/app/config.py
# parents[0]=app, parents[1]=backend, parents[2]=PROJET_PFA (la racine)
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # --- Base de données ---
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    # Base applicative (utilisateurs, demandes d'accès, assistant IA).
    # Distincte du data warehouse dwh_orvsit.
    APP_DB_NAME: str = "orvsit_app"

    # --- JWT (jetons d'authentification) ---
    # JWT_SECRET : la clé secrète qui signe les jetons. À garder confidentielle.
    JWT_SECRET: str = "dev-secret-a-changer"
    JWT_ALGORITHM: str = "HS256"
    # Durée de validité d'un jeton, en minutes (480 = 8 h).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # --- E-mail (SMTP) ---
    # Si SMTP_HOST est vide, on reste en mode "console" (affichage du mail).
    # Renseigne ces valeurs dans le .env pour envoyer de vrais e-mails.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""   # expéditeur affiché ; à défaut on utilise SMTP_USER

    # On indique où trouver le .env ; extra="ignore" = on tolère d'autres
    # variables dans le .env (ex: DB_NAME du data warehouse) sans erreur.
    model_config = SettingsConfigDict(env_file=str(ROOT_ENV), extra="ignore")

    @property
    def database_url(self) -> str:
        """Adresse de connexion SQLAlchemy vers la base applicative."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.APP_DB_NAME}"
        )


    DB_NAME:str = "dwh_orvsitt"  # nom de la base de données du data warehouse (distincte de APP_DB_NAME)
    
    @property
    def warehouse_url(self)-> str:
        """Adresse de connexion SQLAlchemy vers le data warehouse."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
# Un seul objet « settings » réutilisé partout dans l'application.
settings = Settings()
