FROM python:3.14-slim

# Copy the uv binary directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster app startup
ENV UV_COMPILE_BYTECODE=1

# 1. OPTIMIZATION: Copy ONLY dependency specs first
COPY pyproject.toml uv.lock ./

# 2. OPTIMIZATION: Install dependencies ahead of copying application code
# --no-install-project tells uv to freeze the dependencies in a cached layer
RUN uv sync --frozen --no-install-project --no-dev

# 3. Copy the rest of your application code (source files, etc.)
COPY . .

# 4. Final sync to incorporate your app module into the virtual environment
RUN uv sync --frozen --no-dev

# 5. OPTIMIZATION: Add uv's virtual env directly to the system PATH
# This removes the need to prepend "uv run" to your start command
ENV PATH="/app/.venv/bin:$PATH"

# Expose the API port (good practice for documentation)
EXPOSE 8000

# 6. OPTIMIZATION: Run Uvicorn directly out of the PATH environment
CMD ["uvicorn", "ai_book_app.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
