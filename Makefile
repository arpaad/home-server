# Config
IMAGE_NAME=home-server
APP_NAME=home-server
PORT=8080

# Start app locally 
run:
	uv run uvicorn app.main:app --reload --port $(PORT)

# Build image
build:
	uv export \
		--format=requirements-txt \
		--no-editable \
		--no-hashes \
		--no-annotate \
		--no-header \
		--no-dev \
		--no-emit-project \
		--output-file=requirements.txt
	podman build -t $(IMAGE_NAME) .

# Run linter
linter:
	uv run ruff check app

# Run linter
linter-fix:
	uv run ruff check app --fix

# Run static type checker
type-checker:
	uv run pyright 

# Run formatter
formatter:
	uv run ruff format app

# Formatter + Linter + type-checker
lint-all: formatter linter type-checker

# Run tests
test: 
	uv run python3 -m unittest discover tests

# Make test covarage
coverage:
	PYTHONPATH=$(pwd) uv run pytest --cov=app --cov-report=term-missing tests

# Run audit 
security-audit:
	uv run safety scan

# Run container
start-container:
	podman run --rm -d --name $(APP_NAME) -p $(PORT):8080 $(IMAGE_NAME)

# Run container iterative
start-container-it:
	podman run --rm -it --name $(APP_NAME) -p $(PORT):8080 $(IMAGE_NAME)

# Stop container
stop:
	podman stop $(APP_NAME) || true

# Install dependencies for developing the project
install-dev-dependencies:
	pip install uv
	uv sync
	uv run pre-commit install
	