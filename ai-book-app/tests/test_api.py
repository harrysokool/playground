from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    res = client.get("/health")

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_book(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    res = client.post("/books", json=sample_book)

    assert res.status_code == 201
    assert res.json()["message"] == "Book added successfully"
    assert res.json()["book"] == sample_book


def test_get_created_book(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    client.post("/books", json=sample_book)

    res = client.get(f"/books/{sample_book['isbn']}")

    assert res.status_code == 200
    assert res.json() == sample_book


def test_get_unknown_book(client: TestClient) -> None:
    res = client.get("/books/1234567890")

    assert res.status_code == 404
    assert res.json() == {"detail": "Book not found"}


def test_create_duplicate_book(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    client.post("/books", json=sample_book)

    res = client.post("/books", json=sample_book)

    assert res.status_code == 409
    assert res.json() == {"detail": "Book already exists"}


def test_reject_empty_book_name(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    sample_book["name"] = "  "

    res = client.post("/books", json=sample_book)

    assert res.status_code == 422


def test_reject_invalid_isbn(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    sample_book["isbn"] = "123"

    res = client.post("/books", json=sample_book)

    assert res.status_code == 422


def test_delete_book(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    client.post("/books", json=sample_book)

    del_res = client.delete(f"/books/{sample_book['isbn']}")
    get_res = client.get(f"/books/{sample_book['isbn']}")

    assert del_res.status_code == 200
    assert get_res.status_code == 404


def test_get_all_books(client: TestClient, sample_book: dict[str, str]) -> None:
    client.post("/books", json=sample_book)
    res = client.get("/books")

    assert res.status_code == 200
    assert res.json() == [sample_book]


def test_update_book(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    client.post("/books", json=sample_book)

    updated_book = sample_book.copy()
    updated_book["name"] = "Updated Book"

    res = client.put(
        f"/books/{sample_book['isbn']}",
        json=updated_book,
    )

    assert res.status_code == 200
    assert res.json()["message"] == "Book updated successfully"
    assert res.json()["book"] == updated_book


def test_update_book_with_mismatched_isbn(
    client: TestClient,
    sample_book: dict[str, str],
) -> None:
    client.post("/books", json=sample_book)

    original_isbn = sample_book["isbn"]
    updated_book = sample_book.copy()
    updated_book["isbn"] = "1234567890"

    res = client.put(
        f"/books/{original_isbn}",
        json=updated_book,
    )

    assert res.status_code == 400
    assert res.json() == {"detail": "URL ISBN does not match book payload ISBN"}
