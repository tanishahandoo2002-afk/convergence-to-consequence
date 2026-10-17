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

.PHONY: rq1-screen
rq1-screen:
	$(PY) -m tools.screen rq1 --stage title_abstract --rater gemini
	$(PY) -m tools.screen rq1 --stage title_abstract --rater qwen
	$(PY) -m tools.screen rq1 --stage title_abstract --merge

.PHONY: rq1-check-screen
rq1-check-screen:
	$(PY) -m tools.kappa rq1
	$(PY) -m tools.prisma rq1
	$(PY) -m checks.check_screening rq1

.PHONY: rq1-extract-check
rq1-extract-check:
	$(PY) -m checks.check_rq1_extraction

.PHONY: rq1
rq1: rq1-extract-check
	$(PY) -m rq1_map.run_ale
	$(PY) -m checks.check_rq1_ale
