install:
	poetry install
	poetry check
	pre-commit install

test: unittest

unittest:
	PYTHONPATH=. DATABASE__DATABASE_NAME=test \time pytest -vv --cov=app --cov=common --cov-report=term-missing

runserver:
	PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
