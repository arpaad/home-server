# Config
IMAGE_NAME=home-server
APP_NAME=home-server
PORT=8000

# Start app locally with Poetry
run:
	poetry run uvicorn app.main:app --reload

# Build image
build:
	poetry export -f requirements.txt --without-hashes -o requirements.txt
	podman build -t $(IMAGE_NAME) .

# Run container
start:
	podman run --rm -d --name $(APP_NAME) -p $(PORT):8000 $(IMAGE_NAME)

# Run container iterative
start-it:
	podman run --rm -it --name $(APP_NAME) -p $(PORT):8000 $(IMAGE_NAME)

# Stop container
stop:
	podman stop $(APP_NAME) || true
