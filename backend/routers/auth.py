"""
routers/auth.py — Google OAuth 2.0 flow.
POST /auth/google/callback → creates session, stores encrypted refresh token.
"""
import logging
import os
from typing import Annotated

# Allow HTTP and relaxed token scopes for OAuth in local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_db
from models import User
from services.auth import create_access_token
from services.crypto import encrypt_token
from routers.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_flow() -> Flow:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    flow.autogenerate_code_verifier = False
    return flow


@router.get("/google")
async def google_login():
    """Redirect user to Google consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange authorization code for tokens; upsert user; set session cookie."""
    flow = _build_flow()
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error("Token exchange failed: %s", e)
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {str(e)}")

    creds = flow.credentials

    # Fetch user info from Google
    async with httpx.AsyncClient() as client:
        user_info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
        )
    if user_info_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    user_info = user_info_resp.json()
    google_sub = user_info["id"]

    # Upsert user
    stmt = select(User).where(User.google_sub == google_sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_sub=google_sub,
            email=user_info.get("email", ""),
            display_name=user_info.get("name"),
            picture_url=user_info.get("picture"),
        )
        db.add(user)

    user.email = user_info.get("email", user.email)
    user.display_name = user_info.get("name", user.display_name)
    user.picture_url = user_info.get("picture", user.picture_url)

    if creds.refresh_token:
        user.refresh_token_encrypted = encrypt_token(creds.refresh_token)

    await db.commit()
    await db.refresh(user)

    # Issue session JWT as httpOnly cookie
    token = create_access_token(str(user.id))
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/?logged_in=true", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # set True in production with HTTPS
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me")
async def me(current_user: Annotated[User, Depends(get_current_user)]):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "display_name": current_user.display_name,
        "picture_url": current_user.picture_url,
    }
