# M5: Game Log and Death Advice

## Goal

Detect the local Java 26.2 player session and provide one low-noise DeepSeek suggestion per local-player death.

## Requirements

- Prefer macOS process/log discovery with configurable manual path/version override.
- Tail only appended `latest.log` data and recover from rotation/truncation.
- Identify version and local player; support `zh_cn` and `en_us` death templates.
- Ignore other players and unknown/ambiguous events; deduplicate stable event IDs.
- Make exactly one short DeepSeek call per valid death, with no RAG/recipe tools and no retry spam.
- Emit 2–5 sentence local chat events over WebSocket; disconnected game leaves RAG/recipes usable.

## Acceptance Criteria

- [ ] Chinese and English fixtures identify local deaths and reject other players.
- [ ] Rotation, truncation, restart, and duplicate events are safe.
- [ ] Each event produces no more than one model request.
- [ ] Missing game/model is a visible degraded state, not an application crash.

## Dependencies

M1, M4.
