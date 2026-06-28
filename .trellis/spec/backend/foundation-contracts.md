# Foundation Runtime Contracts

## 1. Scope / Trigger

Use this contract whenever changing application startup, health endpoints, settings, SQLite/Qdrant wiring, Docker Compose, or browser readiness display. These paths span infrastructure, storage, API, and UI.

## 2. Signatures

- Application factory: `mc_pilot.app.create_app(settings: Settings | None = None) -> FastAPI`
- Liveness: `GET /health/live -> LivenessResponse`
- Readiness: `GET /health/ready -> ReadinessResponse`
- SQLite probe: `sqlite_is_ready(engine: Engine) -> bool`
- Qdrant probe: `QdrantProbe.is_ready() -> bool`

Real examples: `src/mc_pilot/app.py`, `src/mc_pilot/api/health.py`, and `src/mc_pilot/api/models.py`.

## 3. Contracts

Liveness is process-only:

```json
{"status":"alive","version":"0.1.0"}
```

Readiness always names each dependency and may degrade without killing the process:

```json
{"status":"degraded","components":[{"name":"qdrant","status":"degraded","detail":"Vector database is unavailable."}]}
```

Environment keys use the `MC_PILOT_` prefix. DeepSeek compatibility keys remain `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`. `Settings.safe_summary()` is the only settings representation allowed in HTML/admin responses.

Docker publishes app/Qdrant only on `127.0.0.1`, persists named volumes, and never copies `.env`, project data, Trellis/Codex metadata, tests, or model/game files into the image.

## 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Process serves requests | `/health/live` returns 200 `alive` |
| SQLite unavailable | readiness component is `degraded`; no traceback returned |
| Qdrant unavailable | liveness stays healthy; readiness is `degraded` |
| Secret configured | admin shows only `deepseek_configured: true` |
| Invalid port/timeout | Settings validation fails before application startup |
| App domain failure | standard `{"error": ...}` envelope with request ID |

## 5. Good / Base / Bad Cases

- Good: Docker Compose starts app and Qdrant; readiness reports both `ready`.
- Base: local app starts without Qdrant; pages render and readiness reports one degraded component.
- Bad: a route serializes `Settings` directly, a dependency exception becomes a raw 500 body, or Compose binds `0.0.0.0` on the host.

## 6. Tests Required

- Assert liveness is independent from Qdrant.
- Assert degraded readiness has stable component fields and safe details.
- Assert `/` and `/admin` render without a frontend build.
- Assert `safe_summary()` never contains a configured secret.
- Validate Compose configuration and run the container readiness endpoint before closing an infrastructure milestone.

## 7. Wrong vs Correct

Wrong: make routes construct clients or read environment values directly.

```python
@router.get("/health")
def health() -> dict[str, str]:
    QdrantClient(os.environ["QDRANT_URL"]).get_collections()
    return {"status": "ok"}
```

Correct: the application factory owns dependencies and routes consume narrow typed probes.

```python
qdrant_ready = await run_in_threadpool(request.app.state.qdrant_probe.is_ready)
```
