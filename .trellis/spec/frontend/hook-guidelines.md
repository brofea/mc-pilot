# Browser Module and Data-Fetching Guidelines

There are no React hooks. Stateful browser behavior is implemented as small ES modules initialized from page entry points.

- `api.js` owns JSON fetch, request IDs, timeouts, and error-envelope parsing.
- WebSocket code exposes `connect()`, `close()`, and typed event dispatch; reconnect uses capped exponential backoff and jitter.
- Initialization functions are idempotent so page restoration does not register duplicate listeners.
- Use `AbortController` for replaceable requests and page unload cleanup.
- Do not poll when a WebSocket event exists; admin-only slow health refresh is allowed.
- Never send ordinary Minecraft/server chat to the backend.
