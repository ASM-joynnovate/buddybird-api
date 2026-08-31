.PHONY: setup test local local-otel dev dev-otel coverage check


setup:
	uv sync
	git config core.hooksPath .githooks

test:
	BUDDYBIRD_ENV=test uv run pytest $(ARGS)

local:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=local \
		uv run fastapi dev --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=local \
		uv run fastapi dev --port 8000 app/main.py; \
	fi

local-otel:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=local \
		uv run fastapi run --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=local \
		uv run fastapi run --port 8000 app/main.py; \
	fi

dev:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=dev \
		uv run fastapi dev --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=dev \
		uv run fastapi dev --port 8000 app/main.py; \
	fi

dev-otel:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=dev \
		uv run fastapi run --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=dev \
		uv run fastapi run --port 8000 app/main.py; \
	fi

coverage:
	BUDDYBIRD_ENV=test uv run coverage run -m pytest
	uv run coverage report -m
	uv run coverage html

check:
	uv run ruff check --fix
	uv run ruff format --check
