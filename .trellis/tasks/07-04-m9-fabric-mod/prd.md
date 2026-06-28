# M9: Optional Fabric 26.2 Mod

## Goal

Add a thin Fabric 26.2 client that reuses the completed local backend as a second UI and structured game-event source.

## Requirements

- Client-local `/pilot` natural language and optional subcommands; never send commands/replies to the server.
- HTTP for queries and WebSocket for connection/events/replies.
- Render concise replies in the local chat HUD and capture structured local death events.
- Never store API keys or connect directly to DeepSeek/Qdrant.
- Backend disconnect must not affect Minecraft and must produce one quiet local status.

## Acceptance Criteria

- [ ] `/pilot` commands and replies remain local in multiplayer.
- [ ] Web and Mod receive consistent backend results.
- [ ] Structured death events remove dependence on text regex for the Mod path.
- [ ] Disconnect/reconnect is bounded and safe.

## Dependencies

M1 through M7. This task is optional and does not block the web MVP.
