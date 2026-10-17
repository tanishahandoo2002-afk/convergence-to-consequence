PY := .venv/bin/python

.PHONY: setup test

setup:
	uv venv --python 3.12 --allow-existing && uv pip sync requirements.txt
	$(PY) -m checks.check_setup

test:
	.venv/bin/pytest -q
	Rscript tests/R/run_all.R

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

.PHONY: masks all
masks:
	$(PY) -m masks.build_masks
	$(PY) -m checks.check_masks

all: test rq1 masks

.PHONY: rq2-pilot rq2
rq2-pilot:
	$(PY) -m rq2_nsd.extract_trials --pilot
	$(PY) -m checks.check_rq2 --dir pilot

rq2:
	$(PY) -m rq2_nsd.extract_trials --beta b3
	$(PY) -m checks.check_rq2 --dir b3
	Rscript rq2_nsd/models.R --run --input $$C2C_DATA/rq2/b3 --output rq2_nsd/results
