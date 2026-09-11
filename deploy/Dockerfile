# Build context is the repository root, so one image carries the API and the
# built client. The client is static files once built, so there is no runtime
# process to containerise — the API serves it from the same origin, which also
# removes CORS from the picture rather than configuring it.

# ---- stage 1: build the client ----
FROM docker.io/library/node:24-slim AS client

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---- stage 2: the runtime ----
FROM docker.io/library/python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/srv/.venv \
    PATH=/srv/.venv/bin:$PATH

WORKDIR /srv

# Dependencies first: this layer is rebuilt only when the lock file changes.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini

RUN uv sync --locked --no-dev

# app/web.py serves whatever is here; without it the API still starts, which
# is what development relies on.
COPY --from=client /build/dist ./app/client

COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Run as an unprivileged user; the container writes nothing but logs.
RUN useradd --system --create-home --uid 10001 home \
    && chown -R home:home /srv
USER home

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
