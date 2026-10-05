from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.models import RevokedToken, User
from app.db.session import get_db
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _is_revoked(db: Session, jti: str | None) -> bool:
    if not jti:
        return False
    return db.scalar(select(RevokedToken.id).where(RevokedToken.jti == jti)) is not None


def _revoke_token(db: Session, payload: dict, user_id: int) -> None:
    jti = payload.get("jti")
    exp = payload.get("exp")
    token_type = payload.get("type")
    if not jti or not exp or not token_type:
        return
    if _is_revoked(db, jti):
        return
    expires_at = datetime.fromtimestamp(float(exp), tz=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return
    db.add(RevokedToken(jti=jti, token_type=token_type, user_id=user_id, expires_at=expires_at))


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/refresh", response_model=TokenPair)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
        if _is_revoked(db, payload.get("jti")):
            raise ValueError("Refresh token has been revoked")
        user = db.get(User, int(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or unavailable")

    # Rotate the refresh token so a used token cannot be replayed.
    _revoke_token(db, payload, user.id)
    subject = str(user.id)
    result = TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))
    db.commit()
    return result


@router.post("/logout")
def logout(
    body: LogoutRequest | None = None,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        access_payload = decode_token(token, "access")
        user_id = int(access_payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    _revoke_token(db, access_payload, user_id)

    if body and body.refresh_token:
        try:
            refresh_payload = decode_token(body.refresh_token, "refresh")
            if int(refresh_payload["sub"]) == user_id:
                _revoke_token(db, refresh_payload, user_id)
        except (ValueError, TypeError, KeyError):
            # Logout remains idempotent even when an old/expired refresh token is supplied.
            pass

    db.commit()
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
