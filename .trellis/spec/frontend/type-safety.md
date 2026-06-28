# Frontend Contract Safety

Python/Pydantic OpenAPI models are the source of truth. Native JavaScript must validate boundary shape before use.

- API payloads use discriminators such as `type` and stable `snake_case` JSON fields.
- Each module defines small predicate/parser functions for payloads it consumes.
- Unknown event types are ignored with a bounded diagnostic; malformed known events enter an error state.
- Never assume optional nested fields exist.
- Dates are ISO 8601 UTC strings; display formatting happens at the UI edge.
- Do not duplicate backend enums as free-form strings across files; centralize them in one browser module when reused.
