from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

from app.domain.auth import login_service, get_current_user
from app.schemas.auth import TokenPair, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenPair)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    return login_service(request, db)

def get_me(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user}

