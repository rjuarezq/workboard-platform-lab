# ==========================================
# STAGE 1: (Builder) Build locker prod deps
# ==========================================
FROM python:3.11.16-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app    

# ===================================================
# STAGE 2: (RUNTIME) Run FastAPI without build tools
# ===================================================
FROM python:3.11.16-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN groupadd --gid 10001 workboard \
    && useradd \
        --uid 10001 \
        --gid workboard \
        --create-home \
        --shell /usr/sbin/nologin \
        workboard

COPY --from=builder --chown=workboard:workboard /app/.venv /app/.venv
COPY --from=builder --chown=workboard:workboard /app/alembic /app/alembic
COPY --from=builder --chown=workboard:workboard /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=workboard:workboard /app/app /app/app

USER workboard
EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

