PYTHON = ../.venv/bin/python
PIP    = ../.venv/bin/pip

.PHONY: install check test test-integration

install:
	$(PIP) install -r requirements.txt

check:
	PYTHONPATH=src $(PYTHON) src/check.py

test:
	$(PYTHON) -m pytest tests/unit/ -v

test-integration:
	GARMIN_INTEGRATION=1 $(PYTHON) -m pytest tests/integration/ -v
