from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ai_book_app")


class Book(BaseModel):
    name: str
    author: str
    isbn: int
    genre: str


mock_db = {}


@app.get("/health")
def read_root():
    return {"status": "ok"}


# get all books
@app.get("/books")
def get_all_books():
    return mock_db


# get a specific book
@app.get("/books/{isbn}", response_model=Book)
def get_books(isbn: int):
    if isbn not in mock_db:
        raise HTTPException(status=400, detail="Book not found")

    return mock_db[isbn]


@app.post("/books")
def create_book(book: Book):
    # check if book exist or not
    if book.isbn in mock_db:
        raise HTTPException(status=400, detail="Book already exist")

    mock_db[book.isbn] = book
    return {"message": "Book added successfully", "book": book}
