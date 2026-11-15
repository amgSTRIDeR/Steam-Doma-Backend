# Project Context

## Purpose

- **What it does:** Backend for Steam Дома, an educational team project developed as part of RS School. The application is a Steam-inspired digital game marketplace with a catalog of approximately 5,000 games imported from Steam data.
- **Main use cases:**
  - Browse, search, filter, sort, and view games.
  - Retrieve genres, categories, platforms, prices, discounts, and game details.
  - Register, authenticate, and manage users.
  - Manage shopping carts and their contents.
  - Provide role-based authorization for users and administrators.
  - Allow administrators to manage games and users.
  - Record administrative actions in an audit log.
  - Provide a GraphQL API for the React frontend.
  - User registration with mandatory acceptance of the Terms of Service.
  - Self-service account deletion and personal data removal.
- **Out of scope:**
  - Real payments and Steam purchases.
  - User-submitted games and content moderation.
  - A separate TEST/PROD mode within the application.
  - Direct database access from the frontend.
  - Unnecessary microservices or infrastructure complexity.

## Stack and entry points

- **Language(s) and versions:**
  - Python 3.15.
  - MongoDB Community Server 9.0 for local development.
- **Framework(s) / package manager(s):**
  - FastAPI — HTTP application framework (planned).
  - Strawberry GraphQL — GraphQL schema and resolvers (planned).
  - PyMongo Async — asynchronous MongoDB driver (planned).
  - pytest — automated testing (planned).
  - Ruff — linting and formatting (planned).
  - Python dependency management — not yet configured.
  - Docker Compose and VS Code Dev Containers.
- **Application entry points:**
  - `src/steam_doma/main.py` — planned FastAPI application entry point.
  - `/graphql` — planned primary API endpoint.
  - `/health` — planned health-check endpoint.
  - `scripts/import_games.py` — planned Steam dataset import script.

## Repository layout

- **Application code:** Planned structure under `src/steam_doma/`:
  - `config/` — configuration and environment settings.
  - `db/` — MongoDB connection and database access.
  - `graphql/` — GraphQL schema, queries, and mutations.
  - `modules/games/` — game catalog and filtering.
  - `modules/auth/` — authentication and authorization.
  - `modules/users/` — user management.
  - `modules/cart/` — shopping cart operations.
  - `modules/admin/` — administrative operations and audit logging.
- **Tests:** `tests/` — planned pytest tests, including unit and integration tests.
- **Configuration / generated code:**
  - `.devcontainer/devcontainer.json` — VS Code Dev Container configuration.
  - `compose.yaml` — local Python development container and MongoDB.
  - `pyproject.toml` — planned Python project and tool configuration.
  - `.env.example` — planned environment variable documentation.
  - MongoDB data stored in a persistent Docker volume.

## Architecture and constraints

- **Module responsibilities and dependency direction:**
  - Frontend communicates with the backend through GraphQL.
  - GraphQL resolvers delegate business logic to application services.
  - Services interact with MongoDB through dedicated database access code.
  - Database access must not be implemented directly inside GraphQL resolvers.
  - Use asynchronous database operations where appropriate.
  - Keep modules focused on their respective business domains.
  - Prefer a modular monolith over microservices.
- **Data model:**
  - MongoDB is the primary NoSQL database.
  - Planned collections: `games`, `users`, `carts`, `audit_logs`.
  - Orders may be introduced if checkout becomes part of the application.
  - Game documents originate from an imported Steam JSON dataset.
  - Preserve useful nested Steam data without unnecessary normalization.
  - Use Steam `appid` as a stable game identifier.
  - Some Steam fields may be missing, null, or have different structures.
  - Missing prices must not automatically be interpreted as free games.
  - Store the accepted Terms of Service version and acceptance timestamp
  in the user document.
  - User accounts and shopping carts must support complete account deletion.
  - Personal data in audit logs must be anonymized or removed when required,
    subject to applicable legal retention obligations.
- **Interfaces or behaviors that must remain stable:**
  - GraphQL is the preferred API for application functionality.
  - The React frontend must never connect directly to MongoDB.
  - Authentication and role checks must be enforced on the backend.
  - Admin-only operations must reject unauthorized users.
  - Shopping cart data must remain associated with the correct user.
  - Audit logs must preserve information about administrative actions.
  - Game identifiers must remain consistent during imports and updates.
  - Secrets and database credentials must never be committed.
  - Registration must be rejected unless the user accepts the Terms of Service.
  - The Privacy Policy must be accessible during registration.
  - Users must be able to delete their own accounts without administrator involvement.
  - Account deletion must require authentication and identity re-verification.
  - Users must never be able to delete another user's account.
  - Account deletion must revoke active sessions and invalidate refresh tokens.
  - Deleting an account must remove associated personal data unless retention
  is legally required.
- **Deployment constraints:**
  - Local development uses Docker Compose and MongoDB.
  - Production deployment is planned on Microsoft Azure.
  - Azure Container Apps is the planned backend hosting platform.
  - Azure DocumentDB is the preferred managed NoSQL database candidate, subject to MongoDB driver and feature compatibility verification.
  - Keep infrastructure configuration separate from application business logic.
- **Paths not to edit manually:**
  - `.git/`
  - `.venv/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `.ruff_cache/`
  - Generated files and dependency lockfiles, except through their corresponding tools.

## Local verification

- **Install / setup:**
  - Install Docker Engine, Docker Compose, VS Code, and the Dev Containers extension.
  - Open the repository in VS Code.
  - Run `Dev Containers: Reopen in Container`.
  - Check configuration using `docker compose config --quiet`.
  - Start services using `docker compose up -d`.
  - Verify Python using `python --version` inside the backend container.
  - Verify MongoDB connectivity using `docker compose exec mongo mongosh --eval "db.adminCommand({ ping: 1 })"` from the host.
- **Focused tests:** Planned: `python -m pytest tests/<test_file>.py`.
- **Full test suite:** Planned: `python -m pytest`.
- **Lint / type checks:**
  - Planned: `ruff check .`.
  - Planned: `ruff format --check .`.
  - Static type checking is not yet configured.
- **Build:**
  - The initial development environment uses a prebuilt Python Dev Container image.
  - Application packaging and the production Docker image are not yet implemented.
  - Azure deployment and CI/CD workflows are not yet configured.

## Known limitations

- The repository is in its initial setup stage.
- The application structure and Python dependencies are not yet fully implemented.
- GraphQL schema and authentication mechanisms are not yet finalized.
- Steam data requires validation and preprocessing before importing into MongoDB.
- Some games lack prices, descriptions, screenshots, or release dates.
- Real payment processing is not planned.
- Azure infrastructure has not yet been provisioned.
- Production database compatibility and security configuration require validation before deployment.
- Local development currently uses one MongoDB instance; an additional test database may be configured for isolated automated tests.