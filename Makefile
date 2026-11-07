.DEFAULT_GOAL := help

PYTHON := venv/bin/python

.PHONY: help check

help:
	@echo "Run the product tests:"
	@echo "  make check"

check:
	@test -x $(PYTHON) || (echo "Missing venv. Create it with: python3 -m venv venv && venv/bin/python -m pip install -r requirements.txt"; exit 1)
	@PGTZ=UTC $(PYTHON) -m pytest
