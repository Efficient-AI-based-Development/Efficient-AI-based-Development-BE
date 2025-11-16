from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta, datetime, timezone
from jose import jwt
from app.schemas.auth import TokenPair, LoginRequest

SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(
    schemes=["bcrypt"],
)

def login_service(request: LoginRequest, db: Session) -> TokenPair:
    user = (
        db.query(User)
        .filter(User.id == request.user_id)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
        )

    if not verify_password(request.user_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    # 3) access / refresh token 생성
    access_token = create_access_token(user_id=user.id)
    refresh_token = create_refresh_token(user_id=user.id)

    # 4) 응답
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_pw: str, hashed_pw: str):
    return pwd_context.verify(plain_pw, hashed_pw)

def create_access_token(user_id: str) -> str:
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(user_id, "access", expires)


def create_refresh_token(user_id: str) -> str:
    expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(user_id, "refresh", expires)

def create_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,          # 토큰 주인
        "type": token_type,      # access / refresh
        "iat": now,              # 생성 시간
        "exp": now + expires_delta,    # 만료 시간
    }

    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
