# H.O.M.E. Agent Description

This file describes the H.O.M.E. backend project for reference by AI assistants or future sessions.

## Purpose

H.O.M.E. is a **modular backend system for household management**. It is designed to handle tasks, shopping, recipes, and calendar events, allowing families to coordinate daily activities. The system is FastAPI-based and intended to be scalable, modular, and extensible.

## Key Concepts

- **Modular architecture**: Each feature (tasks, shopping, recipes, calendar) is treated as a separate module conceptually, but modules may interact (e.g., recipes generating shopping list items).  
- **Backend-focused**: Currently only backend, no frontend is included yet. Frontend clients may be mobile apps or web dashboards.  
- **Iterative development**: The project starts as a prototype ("it works"), to be gradually improved to a clean, modular, and production-ready architecture.  
- **Portfolio-oriented**: The goal is to demonstrate professional backend design, API architecture, and scalable coding practices.

## Notes for Future Sessions / AI Assistance

- Any suggestions or code generation should respect the modular design and extensibility.  
- Focus on FastAPI, Pydantic, SQLAlchemy stack patterns.
- The projects will run in a containerized environment, there is a big focus on performance!
- The project is named H.O.M.E.: Household Operations, Management & Essentials.

## Development approach

- Iterative improvements: features, tests, and migrations will be added over time. We'll prefer pragmatic defaults but keep models and code portable.
- Collaboration rules: I will not make structural changes or commit scaffolding without your explicit approval. I'll propose changes, scaffold minimal examples on request, and wait for your sign-off before expanding the codebase.
- **Code quality principles** (all equally important):
  - **Type Safety (mypy)**: Strict type hints throughout the codebase. All code must be checked with mypy to catch type errors early.
  - **SOLID Principles**: Single Responsibility, Open/Closed (extensibility through open/closed principle), Liskov Substitution, Interface Segregation, Dependency Inversion.
  - **Clean Code**: Readable, maintainable code with clear naming conventions and logical structure.
  - **Modularity**: The project is organized into distinct, self-contained modules (tasks, shopping, recipes, calendar, etc.), each encapsulating a specific feature or domain. Modules are designed to be independent but can interact with each other through well-defined interfaces and contracts.
  - **Documentation & Testing**: As we code, we must think about testing and documentation. Code should be well-documented with docstrings, and we plan to write comprehensive tests during and after implementation.

