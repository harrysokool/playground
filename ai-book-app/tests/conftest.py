import pytest
from fastapi.testclient import TestClient

from ai_book_app.main import app
from ai_book_app.repositories.books import book_repository


@pytest.fixture(autouse=True)
def clear_book_repository() -> None:
    book_repository.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_book() -> dict[str, str]:
    return {
        "name": "The Pragmatic Programmer",
        "author": "Andrew Hunt and David Thomas",
        "isbn": "9780135957059",
        "genre": "Software Engineering",
    }
