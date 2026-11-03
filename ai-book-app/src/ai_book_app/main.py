from fastapi import FastAPI

from ai_book_app.routes.books import router as books_router

app = FastAPI(
    title="AI Book App",
    version="0.1.0",
)

app.include_router(books_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
