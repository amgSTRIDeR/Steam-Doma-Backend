
# Build dependencies
FROM python:3.15-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.8 \
    /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY src/ ./src/

RUN uv sync --locked --no-dev --no-editable


# Production image
FROM python:3.15-slim-trixie

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

# Run without root privileges
USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "steam_doma.main:app", "--host", "0.0.0.0", "--port", "8000"]
