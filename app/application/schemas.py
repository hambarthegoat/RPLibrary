from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    avatar_url: str | None = None

class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class BookUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    stock_total: int | None = Field(default=None, ge=0)
    tag_names: list[str] | None = None

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: str
    stock_total: int
    stock_available: int
    cover_url: str | None
    tags: list[TagResponse]

class BorrowRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=30)

class BorrowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    book_id: int
    user_id: int
