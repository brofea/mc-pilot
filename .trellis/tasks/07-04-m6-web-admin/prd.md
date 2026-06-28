# M6: Web Client and Developer Admin

## Goal

Deliver the simple local web product and a loopback-only diagnostic dashboard.

## Requirements

- Chat-centered main page with RAG citations, deterministic recipe tree rendering, connection state, and transient death messages.
- Native JavaScript HTTP/WebSocket integration with bounded reconnect and event deduplication.
- `/admin` system, game/log, RAG/Qdrant, recipe, LLM/agent, usage, configuration, and audit panels.
- Safe diagnostic actions for reconnect, incremental sync, rebuild, health checks, and redacted export.
- Bind only to loopback, never render secrets/raw internal errors, and confirm state-changing admin actions.

## Acceptance Criteria

- [ ] Core flows work without a Node build step.
- [ ] Loading/empty/degraded/error states are visible and accessible.
- [ ] Admin data is redacted and non-loopback access is rejected.
- [ ] Chat and recipe results remain consistent with backend schemas.

## Dependencies

M1 through M5.
