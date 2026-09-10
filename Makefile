# ---- Config ----
IMAGE_NAME=home-server
APP_NAME=home-server
PORT=8080

BACKEND=backend
COMPOSE=podman compose -f deploy/compose.yaml

# ---- Development ----

# Start app locally
run:
	cd $(BACKEND) && uv run uvicorn app.main:app --reload --port $(PORT)

# Install dependencies for developing the project
install-dev-dependencies:
	pip install uv
	cd $(BACKEND) && uv sync
	cd $(BACKEND) && uv run pre-commit install

# ---- Quality ----

# Run linter
linter:
	cd $(BACKEND) && uv run ruff check app tests

# Run linter with autofix
linter-fix:
	cd $(BACKEND) && uv run ruff check app tests --fix

# Run static type checker
type-checker:
	cd $(BACKEND) && uv run pyright

# Run formatter
formatter:
	cd $(BACKEND) && uv run ruff format app tests

# Formatter + linter + type-checker
lint-all: formatter linter type-checker

# Run tests
test:
	cd $(BACKEND) && uv run pytest tests

# Make test coverage
coverage:
	cd $(BACKEND) && uv run pytest --cov=app --cov-report=term-missing tests

# Run audit
security-audit:
	cd $(BACKEND) && uv run safety scan

# ---- Database ----

# Start only Postgres, and wait until it is accepting connections
db-up:
	$(COMPOSE) up -d db
	$(COMPOSE) exec db sh -c 'until pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB; do sleep 1; done'

# Stop Postgres, keeping its volume
db-down:
	$(COMPOSE) stop db

# Apply every migration up to head
migrate: db-up
	cd $(BACKEND) && uv run alembic upgrade head

# Autogenerate a revision: make migration m="add stores"
migration:
	cd $(BACKEND) && uv run alembic revision --autogenerate -m "$(m)"

# Seed the household members
seed:
	cd $(BACKEND) && uv run python -m app.db.seed

# Throw the database away and rebuild it from nothing
db-reset:
	$(COMPOSE) down -v
	$(MAKE) db-up
	$(MAKE) migrate
	$(MAKE) seed

# ---- Deployment ----

# Build image
build:
	podman build -f deploy/Dockerfile -t $(IMAGE_NAME) .

# Bring the whole stack up
up:
	$(COMPOSE) up -d

# Bring the whole stack down, keeping the volume
down:
	$(COMPOSE) down

# Follow the stack's logs
logs:
	$(COMPOSE) logs -f

# Run container standalone
start-container:
	podman run --rm -d --name $(APP_NAME) -p $(PORT):8080 $(IMAGE_NAME)

# Stop container
stop:
	podman stop $(APP_NAME) || true

.PHONY: run install-dev-dependencies linter linter-fix type-checker formatter \
        lint-all test coverage security-audit db-up db-down migrate migration \
        seed db-reset build up down logs start-container stop
