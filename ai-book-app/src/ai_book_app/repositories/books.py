from ai_book_app.models import Book


class BookRepository:
    def __init__(self) -> None:
        self._books: dict[str, Book] = {}

    def get_all(self) -> list[Book]:
        return list(self._books.values())

    def get_by_isbn(self, isbn: str) -> Book | None:
        return self._books.get(isbn)

    def create(self, book: Book) -> Book:
        self._books[book.isbn] = book
        return book

    def update(self, book: Book) -> Book:
        self._books[book.isbn] = book
        return book

    def delete(self, isbn: str) -> None:
        del self._books[isbn]

    def exists(self, isbn: str) -> bool:
        return isbn in self._books

    def clear(self) -> None:
        self._books.clear()


book_repository = BookRepository()
