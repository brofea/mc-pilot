# Logging Guidelines

Emit JSON-compatible structured logs through the standard `logging` API. Human-readable rendering may be enabled in development.

Required common fields: `timestamp`, `level`, `event`, `request_id`, `component`, and `duration_ms` when applicable.

Use levels consistently:

- `DEBUG`: bounded diagnostics such as counts and state transitions.
- `INFO`: startup, readiness, tool completion, index swaps, game connect/disconnect.
- `WARNING`: degraded dependencies, budget warnings, parse misses, bounded retries.
- `ERROR`: an operation failed and cannot fulfill its contract.

Never log API keys, authorization headers, complete prompts, complete Wiki bodies, full chat history, full filesystem paths, or raw `latest.log` lines. Log hashes, basenames, redacted snippets, counts, tool names, status, tokens, and error codes instead.

Agent traces record state transitions and summarized tool arguments/results. Admin diagnostics consume the same structured events; do not create a second ad-hoc tracing format.
