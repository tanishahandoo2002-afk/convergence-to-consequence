PY := .venv/bin/python

.PHONY: setup test

setup:
	uv venv --python 3.12 --allow-existing && uv pip sync requirements.txt
	$(PY) -m checks.check_setup

test:
	.venv/bin/pytest -q

.PHONY: rq1-search
rq1-search:
	$(PY) -m tools.pubmed_search rq1
	$(PY) -m checks.check_search rq1
