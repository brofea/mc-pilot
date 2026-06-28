# Backend Directory Structure

Use a `src` layout and keep FastAPI transport separate from domain logic.

```text
src/mc_pilot/
├── app.py              # application factory only
├── config.py           # Pydantic settings and constants
├── api/                # HTTP/WebSocket adapters
├── admin/              # diagnostics read models and actions
├── agent/              # state machine and tool contracts
├── game/               # process/log/event adapters
├── rag/                # ingestion, chunking, embedding, retrieval
├── recipes/            # official data extraction and graph algorithms
├── storage/            # SQLite and Qdrant adapters
├── templates/          # Jinja2 templates
└── static/             # browser JS and CSS
```

- Domain modules expose typed services; route handlers translate HTTP to those services.
- External systems sit behind adapters. Do not import FastAPI inside recipe, RAG, game, or agent domain modules.
- Keep modules focused; split files approaching 300 lines when they own multiple kinds of knowledge.
- Shared code belongs in a named domain module, not a catch-all `utils.py`.
- Tests mirror the package under `tests/`; deterministic fixtures live under `tests/fixtures/`.
- Scripts that operators run live in `scripts/` and call public package APIs.

Use `snake_case.py` for modules, `PascalCase` for types, and precise verb phrases for operations.

Current examples: `src/mc_pilot/app.py` owns composition, `src/mc_pilot/api/health.py` owns transport, and `src/mc_pilot/storage/` hides persistence clients.
