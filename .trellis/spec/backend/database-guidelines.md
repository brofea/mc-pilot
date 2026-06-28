# Database Guidelines

SQLite stores structured local application data; Qdrant stores Wiki vectors and retrieval payloads. Do not blur these roles.

## SQLite

- Use SQLAlchemy 2.x typed models and explicit sessions.
- Keep transaction ownership in the storage/service boundary; routes never call `commit()`.
- Use plural `snake_case` table names and UTC ISO timestamps.
- Schema changes require an explicit migration before persisted user data exists; never mutate tables at request time.
- Recipe imports use a staging database or transaction and become visible only after validation succeeds.

## Qdrant

- Collection aliases provide atomic staging-to-live swaps.
- Every point includes source URL, page/revision IDs, category, game version, chunker version, and embedding model revision.
- Create payload indexes for every field used in filters.
- Refuse to query an index whose embedding dimension/model metadata differs from configured settings.

## Forbidden

- Raw SQL assembled with string interpolation.
- Qdrant as the source of truth for recipes or budgets.
- SQLite connections shared across async tasks without a scoped session.
- Destructive rebuilds of the live collection before a staging collection passes validation.
