FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev


FROM python:3.14-slim

LABEL maintainer="KangHyeok Lee"
LABEL email="caff1nepill@gmail.com"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/app/.venv/bin:$PATH

RUN apt-get update \
 && apt-get install -y --no-install-recommends libmagic1 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 fastapi \
 && useradd --system --uid 1001 --gid fastapi --create-home fastapi

WORKDIR /app
COPY --from=builder --chown=fastapi:fastapi /app /app
USER fastapi

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]