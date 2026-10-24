from fastapi import APIRouter
from sqlalchemy import select

from app.auth import CurrentUser, create_token, verify_password
from app.db import DbSession
from app.errors import ApiError
from app.models import User
from app.schemas import LoginIn, MeOut, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: DbSession) -> TokenOut:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "Wrong email or password")
    return TokenOut(access_token=create_token(user), role=user.role)


@router.get("/me")
def me(user: CurrentUser) -> MeOut:
    return MeOut(id=user.id, email=user.email, role=user.role)
