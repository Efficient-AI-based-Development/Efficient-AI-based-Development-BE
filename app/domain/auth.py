from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import SocialAccount, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(
    schemes=["bcrypt"],
)

google_client_id = settings.google_client_id
google_client_secret = settings.google_client_secret
google_redirect_uri = settings.google_redirect_uri
BACKEND_BASE_URL = settings.BACKEND_BASE_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def create_access_token(user_id: str) -> str:
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(user_id, "access", expires)


def create_refresh_token(user_id: str) -> str:
    expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(user_id, "refresh", expires)


def create_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,  # 토큰 주인
        "type": token_type,  # access / refresh
        "iat": now,  # 생성 시간
        "exp": now + expires_delta,  # 만료 시간
    }

    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.user_id == user_id).one_or_none()
        if user is None:
            raise HTTPException(401, "User not found")
        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def exchange_code_for_token(code: str) -> dict:
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, data=data)
        if res.status_code != 200:
            print("Token error:", res.text)
            raise HTTPException(400, "구글 토큰 발급 실패")

        return res.json()


async def get_google_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if res.status_code != 200:
            print("Userinfo error:", res.text)
            raise HTTPException(400, "구글 유저 정보 조회 실패")
        return res.json()


def get_or_create_user_from_google(userinfo: dict, db: Session) -> User:
    provider = "google"
    provider_user_id = userinfo["sub"]
    email = userinfo.get("email")
    name = userinfo.get("name", "NoName")

    social = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.provider == provider,
            SocialAccount.provider_user_id == provider_user_id,
        )
        .one_or_none()
    )
    if social:
        return social.user

    user = None
    if email:
        user = db.query(User).filter(User.email == email).one_or_none()

    if not user:
        user = User(
            user_id=str(uuid4()),
            email=email,
            display_name=name,
            password_hash="",
        )
        db.add(user)
        db.flush()

    social = SocialAccount(
        user_id=user.user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
    )
    db.add(social)
    db.commit()
    db.refresh(user)

    return user
