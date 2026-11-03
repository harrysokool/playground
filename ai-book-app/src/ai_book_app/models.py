from pydantic import BaseModel, field_validator


class Book(BaseModel):
    name: str
    author: str
    isbn: str
    genre: str

    @field_validator("name", "author", "genre")
    @classmethod
    def check_not_empty(cls, value: str, info) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} cannot be empty or blank space")

        return value.strip()

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value: str) -> str:
        value = value.strip()

        if not value.isdigit():
            raise ValueError("ISBN must contain digits only")

        if len(value) not in (10, 13):
            raise ValueError("ISBN must be exactly 10 or 13 digits long")

        return value
