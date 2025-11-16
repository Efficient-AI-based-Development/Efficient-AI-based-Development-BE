import httpx
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from fastapi import HTTPException, Depends
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError

from app.db.database import get_db


BACKEND_BASE_URL = "http://localhsot:8000"
SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(
    schemes=["bcrypt"],
)

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

def get_current_user(token: str = Depends(oauth2_scheme), db : Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).(User.id == user_id).one_or_none()
        if user is None:
            raise HTTPException(401, "User not found")
        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def exchange_code_for_token(code: str) -> dict:
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
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
    google_id = userinfo["sub"]
    email = userinfo.get("email")
    name = userinfo.get("name", "NoName")

    social_id = f"google_{google_id}"

    user = db.query(User).filter(User.user_id == social_id).one_or_none()
    if user:
        return user

    # 처음 로그인 → 자동 회원가입
    user = User(
        user_id=social_id,  # PK
        email=email,
        display_name=name,
        password_hash="",  # 소셜 로그인은 비밀번호 필요 없음
        created_at=datetime.utcnow(),  # 있으면
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
