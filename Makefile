PYTHON = .venv/bin/python
PIP    = .venv/bin/pip

.PHONY: setup install check clean-auth test test-integration docker-build docker-login

setup:
	python3 setup.py

install:
	$(PIP) install -r requirements.txt

check:
	PYTHONPATH=src $(PYTHON) src/check.py

clean-auth:
	rm -rf ~/.garminconnect
	@echo "OAuth cache cleared — next 'make check' will trigger a fresh login."

test:
	$(PYTHON) -m pytest tests/unit/ -v

test-integration:
	GARMIN_INTEGRATION=1 $(PYTHON) -m pytest tests/integration/ -v

docker-build:
	docker build -t garmin-mcp .

docker-login:
	docker run --rm -it \
		--env-file .env \
		-v garmin-tokens:/root/.garminconnect \
		--entrypoint python \
		garmin-mcp src/check.py
