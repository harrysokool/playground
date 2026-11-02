from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ai_book_app")


class Book(BaseModel):
    name: str
    author: str
    isbn: str
    genre: str


mock_db = {}


@app.get("/health")
def read_root():
    return {"status": "ok"}


# get all books
@app.get("/books", response_model=list[Book])
def get_all_books():
    return list(mock_db.values())


# get a specific book
@app.get("/books/{isbn}", response_model=Book)
def get_books(isbn: str):
    if isbn not in mock_db:
        raise HTTPException(status_code=404, detail="Book not found")
    return mock_db[isbn]


@app.post("/books", status_code=201)
def create_book(book: Book):
    if book.isbn in mock_db:
        raise HTTPException(status_code=409, detail="Book already exists")

    mock_db[book.isbn] = book
    return {"message": "Book added successfully", "book": book}


@app.delete("/books/{isbn}")
def delete_book(isbn: str):
    if isbn not in mock_db:
        raise HTTPException(status_code=404, detail="Book not found")

    del mock_db[isbn]
    return {"message": "Book deleted successfully"}


@app.put("/books/{isbn}")
def update_book(isbn: str, book: Book):
    if isbn not in mock_db:
        raise HTTPException(status_code=404, detail="Book not found")

    if isbn != book.isbn:
        raise HTTPException(
            status_code=400, detail="URL ISBN does not match book payload ISBN"
        )

    mock_db[isbn] = book
    return {"message": "Book updated successfully", "book": book}
