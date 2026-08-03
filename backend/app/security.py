import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from .config import settings

def hash_password(password: str) -> str:
    # Générer un sel aléatoire
    salt = bcrypt.gensalt()
    # Hasher le mot de passe avec le sel
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8') #on decode les octets en texte pour le stocker dans la base de données

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Vérifier le mot de passe en comparant le mot de passe en clair avec le hash stocké
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.InvalidTokenError:   # couvre aussi l'expiration (elle en hérite)
        return None