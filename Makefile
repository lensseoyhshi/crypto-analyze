.PHONY: help install dev test lint format clean docker-up docker-down migrate

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
	pip install -r requirements.txt

dev:  ## Run development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:  ## Run tests
	pytest -v

test-cov:  ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term

lint:  ## Run linters
	flake8 app tests
	black --check app tests
	isort --check-only app tests

format:  ## Format code
	black app tests
	isort app tests

clean:  ## Clean up cache and build files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ dist/ build/

docker-up:  ## Start Docker Compose services
	docker-compose up --build

docker-down:  ## Stop Docker Compose services
	docker-compose down

docker-logs:  ## View Docker Compose logs
	docker-compose logs -f

migrate:  ## Run database migrations
	alembic upgrade head

migrate-create:  ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-rollback:  ## Rollback last migration
	alembic downgrade -1

db-reset:  ## Reset database (WARNING: deletes all data)
	docker-compose down -v
	docker-compose up -d db
	sleep 5
	alembic upgrade head

