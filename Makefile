.PHONY: install test lint format check pipeline dbt

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	ruff check .

format:
	ruff format .

check: lint test

pipeline:
	python -m pipeline.run

dbt:
	dbt build --project-dir dbt --profiles-dir dbt
