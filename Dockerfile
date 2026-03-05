FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install runtime dependencies (no dev deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy app source
COPY models/ ./models/
COPY web/ ./web/
COPY maint.py ./

# Vehicle YAML files are loaded from /app/vehicles — mount a volume there
VOLUME ["/app/vehicles"]

EXPOSE 5002

CMD [".venv/bin/flask", "--app", "web/app.py", "run", "--host", "0.0.0.0", "--port", "5002"]
