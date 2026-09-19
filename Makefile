.PHONY: setup test local dev coverage check


setup:
	uv sync
	git config core.hooksPath .githooks

test:
	ENV=test uv run pytest $(ARGS)

local:
	@if [ -n "$(port)" ]; then \
		ENV=local \
		uv run fastapi dev --port $(port) app/main.py; \
	else \
		ENV=local \
		uv run fastapi dev --port 8000 app/main.py; \
	fi

dev:
	@if [ -n "$(port)" ]; then \
		ENV=dev \
		uv run fastapi dev --port $(port) app/main.py; \
	else \
		ENV=dev \
		uv run fastapi dev --port 8000 app/main.py; \
	fi

coverage:
	ENV=test uv run coverage run -m pytest
	uv run coverage report -m
	uv run coverage html

check:
	uv run ruff check --fix
	uv run ruff format --check
