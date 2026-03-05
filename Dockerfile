FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

COPY models/ ./models/
COPY web/ ./web/
COPY maint.py ./

VOLUME ["/app/vehicles"]

EXPOSE 5002

CMD [".venv/bin/flask", "--app", "web/app.py", "run", "--host", "0.0.0.0", "--port", "5002"]
