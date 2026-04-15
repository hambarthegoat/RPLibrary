from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile

from app.application.schemas import BookResponse, BookUpdateRequest, TagResponse, UserResponse
from app.core.entities import Book, BorrowTransaction, Tag, User
from app.core.interfaces import BookRepository, BorrowingRepository, TagRepository, UserRepository
from app.infrastructure.config import settings
from app.security import hash_password, verify_password

def _extract_image(upload_file: UploadFile) -> tuple[bytes, str]:
    content_type = upload_file.content_type
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File harus berupa gambar")
    content = upload_file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File gambar kosong")
    return content, content_type


def _require_user_id(user: User) -> int:
    if user.id is None:
        raise HTTPException(status_code=500, detail="User ID tidak tersedia")
    return user.id


def _require_book_id(book: Book) -> int:
    if book.id is None:
        raise HTTPException(status_code=500, detail="Book ID tidak tersedia")
    return book.id

def user_to_response(user: User) -> UserResponse:
    user_id = _require_user_id(user)
    return UserResponse(
        id=user_id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar_url=f"/users/{user_id}/avatar" if user.avatar_image else None,
    )

def register_user(user_repo: UserRepository, name: str, email: str, password: str) -> User:
    existing = user_repo.get_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    user = User(
        id=None,
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin" if settings.default_admin_email and email == settings.default_admin_email else "user",
    )
    return user_repo.add(user)

def authenticate_user(user_repo: UserRepository, email: str, password: str) -> User:
    user = user_repo.get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email / password salah")
    return user

def upload_user_avatar(
    user_repo: UserRepository,
    current_user: User,
    upload_file: UploadFile,
) -> User:
    image, content_type = _extract_image(upload_file)
    current_user.avatar_image = image
    current_user.avatar_content_type = content_type
    return user_repo.update(current_user)

def parse_or_create_tags(tag_repo: TagRepository, tag_csv: str | None) -> list[Tag]:
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
    existing = tag_repo.get_by_names(names)
    existing_map = {tag.name: tag for tag in existing}
    result: list[Tag] = []
    for name in names:
        if name in existing_map:
            result.append(existing_map[name])
            continue
        tag = tag_repo.add(Tag(id=None, name=name))
        result.append(tag)
    return result

def book_to_response(book: Book) -> BookResponse:
    book_id = _require_book_id(book)
    return BookResponse(
        id=book_id,
        title=book.title,
        author=book.author,
        description=book.description,
        stock_total=book.stock_total,
        stock_available=book.stock_available,
        cover_url=f"/books/{book_id}/cover" if book.cover_image else None,
        tags=[TagResponse.model_validate(tag) for tag in book.tags],
    )


def create_tag(tag_repo: TagRepository, name: str) -> Tag:
    existing = tag_repo.get_by_name(name)
    if existing:
        raise HTTPException(status_code=400, detail="Tag sudah ada")
    return tag_repo.add(Tag(id=None, name=name))


def update_tag(tag_repo: TagRepository, tag_id: int, name: str) -> Tag:
    existing = tag_repo.get_by_id(tag_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tag tidak ditemukan")
    existing.name = name
    return tag_repo.update(existing)


def delete_tag(tag_repo: TagRepository, tag_id: int) -> None:
    tag = tag_repo.get_by_id(tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag tidak ditemukan")
    tag_repo.delete(tag_id)


def create_book(
    book_repo: BookRepository,
    tag_repo: TagRepository,
    title: str,
    author: str,
    description: str,
    stock_total: int,
    tag_names: str | None,
    cover_file: UploadFile | None,
) -> Book:
    book = Book(
        id=None,
        title=title,
        author=author,
        description=description,
        stock_total=stock_total,
        stock_available=stock_total,
    )
    book.tags = parse_or_create_tags(tag_repo, tag_names)
    if cover_file:
        image, content_type = _extract_image(cover_file)
        book.cover_image = image
        book.cover_content_type = content_type
    return book_repo.add(book)


def list_books(
    book_repo: BookRepository,
    q: str | None,
    tag: str | None,
    available_only: bool,
) -> list[Book]:
    books = book_repo.list(q, available_only)
    if tag:
        books = [book for book in books if any(t.name == tag for t in book.tags)]
    return books


def get_book_by_id(book_repo: BookRepository, book_id: int) -> Book:
    book = book_repo.get_by_id(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    return book


def update_book(
    book_repo: BookRepository,
    tag_repo: TagRepository,
    book_id: int,
    payload: BookUpdateRequest,
) -> Book:
    book = get_book_by_id(book_repo, book_id)
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
        book.tags = parse_or_create_tags(tag_repo, ",".join(payload.tag_names))
    return book_repo.update(book)


def upload_book_cover(book_repo: BookRepository, book_id: int, cover_file: UploadFile) -> Book:
    book = get_book_by_id(book_repo, book_id)
    image, content_type = _extract_image(cover_file)
    book.cover_image = image
    book.cover_content_type = content_type
    return book_repo.update(book)


def delete_book(book_repo: BookRepository, book_id: int) -> None:
    book = get_book_by_id(book_repo, book_id)
    resolved_book_id = _require_book_id(book)
    book_repo.delete(resolved_book_id)


def borrow_book(
    book_repo: BookRepository,
    borrowing_repo: BorrowingRepository,
    current_user: User,
    book_id: int,
    days: int,
) -> BorrowTransaction:
    book = get_book_by_id(book_repo, book_id)
    if book.stock_available <= 0:
        raise HTTPException(status_code=400, detail="Buku sedang tidak tersedia")
    resolved_book_id = _require_book_id(book)
    user_id = _require_user_id(current_user)
    borrowing = BorrowTransaction(
        id=None,
        user_id=user_id,
        book_id=resolved_book_id,
        status="borrowed",
        borrowed_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=days),
    )
    book.stock_available -= 1
    book_repo.update(book)
    return borrowing_repo.add(borrowing)


def list_user_borrowings(
    borrowing_repo: BorrowingRepository, current_user: User
) -> list[BorrowTransaction]:
    user_id = _require_user_id(current_user)
    return borrowing_repo.list_by_user(user_id)


def request_return(
    borrowing_repo: BorrowingRepository,
    current_user: User,
    borrowing_id: int,
) -> BorrowTransaction:
    borrowing = borrowing_repo.get_by_id(borrowing_id)
    if borrowing is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    user_id = _require_user_id(current_user)
    if borrowing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Bukan peminjaman milik Anda")
    if borrowing.status == "returned":
        raise HTTPException(status_code=400, detail="Buku sudah dikembalikan")
    borrowing.status = "return_requested"
    return borrowing_repo.update(borrowing)


def list_return_requests(borrowing_repo: BorrowingRepository) -> list[BorrowTransaction]:
    return borrowing_repo.list_return_requests()


def confirm_return(
    book_repo: BookRepository,
    borrowing_repo: BorrowingRepository,
    current_admin: User,
    borrowing_id: int,
) -> BorrowTransaction:
    borrowing = borrowing_repo.get_by_id(borrowing_id)
    if borrowing is None:
        raise HTTPException(status_code=404, detail="Data peminjaman tidak ditemukan")
    if borrowing.status == "returned":
        raise HTTPException(status_code=400, detail="Buku sudah dikonfirmasi kembali")
    if borrowing.status not in {"borrowed", "return_requested"}:
        raise HTTPException(status_code=400, detail="Status peminjaman tidak valid")

    book = get_book_by_id(book_repo, borrowing.book_id)
    admin_id = _require_user_id(current_admin)
    borrowing.status = "returned"
    borrowing.returned_at = datetime.now(timezone.utc)
    borrowing.processed_by_admin_id = admin_id
    book.stock_available = min(book.stock_total, book.stock_available + 1)
    book_repo.update(book)
    return borrowing_repo.update(borrowing)
