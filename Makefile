unittest:
	DATABASE__DATABASE_NAME=test \time coverage run -m pytest -vv

cov_report:
	coverage report -m

cov_html:
	coverage html

install:
	poetry install
	poetry check
	pre-commit install

test: unittest cov_report cov_html
