import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.domain.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    exchange_code_for_token,
    get_google_userinfo,
    get_or_create_user_from_google,
)
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login/google")
def google_login():
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    import os

    # 환경에 따라 자동으로 설정
    environment = os.getenv("ENVIRONMENT", "development")  # "development" 또는 "production"

    if environment == "production":
        frontend_url = "https://atrina.vercel.app/document/setting1"
    else:
        frontend_url = "http://localhost:5173/document/setting1"  # 개발 환경

    google_client_id = settings.google_client_id
    # google_redirect_uri = settings.google_redirect_uri
    params = {
        "client_id": google_client_id,
        "redirect_uri": frontend_url,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return {"url": url}


refresh_scheme = HTTPBearer(auto_error=True)


@router.post("/refresh", response_model=TokenPair)
def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(refresh_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")

    if user_id is None or token_type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    user = db.query(User).filter(User.user_id == user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 새 토큰 생성
    user_id = user.user_id
    access_jwt = create_access_token(user_id)
    refresh_jwt = create_refresh_token(user_id)

    return TokenPair(access_token=access_jwt, refresh_token=refresh_jwt)


@router.post("/login/google/exchange", response_model=TokenPair)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "code가 없습니다.")

    token_data = await exchange_code_for_token(code)
    access_token = token_data.get("access_token")

    userinfo = await get_google_userinfo(access_token)
    user = get_or_create_user_from_google(userinfo, db)

    payload = user.user_id

    access_jwt = create_access_token(payload)
    refresh_jwt = create_refresh_token(payload)

    return TokenPair(
        access_token=access_jwt,
        refresh_token=refresh_jwt,
        token_type="bearer",
    )
