from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class User:
    id: int | None
    name: str
    email: str
    role: str = "user"
    password_hash: str = ""
    avatar_image: bytes | None = None
    avatar_content_type: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class Tag:
    id: int | None
    name: str


@dataclass(slots=True)
class Book:
    id: int | None
    title: str
    author: str
    description: str
    stock_total: int
    stock_available: int
    cover_image: bytes | None = None
    cover_content_type: str | None = None
    created_at: datetime | None = None
    tags: list[Tag] = field(default_factory=list)


@dataclass(slots=True)
class BorrowTransaction:
    id: int | None
    user_id: int
    book_id: int
    status: str
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    processed_by_admin_id: int | None = None
