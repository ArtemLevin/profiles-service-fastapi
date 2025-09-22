PY_SRC=services gateway
TYPECHECK_SRC=services

.PHONY: up down logs install-dev format format-check lint lint-fix typecheck check

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f

install-dev:
	pip install -r requirements-dev.txt

format:
	black $(PY_SRC)

format-check:
	black --check $(PY_SRC)

lint:
	ruff check $(PY_SRC)

lint-fix:
	ruff check --fix $(PY_SRC)

typecheck:
	mypy $(TYPECHECK_SRC)

check: format-check lint typecheck
