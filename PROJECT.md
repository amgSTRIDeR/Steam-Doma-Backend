# Project Context

## Purpose

- **What it does:** Backend API for Steam Doma, an educational RS School project. This backend is developed individually. The team-developed frontend is maintained in a separate repository.
- **Main use cases:**
  - Browse, search, filter, sort, and paginate the Steam-inspired game catalog.
  - Retrieve game details and available catalog filters.
  - Provide a GraphQL API for the separate frontend and a health endpoint for operations.
- **Out of scope for this backend:**
  - Frontend application code.
  - User registration, authentication, shopping carts, and administration features not present in this repository.
  - Real payments and Steam purchases.
  - Direct database access from the frontend.
  - Unnecessary microservices or infrastructure complexity.

## Stack and entry points

- **Language and version:** Python `>=3.15,<3.16`.
- **Frameworks and tools:** FastAPI, Strawberry GraphQL, PyMongo Async, MongoDB, uv, pytest, Ruff, Docker Compose, and GitHub Actions.
- **Application entry points:**
  - `src/steam_doma/main.py` — FastAPI application, GraphQL schema, database lifecycle, CORS, and `/health`.
  - `/graphql` — GraphQL endpoint.
  - `scripts/seed_games.py` — explicit game catalog import.
  - `scripts/setup_game_indexes.py` — game index setup.
  - `scripts/check_azure_documentdb.py` — Azure DocumentDB connectivity check.

## Repository layout

- `src/steam_doma/modules/games/` — game catalog GraphQL types, queries, filters, details, normalization, and repository.
- `tests/` — API, catalog, repository, sorting, release-date, and seed tests.
- `scripts/` — catalog seeding, index setup, release-date maintenance, and Azure database diagnostics.
- `docs/graphql-catalog.md` — GraphQL catalog API reference.
- `compose.yaml` — local backend development container and MongoDB service.
- `.devcontainer/` — VS Code Dev Container configuration.
- `Dockerfile` — production application image.
- `.github/workflows/backend-ci.yml` — backend checks and Azure deployment workflow.
- `pyproject.toml` and `uv.lock` — Python project configuration and locked dependencies.

## Architecture and constraints

- The frontend is a separate, team-maintained repository. It calls this backend over HTTPS and GraphQL; it must not connect directly to MongoDB.
- GraphQL resolvers use the game repository for database access.
- The application connects to MongoDB-compatible storage at startup and closes the client at shutdown.
- The local database is MongoDB Community Server. The hosted backend is configured to use Azure DocumentDB.
- The database contains the game catalog and seeding history. Game data originates from the Steam JSON dataset; `steam_appid` is the stable Steam identifier.
- Catalog/API behavior:
  - `/graphql` exposes `ping`, `games`, `game`, and `catalogFilters`.
  - `/health` checks database connectivity.
  - The catalog API currently has no user authentication or authorization; treat it as public.
  - Missing prices must not be interpreted as free games.
  - Keep credentials out of source control.
- CORS origins are configured through `CORS_ORIGINS`; local defaults permit the Vite origins on port 5173.

## Deployment

- The backend is deployed to Azure Container Apps and uses Azure DocumentDB.
- `.github/workflows/backend-ci.yml` runs linting, formatting checks, tests, and image verification for pull requests to `main`. Pushes to `main` publish the image to Azure Container Registry, deploy it to Azure Container Apps, and run health and GraphQL smoke tests.
- The frontend is maintained in a separate repository by the project team and is planned for an independent Azure deployment. Its public origin must be allowed by the backend CORS configuration.
- Keep cloud infrastructure configuration separate from application business logic. Do not initialize or seed the production database as part of application startup or deployment.

## Local verification

- Install Docker with Compose, VS Code, and the Dev Containers extension, or install uv and Python 3.15 locally.
- In VS Code, use **Dev Containers: Reopen in Container**. Alternatively, run `uv sync --locked`.
- Configure `.env` with the local MongoDB connection and database name. `compose.yaml` provides the `mongo` service at `mongodb://mongo:27017` inside the Compose network.
- Check Compose configuration with `docker compose config --quiet`.
- Run tests with `uv run --env-file .env pytest -v`.
- Run lint and format checks with `uv run ruff check .` and `uv run ruff format --check .`.
- Build the production image with `docker build -t steam-doma-backend:local .`.

## Known limitations

- Catalog data is imported and may be outdated; prices and release statuses are not refreshed live.
- No live currency conversion is implemented. Missing prices remain distinct from free games.
- User accounts, authentication, carts, payments, and administrative APIs are not implemented in this backend.
- Validate Azure DocumentDB compatibility and production security settings when changing database features or deployment configuration.
