PYTHON ?= python
.PHONY: dev migrate seed test evaluate build demo-check
dev:
	docker compose -f infra/compose.yaml up --build
migrate:
	$(PYTHON) -m scripts.migrate
seed:
	$(PYTHON) -m data.generate
test:
	$(PYTHON) -m pytest -q
evaluate:
	$(PYTHON) -m scripts.evaluate
	$(PYTHON) -m scripts.transport_evaluation
	$(PYTHON) -m scripts.federation_check
build:
	npm --prefix apps/web ci
	npm --prefix apps/web run build
	docker build -f infra/Dockerfile -t swasthyasetu-api .
demo-check:
	$(PYTHON) -m scripts.demo_check
