# Backend Development Guidelines

These rules govern the Python 3.12 FastAPI backend, data pipelines, agent runtime, and tests.

## Pre-Development Checklist

1. Read [Directory Structure](./directory-structure.md).
2. Read [Error Handling](./error-handling.md) and [Logging](./logging-guidelines.md) for every API or background job.
3. Read [Database](./database-guidelines.md) for SQLite or Qdrant changes.
4. Read [Quality](./quality-guidelines.md) before adding dependencies or tests.
5. Read the shared cross-layer guide when a schema is consumed by web, admin, or Fabric.
6. Read [Foundation Runtime Contracts](./foundation-contracts.md) for startup, health, settings, Docker, SQLite, or Qdrant changes.

## Quality Check

- `ruff check .`
- `mypy src`
- `pytest -q`
- Confirm secrets and raw game logs are absent from logs and API responses.

## Guides

| Guide | Owns |
|---|---|
| [Directory Structure](./directory-structure.md) | Package and module boundaries |
| [Database](./database-guidelines.md) | SQLite and Qdrant persistence |
| [Error Handling](./error-handling.md) | Domain failures and API errors |
| [Logging](./logging-guidelines.md) | Structured, redacted telemetry |
| [Quality](./quality-guidelines.md) | Typing, tests, dependencies and review |
| [Foundation Contracts](./foundation-contracts.md) | Executable startup, health, settings and Docker contracts |
