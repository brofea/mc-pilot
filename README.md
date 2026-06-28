# Minecraft Pilot Agent

Minecraft Pilot is a local assistant for Minecraft Java Edition 26.2. The required web MVP will combine Chinese Wiki RAG, deterministic recipe trees, and concise local-player death advice. A thin Fabric client is planned as an optional second phase.

This is an unofficial, educational project. It is not approved by or associated with Mojang or Microsoft.

## M1 foundation

The current milestone provides the typed FastAPI skeleton, local web/admin placeholders, SQLite bootstrap, Qdrant readiness checks, Docker Compose, and baseline quality checks. Game, RAG, recipe, and model behavior arrive in later milestones.

## Local development

Python 3.12 is required. This project deliberately uses pip and an isolated `.venv`; it does not use conda.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
docker compose up -d qdrant
.venv/bin/uvicorn mc_pilot.app:create_app --factory --reload
```

Open <http://127.0.0.1:8000/> and <http://127.0.0.1:8000/admin>.

## Docker

```bash
docker compose up --build
```

Only loopback ports `8000` and `6333` are published. Qdrant and application state use named Docker volumes.

## Verification

```bash
.venv/bin/ruff check .
.venv/bin/mypy src tests
.venv/bin/pytest -q
docker compose config --quiet
```

Never commit `.env`, Minecraft game files, Wiki dumps, model weights, Qdrant data, or private game logs.
