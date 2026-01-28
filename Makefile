.PHONY: install test lint format build docker-build

install:
	pip install -r backend/requirements.txt -r requirements-dev.txt
	python -m spacy download en_core_web_sm

test:
	pytest -q

lint:
	flake8

format:
	black .
	isort .

build:
	python -m build

docker-build:
	docker build -t resume-analyzer-builder:local .
