import pytest
from fastapi.testclient import TestClient

from ai_book_app.api import app, mock_db


@pytest.fixture(autouse=True)
def clear_mock_db() -> None:
    mock_db.clear()


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
