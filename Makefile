unittest:
	DATABASE__DATABASE_NAME=test \time coverage run -m pytest -vv

cov_report:
	coverage report -m

cov_html:
	coverage html

test: unittest cov_report cov_html
