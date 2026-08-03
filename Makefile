#.PHONY: patch minor major test local local-otel dev dev-otel coverage check
.PHONY: test local local-otel dev dev-otel coverage check


#patch:
#	@python ./update_version.py patch
#
#minor:
#	@python ./update_version.py minor
#
#major:
#	@python ./update_version.py major

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
	uv run ruff check
