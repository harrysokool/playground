from fastapi import APIRouter, HTTPException, status

from ai_book_app.models import Book
from ai_book_app.repositories.books import book_repository

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[Book])
def get_all_books() -> list[Book]:
    return book_repository.get_all()


@router.get("/{isbn}", response_model=Book)
def get_book(isbn: str) -> Book:
    book = book_repository.get_by_isbn(isbn)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    return book


@router.post("", status_code=status.HTTP_201_CREATED)
def create_book(book: Book) -> dict[str, str | Book]:
    if book_repository.exists(book.isbn):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book already exists",
        )

    book_repository.create(book)

    return {"message": "Book added successfully", "book": book}


@router.put("/{isbn}")
def udpate_book(isbn: str, book: Book) -> dict[str, str | Book]:
    if not book_repository.exists(isbn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    if isbn != book.isbn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL ISBN does not match book payload ISBN",
        )

    book_repository.update(book)

    return {"message": "Book updated successfully", "book": book}


@router.delete("/{isbn}")
def delete_book(isbn: str) -> dict[str, str | Book]:
    if not book_repository.exists(isbn):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    book_repository.delete(isbn)

    return {"message": "Book deleted successfully"}
