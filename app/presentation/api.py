from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import services
from app.application.schemas import (
    BookResponse,
    BookUpdateRequest,
    BorrowRequest,
    BorrowResponse,
    LoginRequest,
    RegisterRequest,
    TagCreateRequest,
    TagResponse,
    TokenResponse,
    UserResponse,
)
from app.core.security import create_access_token
from app.infrastructure.database import get_db
from app.infrastructure.models import Book, Tag, User
from app.presentation.deps import get_current_user, require_admin

app = FastAPI(
    title="RPLibrary API",
    description="API sederhana untuk manajemen perpustakaan RPL",
    version="0.1.0",
)

@app.get("/")
def root():
    return {"message": "RPLibrary is UP!"}

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return services.user_to_response(
        services.register_user(db, payload.name, payload.email, payload.password)
    )

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, payload.email, payload.password)
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)

@app.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return services.user_to_response(current_user)

@app.post("/users/me/avatar", response_model=UserResponse)
def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.user_to_response(services.upload_user_avatar(db, current_user, avatar))

@app.get("/users/{user_id}/avatar")
def get_user_avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or user.avatar_image is None or user.avatar_content_type is None:
        raise HTTPException(status_code=404, detail="Avatar tidak ditemukan")
    return Response(content=user.avatar_image, media_type=user.avatar_content_type)

@app.post("/tags", response_model=TagResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_tag(payload: TagCreateRequest, db: Session = Depends(get_db)):
    return services.create_tag(db, payload.name)

@app.get("/tags", response_model=list[TagResponse])
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()

@app.put("/tags/{tag_id}", response_model=TagResponse, dependencies=[Depends(require_admin)])
def update_tag(tag_id: int, payload: TagCreateRequest, db: Session = Depends(get_db)):
    return services.update_tag(db, tag_id, payload.name)

@app.delete("/tags/{tag_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    services.delete_tag(db, tag_id)

@app.post("/books", response_model=BookResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_book(
    title: str = Form(...),
    author: str = Form(...),
    description: str = Form(""),
    stock_total: int = Form(..., ge=0),
    tag_names: str | None = Form(None),
    cover: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    return services.book_to_response(
        services.create_book(db, title, author, description, stock_total, tag_names, cover)
    )

@app.get("/books", response_model=list[BookResponse])
def list_books(
    q: str | None = None,
    tag: str | None = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    return [services.book_to_response(book) for book in services.list_books(db, q, tag, available_only)]

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return services.book_to_response(services.get_book_by_id(db, book_id))

@app.put("/books/{book_id}", response_model=BookResponse, dependencies=[Depends(require_admin)])
def update_book(book_id: int, payload: BookUpdateRequest, db: Session = Depends(get_db)):
    return services.book_to_response(services.update_book(db, book_id, payload))


@app.post("/books/{book_id}/cover", response_model=BookResponse, dependencies=[Depends(require_admin)])
def upload_book_cover(book_id: int, cover: UploadFile = File(...), db: Session = Depends(get_db)):
    return services.book_to_response(services.upload_book_cover(db, book_id, cover))

@app.get("/books/{book_id}/cover")
def get_book_cover(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None or book.cover_image is None or book.cover_content_type is None:
        raise HTTPException(status_code=404, detail="Cover buku tidak ditemukan")
    return Response(content=book.cover_image, media_type=book.cover_content_type)

@app.delete("/books/{book_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    services.delete_book(db, book_id)

@app.post("/books/{book_id}/borrow", response_model=BorrowResponse)
def borrow_book(
    book_id: int,
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.borrow_book(db, current_user, book_id, payload.days)

@app.get("/borrowings/me", response_model=list[BorrowResponse])
def my_borrowings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return services.list_user_borrowings(db, current_user)

@app.post("/borrowings/{borrowing_id}/return-request", response_model=BorrowResponse)
def request_return(
    borrowing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return services.request_return(db, current_user, borrowing_id)

@app.get(
    "/admin/borrowings/return-requests",
    response_model=list[BorrowResponse],
    dependencies=[Depends(require_admin)],
)
def list_return_requests(db: Session = Depends(get_db)):
    return services.list_return_requests(db)

@app.post(
    "/admin/borrowings/{borrowing_id}/confirm-return",
    response_model=BorrowResponse,
    dependencies=[Depends(require_admin)],
)
def confirm_return(
    borrowing_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    return services.confirm_return(db, current_admin, borrowing_id)
