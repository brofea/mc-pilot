# Frontend Quality Guidelines

- Progressive enhancement, no Node build pipeline, and no inline event handlers.
- Keep browser modules small, explicit, and dependency-free until a concrete need proves otherwise.
- All fetch/WebSocket paths show loading, success, empty, degraded, and failure states.
- Escape untrusted content and keep secrets out of HTML, JS, data attributes, and browser logs.
- Bind the application to loopback; admin actions require confirmation and server-side authorization checks.
- Test critical rendering and API behavior through FastAPI integration tests; add browser automation only for flows that unit/integration tests cannot prove.
- Verify responsive layout, keyboard operation, visible focus, reduced-motion behavior, and readable contrast.

Forbidden: `innerHTML` with external content, infinite reconnect loops, silent promise rejection, duplicated fetch wrappers, and UI-only enforcement of security rules.
