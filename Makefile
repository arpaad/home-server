# ---- Config ----
IMAGE_NAME=home-server
APP_NAME=home-server
PORT=8080

BACKEND=backend
FRONTEND=frontend
TEST_DB=home_test
COMPOSE=podman compose -f deploy/compose.yaml
DEPLOY_COMPOSE=podman compose -f deploy/compose.deploy.yaml

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

# Formatter + linter + type-checker, both halves of the repository
lint-all: formatter linter type-checker client-lint

# Run tests. Needs the development database: run `make db-up` first (the
# deploy stack does not publish Postgres, by design).
test: db-up
	cd $(BACKEND) && uv run pytest tests

# Make test coverage
coverage: db-up
	cd $(BACKEND) && uv run pytest --cov=app --cov-report=term-missing tests

# Run audit
security-audit:
	cd $(BACKEND) && uv run safety scan

# ---- Client ----

# Install the client's dependencies
client-install:
	cd $(FRONTEND) && npm install

# Run the client's dev server (proxies /api to the backend)
client-dev:
	cd $(FRONTEND) && npm run dev

# Build the client into frontend/dist
client-build:
	cd $(FRONTEND) && npm run build

# Lint and type-check the client
client-lint:
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run typecheck

# End-to-end tests. Builds the client and drives a real browser against the
# real API, because the rule under test lives in SQL — a mocked API would only
# prove the mock agrees with itself.
#   make e2e                    # starts its own preview server
#   make e2e-deployed           # against the running stack on :8080
e2e:
	cd $(FRONTEND) && npm run test:e2e

e2e-deployed:
	cd $(FRONTEND) && E2E_BASE_URL=http://127.0.0.1:8080 npm run test:e2e

# ---- Database ----

# Start only Postgres, wait until it accepts connections, and make sure the
# test database exists. The test suite runs against real PostgreSQL, so
# forgetting this database is otherwise a confusing wall of connection errors.
db-up:
	$(COMPOSE) up -d db
	$(COMPOSE) exec db sh -c 'until pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB; do sleep 1; done'
	$(COMPOSE) exec db sh -c 'psql -U $$POSTGRES_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '"'"'$(TEST_DB)'"'"'" | grep -q 1 || psql -U $$POSTGRES_USER -d postgres -c "CREATE DATABASE $(TEST_DB) OWNER $$POSTGRES_USER"'

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

# ---- Deployment (prebuilt image from GHCR) ----
#
# The Pi hosts the image, it does not build it. These targets run the same
# stack here on a laptop.

# Fetch the published image
deploy-pull:
	$(DEPLOY_COMPOSE) pull

# Run the published image
deploy-up:
	$(DEPLOY_COMPOSE) up -d

# Stop it, keeping the volume
deploy-down:
	$(DEPLOY_COMPOSE) down

# Follow the deployed stack's logs
deploy-logs:
	$(DEPLOY_COMPOSE) logs -f

# Run container standalone
start-container:
	podman run --rm -d --name $(APP_NAME) -p $(PORT):8080 $(IMAGE_NAME)

# Stop container
stop:
	podman stop $(APP_NAME) || true

.PHONY: run install-dev-dependencies linter linter-fix type-checker formatter \
        lint-all test coverage security-audit client-install client-dev \
        client-build client-lint e2e e2e-deployed db-up db-down migrate \
        migration seed db-reset build up down logs deploy-pull deploy-up \
        deploy-down deploy-logs start-container stop
