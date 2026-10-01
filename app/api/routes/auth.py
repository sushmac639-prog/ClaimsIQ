from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.user import UserRead
router = APIRouter(prefix="/auth", tags=["Authentication"])
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
        user = db.get(User, int(payload["sub"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or unavailable")
    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))
@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
