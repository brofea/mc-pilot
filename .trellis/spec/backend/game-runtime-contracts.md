# Game Runtime and Local Client Contracts

## 1. Scope / Trigger

Use this contract when changing FastAPI lifespan, game log detection, death advice,
WebSocket delivery, Docker mounts, loopback admin access, or the Fabric 26.2 client.

## 2. Signatures

- `GameStateService.start(log_path: str | None = None) -> None`
- `GameStateService.stop() -> None` is asynchronous and must be awaited.
- `GameStateService.add_advice_callback(callback)` and
  `remove_advice_callback(callback)` bracket each WebSocket connection.
- `GET /api/game-state` exposes the current degraded/connected snapshot.
- `WS /ws` emits discriminated `state` and `death_advice` events.

## 3. Contracts

- `MC_PILOT_GAME_LOG_PATH` is the in-process `latest.log` path.
- `MC_PILOT_MINECRAFT_DIR` is Compose-only and is mounted read-only at `/minecraft`.
- Lifespan starts the game service after SQLite initialization and awaits shutdown
  before disposing shared dependencies.
- Missing log/model is a degraded state: no listener/model call, while recipes and RAG remain available.
- Docker publishes the app on host loopback. Inside Docker Desktop, a legitimate host
  request may have a private gateway source IP; admin access additionally requires a
  loopback Host header.
- Minecraft 26.2 uses Java 25, `net.fabricmc.fabric-loom` 1.17, Gradle 9.5.1,
  Fabric Loader 0.19.3 and Fabric API 0.154.0+26.2. Build with the committed wrapper.

## 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Log path missing | listener remains inactive; state is `disconnected` |
| API key missing | death advice disabled; application remains healthy |
| WebSocket disconnects | callback removed and client count decremented once |
| Host header is not loopback | admin API returns 403 |
| Docker gateway + loopback Host | admin API is allowed |
| Repeated identical log line | stable event ID suppresses duplicate advice |
| Fabric built with obsolete Yarn/Loom | reject in review; wrapper build must pass |

## 5. Good / Base / Bad Cases

- Good: Docker mounts the macOS game directory read-only, detects new log lines and
  pushes one short suggestion for a local-player death.
- Base: Minecraft or DeepSeek is absent; the web app, recipes and RAG still work.
- Bad: only an admin button starts the listener, a disconnected socket retains its
  callback, or Compose has no host log mount.

## 6. Tests Required

- Lifespan integration test asserts listener running inside `TestClient` and stopped after exit.
- No-key test asserts `advice_enabled` is false.
- WebSocket test asserts callback count returns to zero after disconnect.
- Parser test asserts the same raw log line has the same event ID across processing times.
- Compose test asserts a read-only `/minecraft` bind and configured container log path.
- Runtime acceptance checks container readiness, admin API, disconnected game state and
  `./gradlew clean build` output/JAR.

## 7. Wrong vs Correct

Wrong: construct `GameStateService()` without a model and never start it from lifespan.

```python
services["game"] = GameStateService()
```

Correct: inject the optional death client and configured path, then own start/stop in lifespan.

```python
services["game"] = GameStateService(
    deepseek_client=death_client,
    configured_log_path=settings.game_log_path,
)
await services["game"].start()
try:
    yield
finally:
    await services["game"].stop()
```
