# H.O.M.E. – Household Operations, Management & Essentials

**H.O.M.E.** (Household Operations, Management & Essentials) backend built with FastAPI.  
A modular, scalable backend intended to help families manage household tasks in real-time.

> ⚠️ This project is under active development. Current implementation is an early prototype.

## Project Overview

H.O.M.E. aims to provide a **centralized backend system** for managing everyday household activities. The system is designed to be modular and flexible, allowing different components to evolve independently while potentially interacting with each other in meaningful ways.  

### Planned Modules (conceptual)

- **Shopping** – tracking items, generating lists, and possibly linking with recipes  
- **Recipes** – storing and managing recipes, potentially connected to shopping lists  
- **Tasks** – managing household chores and recurring activities  
- **Calendar** – scheduling tasks, shopping trips, or events  
- **Finance** - budgets, and spending patterns 

> These are *planned or conceptual modules*. Their existence and design may evolve over time as the project grows.

## Goals

- Provide a clean, modular FastAPI backend  
- Enable easy integration with multiple frontend clients (mobile, web)  
- Support real-time features such as notifications and task updates  
- Serve as a **portfolio project** demonstrating software architecture, API design, and scalable backend practices

---

## Getting Started

This project uses (**Python 3.13**)[https://www.python.org/], and optionally, **Make** is recommended to simplify common tasks.  
For package and project management, it uses (**UV**)[https://docs.astral.sh/uv/].  
For linting and formatting, it uses (**Ruff**)[https://astral.sh/ruff],  
both are powerful open-source projects written in __Rust__ under the MIT License.  

For static type checking, it uses (**Pyright**)[https://microsoft.github.io/pyright/#/].  

---

> For development, you don’t necessarily need Python installed on your system.  
> If you don’t have Python 3.13, UV will install it along with all other required dependencies.

To set up your development environment, follow these 3 steps:  

1. (Install UV)[https://docs.astral.sh/uv/getting-started/installation/]  
2. `$ uv sync`  
3. `$ uv run pre-commit install`  

Or, if you have **Make**, simply run:

```bash
make install-dev-dependencies
````

---

## Development Tools & Workflow

This project uses several tools to make development easier and more consistent:

| Tool                  | Purpose                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------- |
| **UV**                | Managing dependencies, virtual environments, and fixed requirements for reproducibility |
| **Ruff**              | Linting and formatting Python code                                                      |
| **Pyright**           | Static type checking                                                                    |
| **pre-commit**        | Automatically runs formatters and updates locked dependencies before commits            |
| **Podman**            | Local containerization                                                                  |
| **pytest / unittest** | Running tests and measuring coverage                                                    |
| **GitHub Actions**    | CI workflows for linting, type checking, testing, coverage, and building Docker images  |

---

## Makefile Commands

All common development tasks are exposed via `make` commands:

| Command                    | Description                                                              |
| -------------------------- | ------------------------------------------------------------------------ |
| `run`                      | Run the app locally with `uvicorn --reload` on `PORT=8080`               |
| `build`                    | Build a container image with dependencies exported to `requirements.txt` |
| `start-container`          | Start the container in detached mode                                     |
| `start-container-it`       | Start the container interactively                                        |
| `stop`                     | Stop the running container                                               |
| `linter`                   | Run `ruff check` to lint Python code                                     |
| `linter-fix`               | Run `ruff check --fix` to automatically fix lint issues                  |
| `formatter`                | Run `ruff format` to automatically format code                           |
| `type-checker`             | Run `pyright` to check static types                                      |
| `test`                     | Run all unit tests with `unittest`                                       |
| `coverage`                 | Run tests with coverage reporting via `pytest`                           |
| `install-dev-dependencies` | Install all dependencies and pre-commit hooks for development            |

---

## Pre-commit Hooks

The repository includes **pre-commit hooks** to automatically ensure code quality before every commit:

* Format all Python files in the commit (if under the `app/` folder).
* Update locked dependencies if `pyproject.toml` changes.

> ✅ `uv.lock` is versioned in the repository to ensure reproducibility. You **do not** need to run `uv lock --dev` unless you add or update dependencies.

These hooks run automatically before each commit.

You can also manually run them on all files:

```bash
pre-commit run --all-files
```

---

## Continuous Integration (GitHub Actions)

The project is integrated with **GitHub Actions** to automatically run code quality checks, tests, type checking, coverage, and Docker builds on:

* **Pushes to feature branches**
* **Pull requests to main**
* **Tag pushes for releases**

---

## Notes

* All Python dependencies (main + dev) are locked in `uv.lock` for reproducible environments.
* Use `uv sync` after pulling updates to ensure your local environment matches the lock file.
* Using the Makefile simplifies repetitive tasks and ensures consistent commands across all developers.
