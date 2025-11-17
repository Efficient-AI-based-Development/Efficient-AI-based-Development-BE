import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.domain.auth import (
    create_access_token,
    create_refresh_token,
    exchange_code_for_token,
    get_current_user,
    get_google_userinfo,
    get_or_create_user_from_google,
)
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def get_me(current_user: str = Depends(get_current_user)):
    return {"user_id": current_user}


@router.get("/login/google")
def google_login():
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    google_client_id = settings.google_client_id
    google_redirect_uri = settings.google_redirect_uri
    params = {
        "client_id": google_client_id,
        "redirect_uri": google_redirect_uri,
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
