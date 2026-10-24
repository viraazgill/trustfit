"""bcrypt passwords and JWTs with roles admin > analyst > viewer."""
import datetime as dt
from collections.abc import Callable
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db import DbSession
from app.errors import ApiError
from app.models import User
from app.settings import settings

ROLE_RANK = {"viewer": 0, "analyst": 1, "admin": 2}
JWT_ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user: User, lifetime: dt.timedelta | None = None) -> str:
    expires = dt.datetime.now(dt.UTC) + (lifetime or dt.timedelta(hours=settings.JWT_EXPIRE_HOURS))
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": expires},
                      settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
                 db: DbSession) -> User:
    if creds is None:
        raise ApiError(401, "Sign in first")
    try:
        claims = jwt.decode(creds.credentials, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ApiError(401, "Invalid or expired token") from exc
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise ApiError(401, "Unknown user")
    return user


def require(role: str) -> Callable[..., User]:
    """Dependency: the signed-in user must have `role` or a higher one."""
    def check(user: CurrentUser) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[role]:
            raise ApiError(403, f"Needs the {role} role")
        return user
    return check


CurrentUser = Annotated[User, Depends(current_user)]
viewer = require("viewer")
analyst = require("analyst")
admin = require("admin")
AnalystUser = Annotated[User, Depends(analyst)]
AdminUser = Annotated[User, Depends(admin)]
