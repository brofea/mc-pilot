# Minecraft Pilot Fabric Mod

Lightweight Fabric client mod for Minecraft Java Edition 26.2 that connects to the local Pilot Agent backend.

## Features

- `/pilot <query>` - Query the Agent (natural language)
- `/pilot wiki <term>` - Search the Wiki knowledge base
- `/pilot recipe <item_id>` - Query crafting recipes
- `/pilot status` - Check backend connection status
- `/pilot clear` - Clear conversation memory
- Real-time death advice via WebSocket
- All messages stay local (never sent to multiplayer servers)
- No API keys stored in the mod

## Build

```bash
cd fabric-mod
./gradlew build
```

Copy `build/libs/pilot-mod-0.1.0.jar` to your Fabric mods folder.

## Configuration

The mod connects to `http://127.0.0.1:8000` by default. Ensure the Pilot backend is running:

```bash
docker compose up -d
# or
.venv/bin/uvicorn mc_pilot.app:create_app --factory
```

## Architecture

```
[Fabric Mod] --HTTP POST /api/chat--> [Pilot Backend] --HTTPS--> [DeepSeek API]
              <--HTTP response------                                          |
              --WebSocket /ws------>                                        [Qdrant]
              <--WS death_advice---                                          [SQLite]
```

The mod is a thin UI adapter. All AI logic, RAG, recipes, and game state parsing live in the Python backend. The mod only handles:
1. Command registration and routing
2. HTTP queries to the backend
3. WebSocket connection for real-time events
4. Local chat message rendering
