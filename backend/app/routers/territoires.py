from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_dwh
from ..deps import get_current_user   # réservé aux utilisateurs connectés

router = APIRouter(prefix="/territoires", tags=["territoires"])

@router.get("")
def lister_territoires(dwh: Session = Depends(get_dwh), user=Depends(get_current_user)):
    lignes = dwh.execute(text("""
        SELECT territoire_id, nom, niveau
        FROM referential.dim_territoire
        WHERE niveau = 'prefecture_province'
        ORDER BY nom
    """)).mappings().all()
    return [dict(l) for l in lignes]