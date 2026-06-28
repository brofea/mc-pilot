# M1: Engineering and Docker Foundation

## Goal

Create the smallest production-shaped skeleton that starts locally and in Docker, exposes health/readiness and placeholder web/admin pages, validates configuration, persists local state, and can be extended by later milestones without restructuring.

## Requirements

- Python 3.12 `src` package using FastAPI, Pydantic Settings, Jinja2, SQLAlchemy/SQLite, structured logging, Qdrant client, pytest, Ruff, and mypy.
- Application factory with `/`, `/admin`, `/health/live`, and `/health/ready`.
- Readiness reports component states without exposing secrets; Qdrant may be degraded while liveness remains healthy.
- Dockerfile and Docker Compose with an app service, pinned Qdrant image, health checks, loopback-only published ports, and persistent volumes.
- `.env.example`, pip requirements, developer commands, minimal templates/CSS/JS, and an initial README.
- No conda files or commands.

## Acceptance Criteria

- [ ] Local `.venv` installation can import and start the application.
- [ ] `docker compose config` succeeds and exposes the web and Qdrant ports only on `127.0.0.1`.
- [ ] Liveness returns HTTP 200; readiness returns typed component states.
- [ ] Home and admin pages render without a frontend build step.
- [ ] SQLite schema/bootstrap and Qdrant configuration are isolated behind storage adapters.
- [ ] Ruff, mypy, and baseline offline tests pass.

## Out of Scope

- Wiki ingestion, recipe extraction, DeepSeek calls, live game detection, production UI, and Fabric code.
