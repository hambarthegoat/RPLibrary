from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.entities import Book, BorrowTransaction, Tag, User
from app.infrastructure.models import (
    Book as BookModel,
    BorrowTransaction as BorrowModel,
    Tag as TagModel,
    User as UserModel,
)


def _user_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        name=model.name,
        email=model.email,
        role=model.role,
        password_hash=model.password_hash,
        avatar_image=model.avatar_image,
        avatar_content_type=model.avatar_content_type,
        created_at=model.created_at,
    )


def _tag_to_entity(model: TagModel) -> Tag:
    return Tag(id=model.id, name=model.name)


def _book_to_entity(model: BookModel) -> Book:
    return Book(
        id=model.id,
        title=model.title,
        author=model.author,
        description=model.description,
        stock_total=model.stock_total,
        stock_available=model.stock_available,
        cover_image=model.cover_image,
        cover_content_type=model.cover_content_type,
        created_at=model.created_at,
        tags=[_tag_to_entity(tag) for tag in model.tags],
    )


def _borrow_to_entity(model: BorrowModel) -> BorrowTransaction:
    return BorrowTransaction(
        id=model.id,
        user_id=model.user_id,
        book_id=model.book_id,
        status=model.status,
        borrowed_at=model.borrowed_at,
        due_date=model.due_date,
        returned_at=model.returned_at,
        processed_by_admin_id=model.processed_by_admin_id,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _user_to_entity(model) if model else None

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _user_to_entity(model) if model else None

    def add(self, user: User) -> User:
        model = UserModel(
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            avatar_image=user.avatar_image,
            avatar_content_type=user.avatar_content_type,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _user_to_entity(model)

    def update(self, user: User) -> User:
        if user.id is None:
            raise ValueError("User ID required for update")
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError("User not found")
        model.name = user.name
        model.email = user.email
        model.password_hash = user.password_hash
        model.role = user.role
        model.avatar_image = user.avatar_image
        model.avatar_content_type = user.avatar_content_type
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _user_to_entity(model)


class SqlAlchemyTagRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[Tag]:
        tags = self._session.scalars(select(TagModel).order_by(TagModel.name)).all()
        return [_tag_to_entity(tag) for tag in tags]

    def get_by_id(self, tag_id: int) -> Tag | None:
        model = self._session.get(TagModel, tag_id)
        return _tag_to_entity(model) if model else None

    def get_by_name(self, name: str) -> Tag | None:
        model = self._session.scalar(select(TagModel).where(TagModel.name == name))
        return _tag_to_entity(model) if model else None

    def get_by_names(self, names: list[str]) -> list[Tag]:
        if not names:
            return []
        models = self._session.scalars(select(TagModel).where(TagModel.name.in_(names))).all()
        return [_tag_to_entity(tag) for tag in models]

    def add(self, tag: Tag) -> Tag:
        model = TagModel(name=tag.name)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _tag_to_entity(model)

    def update(self, tag: Tag) -> Tag:
        if tag.id is None:
            raise ValueError("Tag ID required for update")
        model = self._session.get(TagModel, tag.id)
        if model is None:
            raise ValueError("Tag not found")
        model.name = tag.name
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _tag_to_entity(model)

    def delete(self, tag_id: int) -> None:
        model = self._session.get(TagModel, tag_id)
        if model is None:
            raise ValueError("Tag not found")
        self._session.delete(model)
        self._session.commit()


class SqlAlchemyBookRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_tag_models(self, tags: list[Tag]) -> list[TagModel]:
        tag_ids = [tag.id for tag in tags if tag.id is not None]
        if not tag_ids:
            return []
        models = self._session.scalars(select(TagModel).where(TagModel.id.in_(tag_ids))).all()
        return list(models)

    def add(self, book: Book) -> Book:
        model = BookModel(
            title=book.title,
            author=book.author,
            description=book.description,
            stock_total=book.stock_total,
            stock_available=book.stock_available,
            cover_image=book.cover_image,
            cover_content_type=book.cover_content_type,
        )
        model.tags = self._get_tag_models(book.tags)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _book_to_entity(model)

    def list(self, q: str | None, available_only: bool) -> list[Book]:
        query = select(BookModel).options(selectinload(BookModel.tags)).order_by(BookModel.title)
        if q:
            query = query.where(
                (BookModel.title.ilike(f"%{q}%")) | (BookModel.author.ilike(f"%{q}%"))
            )
        if available_only:
            query = query.where(BookModel.stock_available > 0)
        books = self._session.scalars(query).all()
        return [_book_to_entity(book) for book in books]

    def get_by_id(self, book_id: int) -> Book | None:
        model = self._session.scalar(
            select(BookModel)
            .options(selectinload(BookModel.tags))
            .where(BookModel.id == book_id)
        )
        return _book_to_entity(model) if model else None

    def update(self, book: Book) -> Book:
        if book.id is None:
            raise ValueError("Book ID required for update")
        model = self._session.scalar(
            select(BookModel)
            .options(selectinload(BookModel.tags))
            .where(BookModel.id == book.id)
        )
        if model is None:
            raise ValueError("Book not found")
        model.title = book.title
        model.author = book.author
        model.description = book.description
        model.stock_total = book.stock_total
        model.stock_available = book.stock_available
        model.cover_image = book.cover_image
        model.cover_content_type = book.cover_content_type
        model.tags = self._get_tag_models(book.tags)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _book_to_entity(model)

    def delete(self, book_id: int) -> None:
        model = self._session.get(BookModel, book_id)
        if model is None:
            raise ValueError("Book not found")
        self._session.delete(model)
        self._session.commit()


class SqlAlchemyBorrowingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, borrowing: BorrowTransaction) -> BorrowTransaction:
        model = BorrowModel(
            user_id=borrowing.user_id,
            book_id=borrowing.book_id,
            status=borrowing.status,
            borrowed_at=borrowing.borrowed_at,
            due_date=borrowing.due_date,
            returned_at=borrowing.returned_at,
            processed_by_admin_id=borrowing.processed_by_admin_id,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _borrow_to_entity(model)

    def get_by_id(self, borrowing_id: int) -> BorrowTransaction | None:
        model = self._session.get(BorrowModel, borrowing_id)
        return _borrow_to_entity(model) if model else None

    def list_by_user(self, user_id: int) -> list[BorrowTransaction]:
        borrowings = self._session.scalars(
            select(BorrowModel)
            .where(BorrowModel.user_id == user_id)
            .order_by(BorrowModel.borrowed_at.desc())
        ).all()
        return [_borrow_to_entity(borrowing) for borrowing in borrowings]

    def list_return_requests(self) -> list[BorrowTransaction]:
        borrowings = self._session.scalars(
            select(BorrowModel)
            .where(BorrowModel.status == "return_requested")
            .order_by(BorrowModel.borrowed_at.asc())
        ).all()
        return [_borrow_to_entity(borrowing) for borrowing in borrowings]

    def update(self, borrowing: BorrowTransaction) -> BorrowTransaction:
        if borrowing.id is None:
            raise ValueError("Borrowing ID required for update")
        model = self._session.get(BorrowModel, borrowing.id)
        if model is None:
            raise ValueError("Borrowing not found")
        model.status = borrowing.status
        model.returned_at = borrowing.returned_at
        model.processed_by_admin_id = borrowing.processed_by_admin_id
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _borrow_to_entity(model)
