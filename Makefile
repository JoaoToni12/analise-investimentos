.PHONY: install lint type-check test test-fast run docker-build docker-run

install:
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	ruff check . --fix
	ruff format .

type-check:
	mypy ingestion engine config.py

test:
	pytest -v

test-fast:
	pytest -v -m "not slow"

run:
	streamlit run main.py

docker-build:
	docker build -t rebalanceamento .

docker-run:
	docker run -p 8501:8501 --env-file .env rebalanceamento
