COMPOSE ?= docker compose
VENV    ?= .venv
PYTHON  ?= $(VENV)/bin/python
COUNT   ?= 100
SEED    ?=

.DEFAULT_GOAL := help
.PHONY: help install up down logs migrate test test-unit seed_fields

help: ## Показати доступні команди
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Створити .venv і встановити залежності (разом із dev)
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -e '.[dev]'

up: ## Зібрати й підняти додаток і базу (http://localhost:8000)
	$(COMPOSE) up -d --build --wait

down: ## Зупинити контейнери (дані бази зберігаються у volume)
	$(COMPOSE) down

logs: ## Стежити за логами додатку
	$(COMPOSE) logs -f web

migrate: ## Застосувати міграції Alembic
	$(COMPOSE) run --rm --build web alembic upgrade head

test: migrate ## Запустити всі тести (contract-тести потребують бази)
	$(PYTHON) -m pytest

test-unit: ## Запустити лише unit-тести, без Docker
	$(PYTHON) -m pytest tests/unit

seed_fields: migrate ## Згенерувати тестові поля: make seed_fields COUNT=500 SEED=42
	$(COMPOSE) run --rm web python -m src.scripts.seed_fields --count $(COUNT) $(if $(SEED),--seed $(SEED))
