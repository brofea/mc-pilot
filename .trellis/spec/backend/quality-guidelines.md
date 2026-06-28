# Backend Quality Guidelines

- Python 3.12, `from __future__ import annotations`, full public-function annotations, and strict mypy-compatible code.
- Pydantic models own external contracts; frozen dataclasses or immutable domain models own internal state.
- Prefer deep modules with small typed interfaces. Do not thread raw dictionaries through layers.
- Dependencies must solve a confirmed requirement; pin direct dependencies and avoid framework bundles.
- All network and file operations have timeouts/bounds and injectable adapters for tests.
- Deterministic algorithms never call the LLM.

## Tests

- Default tests are offline and deterministic.
- Real DeepSeek and live Wiki tests require explicit markers/commands.
- Every parser includes positive, invalid, and boundary fixtures.
- Every bug fix adds a regression test.
- Test behavior and contracts, not private implementation details.

## Forbidden

- `Any` as an escape hatch, mutable global state, import-time network calls, `sys.path` hacks, secrets in defaults, unbounded agent loops, and broad catches that hide defects.
- Conda commands or environment files; this repository uses pip, `.venv`, and Docker by explicit project decision.
