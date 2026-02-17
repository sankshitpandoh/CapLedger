import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional, get_db_session
from app.core.config import get_settings
from app.models import Employee, User, UserRole
from app.schemas import AuthSession, AuthUser

try:
    from authlib.integrations.starlette_client import OAuth
except ImportError:  # pragma: no cover
    OAuth = None


router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger(__name__)
oauth_google_client = None


def _get_oauth_client():
    global oauth_google_client

    if OAuth is None:
        raise HTTPException(status_code=503, detail="Google SSO is not available: authlib is not installed")

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google SSO is not configured")

    if oauth_google_client is None:
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
            timeout=45.0,
        )
        oauth_google_client = oauth.google

    return oauth_google_client


def _is_org_email(email: str, hd_claim: str | None) -> bool:
    if not settings.google_org_domain:
        return True
    domain = settings.google_org_domain.strip().lower()
    if not domain:
        return True

    if hd_claim and hd_claim.strip().lower() == domain:
        return True

    return email.lower().endswith(f"@{domain}")


def _determine_role(db: Session, email: str, existing_user: User | None) -> UserRole:
    email_lower = email.lower()
    if existing_user is not None:
        if email_lower in settings.admin_email_list:
            return UserRole.ADMIN
        return existing_user.role

    if email_lower in settings.admin_email_list:
        return UserRole.ADMIN

    return UserRole.EMPLOYEE


@router.get("/login")
async def login(request: Request):
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Auth is disabled")

    google = _get_oauth_client()
    redirect_uri = request.url_for("auth_callback")
    return await google.authorize_redirect(request, redirect_uri, prompt="select_account")


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db_session)):
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Auth is disabled")

    google = _get_oauth_client()
    try:
        token = await google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if userinfo is None:
            userinfo = await google.parse_id_token(request, token)
    except httpx.TimeoutException as exc:
        logger.exception("Google OAuth callback timed out during token exchange")
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth network timeout. Ensure this server can reach "
                "accounts.google.com and oauth2.googleapis.com. "
                "If your network requires a proxy, set HTTPS_PROXY/HTTP_PROXY before starting the app."
            ),
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Google OAuth callback HTTP error")
        raise HTTPException(status_code=503, detail="Google OAuth request failed due to a network error") from exc

    if not userinfo:
        raise HTTPException(status_code=400, detail="Unable to read user profile from Google")

    email = str(userinfo.get("email", "")).strip().lower()
    full_name = str(userinfo.get("name", "")).strip() or email
    google_sub = str(userinfo.get("sub", "")).strip()
    hd_claim = userinfo.get("hd")

    if not email or not google_sub:
        raise HTTPException(status_code=400, detail="Google profile is missing required identity fields")

    if not _is_org_email(email, hd_claim):
        raise HTTPException(status_code=403, detail="Only organization users are allowed")

    user = db.scalar(select(User).where(User.email == email).limit(1))
    role = _determine_role(db, email, user)

    if user is None:
        user = User(email=email, full_name=full_name, google_sub=google_sub, role=role)
        db.add(user)
    else:
        user.full_name = full_name
        user.google_sub = google_sub
        user.role = role

    matching_employee = db.scalar(select(Employee).where(Employee.email == email).limit(1))
    if matching_employee is not None:
        user.employee_id = matching_employee.id

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session.clear()
    request.session["user_id"] = user.id

    return RedirectResponse(url="/", status_code=302)


@router.post("/logout")
def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=AuthSession)
def me(current_user: User | None = Depends(get_current_user_optional)) -> AuthSession:
    if current_user is None:
        return AuthSession(authenticated=False, user=None)

    return AuthSession(
        authenticated=True,
        user=AuthUser(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            employee_id=current_user.employee_id,
        ),
    )


@router.get("/require", response_model=AuthUser)
def require_user(current_user: User = Depends(get_current_user)) -> AuthUser:
    return AuthUser(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        employee_id=current_user.employee_id,
    )
