PY := .venv/bin/python

.PHONY: setup test

setup:
	uv venv --python 3.12 --allow-existing && uv pip sync requirements.txt
	$(PY) -m checks.check_setup

test:
	.venv/bin/pytest -q
