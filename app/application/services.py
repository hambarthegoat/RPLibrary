from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas import BookResponse, BookUpdateRequest, TagResponse, UserResponse
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.infrastructure.models import Book, BorrowTransaction, Tag, User


def _extract_image(upload_file: UploadFile) -> tuple[bytes, str]:
    content_type = upload_file.content_type
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File harus berupa gambar")
    content = upload_file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File gambar kosong")
    return content, content_type


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar_url=f"/users/{user.id}/avatar" if user.avatar_image else None,
    )


def register_user(db: Session, name: str, email: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin" if settings.default_admin_email and email == settings.default_admin_email else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email / password salah")
    return user


def upload_user_avatar(db: Session, current_user: User, upload_file: UploadFile) -> User:
    image, content_type = _extract_image(upload_file)
    current_user.avatar_image = image
    current_user.avatar_content_type = content_type
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


def parse_or_create_tags(db: Session, tag_csv: str | None) -> list[Tag]:
    if not tag_csv:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in tag_csv.split(","):
        name = raw_name.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    if not names:
        return []
    existing = db.scalars(select(Tag).where(Tag.name.in_(names))).all()
    existing_map = {tag.name: tag for tag in existing}
    result: list[Tag] = []
    for name in names:
        if name in existing_map:
            result.append(existing_map[name])
            continue
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
        result.append(tag)
    return result


def book_to_response(book: Book) -> BookResponse:
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        description=book.description,
        stock_total=book.stock_total,
        stock_available=book.stock_available,
        cover_url=f"/books/{book.id}/cover" if book.cover_image else None,
        tags=[TagResponse.model_validate(tag) for tag in book.tags],
    )


def create_tag(db: Session, name: str) -> Tag:
    existing = db.scalar(select(Tag).where(Tag.name == name))
    if existing:
        raise HTTPException(status_code=400, detail="Tag sudah ada")
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, name: str) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag tidak ditemukan")
    tag.name = name
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag tidak ditemukan")
    db.delete(tag)
    db.commit()


def create_book(
    db: Session,
    title: str,
    author: str,
    description: str,
    stock_total: int,
    tag_names: str | None,
    cover_file: UploadFile | None,
) -> Book:
    book = Book(
        title=title,
        author=author,
        description=description,
        stock_total=stock_total,
        stock_available=stock_total,
    )
    book.tags = parse_or_create_tags(db, tag_names)
    if cover_file:
        image, content_type = _extract_image(cover_file)
        book.cover_image = image
        book.cover_content_type = content_type
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def list_books(db: Session, q: str | None, tag: str | None, available_only: bool) -> list[Book]:
    query = select(Book).order_by(Book.title)
    if q:
        query = query.where((Book.title.ilike(f"%{q}%")) | (Book.author.ilike(f"%{q}%")))
    if available_only:
        query = query.where(Book.stock_available > 0)
    books = list(db.scalars(query).all())
    if tag:
        books = [book for book in books if any(t.name == tag for t in book.tags)]
    return books


def get_book_by_id(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return book


def update_book(db: Session, book_id: int, payload: BookUpdateRequest) -> Book:
    book = get_book_by_id(db, book_id)
    if payload.title is not None:
        book.title = payload.title
    if payload.author is not None:
        book.author = payload.author
    if payload.description is not None:
        book.description = payload.description
    if payload.stock_total is not None:
        borrowed_count = book.stock_total - book.stock_available
        if payload.stock_total < borrowed_count:
            raise HTTPException(status_code=400, detail="Stock total lebih kecil dari buku yang sedang dipinjam")
        book.stock_total = payload.stock_total
        book.stock_available = payload.stock_total - borrowed_count
    if payload.tag_names is not None:
        book.tags = parse_or_create_tags(db, ",".join(payload.tag_names))
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def upload_book_cover(db: Session, book_id: int, cover_file: UploadFile) -> Book:
    book = get_book_by_id(db, book_id)
    image, content_type = _extract_image(cover_file)
    book.cover_image = image
    book.cover_content_type = content_type
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book_by_id(db, book_id)
    db.delete(book)
    db.commit()


def borrow_book(db: Session, current_user: User, book_id: int, days: int) -> BorrowTransaction:
    book = get_book_by_id(db, book_id)
    if book.stock_available <= 0:
        raise HTTPException(status_code=400, detail="Buku sedang tidak tersedia")
    borrowing = BorrowTransaction(
        user_id=current_user.id,
        book_id=book.id,
        status="borrowed",
        due_date=datetime.now(timezone.utc) + timedelta(days=days),
    )
    book.stock_available -= 1
    db.add(borrowing)
    db.add(book)
    db.commit()
    db.refresh(borrowing)
    return borrowing


def list_user_borrowings(db: Session, current_user: User) -> list[BorrowTransaction]:
    return list(
        db.scalars(
            select(BorrowTransaction)
            .where(BorrowTransaction.user_id == current_user.id)
            .order_by(BorrowTransaction.borrowed_at.desc())
        ).all()
    )


def request_return(db: Session, current_user: User, borrowing_id: int) -> BorrowTransaction:
    borrowing = db.get(BorrowTransaction, borrowing_id)
    if borrowing is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    if borrowing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bukan peminjaman milik Anda")
    if borrowing.status == "returned":
        raise HTTPException(status_code=400, detail="Buku sudah dikembalikan")
    borrowing.status = "return_requested"
    db.add(borrowing)
    db.commit()
    db.refresh(borrowing)
    return borrowing


def list_return_requests(db: Session) -> list[BorrowTransaction]:
    return list(
        db.scalars(
            select(BorrowTransaction)
            .where(BorrowTransaction.status == "return_requested")
            .order_by(BorrowTransaction.borrowed_at.asc())
        ).all()
    )


def confirm_return(db: Session, current_admin: User, borrowing_id: int) -> BorrowTransaction:
    borrowing = db.get(BorrowTransaction, borrowing_id)
    if borrowing is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    if borrowing.status == "returned":
        raise HTTPException(status_code=400, detail="Buku sudah dikonfirmasi kembali")
    if borrowing.status not in {"borrowed", "return_requested"}:
        raise HTTPException(status_code=400, detail="Status peminjaman tidak valid")

    book = get_book_by_id(db, borrowing.book_id)
    borrowing.status = "returned"
    borrowing.returned_at = datetime.now(timezone.utc)
    borrowing.processed_by_admin_id = current_admin.id
    book.stock_available = min(book.stock_total, book.stock_available + 1)
    db.add(borrowing)
    db.add(book)
    db.commit()
    db.refresh(borrowing)
    return borrowing
