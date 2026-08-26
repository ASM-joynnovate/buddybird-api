.PHONY: setup test local local-otel dev dev-otel coverage check


setup:
	uv sync
	git config core.hooksPath .githooks

test:
	BUDDYBIRD_ENV=test pytest $(ARGS)

local:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=local \
		fastapi dev --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=local \
		fastapi dev --port 8000 app/main.py; \
	fi

local-otel:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=local \
		fastapi run --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=local \
		fastapi run --port 8000 app/main.py; \
	fi

dev:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=dev \
		fastapi dev --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=dev \
		fastapi dev --port 8000 app/main.py; \
	fi

dev-otel:
	@if [ -n "$(port)" ]; then \
		BUDDYBIRD_ENV=dev \
		fastapi run --port $(port) app/main.py; \
	else \
		BUDDYBIRD_ENV=dev \
		fastapi run --port 8000 app/main.py; \
	fi

coverage:
	BUDDYBIRD_ENV=test coverage run -m pytest
	coverage report -m
	coverage html

check:
	uv run ruff check --fix
