import urllib.parse

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from fastapi.responses import RedirectResponse

from app.domain.auth import get_current_user, get_or_create_user_from_google, \
    get_google_userinfo, exchange_code_for_token, create_access_token, create_refresh_token
from app.schemas.auth import TokenPair
from fastapi import HTTPException

router = APIRouter(prefix="/auth", tags=["auth"])

# GOOGLE_CLIENT_ID=발급받은값
# GOOGLE_CLIENT_SECRET=발급받은값
# GOOGLE_REDIRECT_URI=http://<고정IP>:8000/auth/google/callback

def get_me(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user}

@router.get("/google/login")
def google_login():
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@router.get("/login/google/callback", response_model=TokenPair)
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