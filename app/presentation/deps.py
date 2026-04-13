from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.infrastructure.database import get_db
from app.infrastructure.models import User

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_error

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except jwt.InvalidTokenError as exc:
        raise credentials_error from exc

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_error
    return user

def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses admin dibutuhkan")
    return current_user

