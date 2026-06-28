# State Management

Use local DOM/module state; no global state library.

- Server state remains authoritative and is fetched through APIs.
- Connection state is one explicit enum: `connecting`, `connected`, `degraded`, `disconnected`.
- Keep the active chat session ID in memory; do not persist chat history to localStorage.
- URL query parameters may represent shareable recipe inputs such as item, quantity, and depth.
- Derive rendered state from the latest validated API payload; do not maintain parallel copies in unrelated modules.
- WebSocket events carry stable IDs and are deduplicated before display.
