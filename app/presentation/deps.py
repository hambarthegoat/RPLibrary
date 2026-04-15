from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.entities import User
from app.infrastructure.database import get_db
from app.infrastructure.repositories import (
    SqlAlchemyBookRepository,
    SqlAlchemyBorrowingRepository,
    SqlAlchemyTagRepository,
    SqlAlchemyUserRepository,
)
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

def get_user_repo(db: Annotated[Session, Depends(get_db)]) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


def get_tag_repo(db: Annotated[Session, Depends(get_db)]) -> SqlAlchemyTagRepository:
    return SqlAlchemyTagRepository(db)


def get_book_repo(db: Annotated[Session, Depends(get_db)]) -> SqlAlchemyBookRepository:
    return SqlAlchemyBookRepository(db)


def get_borrowing_repo(
    db: Annotated[Session, Depends(get_db)]
) -> SqlAlchemyBorrowingRepository:
    return SqlAlchemyBorrowingRepository(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: Annotated[SqlAlchemyUserRepository, Depends(get_user_repo)],
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

    user = user_repo.get_by_id(int(user_id))
    if user is None:
        raise credentials_error
    return user

def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Akses admin dibutuhkan")
    return current_user
