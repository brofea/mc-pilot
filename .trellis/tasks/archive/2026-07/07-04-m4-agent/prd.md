# M4: DeepSeek Agent and Tool Contracts

## Goal

Implement a bounded single-agent loop that uses DeepSeek tool calls for Wiki and recipe requests while keeping deterministic work in code.

## Requirements

- Configurable DeepSeek OpenAI-compatible client and explicit real-model connectivity command.
- MCP-style `wiki_search` and `recipe_query` descriptions, Pydantic inputs/outputs, error semantics, and safety boundaries.
- State machine: received, deciding, tool_running, observing, answered/stopped/failed.
- Tool whitelist, validated arguments, at most four model turns, timeout/token budgets, and short six-turn session memory.
- Natural `/pilot` routing plus deterministic `wiki`, `recipe`, `status`, `help`, and `clear` shortcuts.
- Structured, redacted traces and usage accounting.

## Acceptance Criteria

- [ ] Model connectivity reports model, latency, status, and token usage without secrets.
- [ ] Tool selection and failure exits are visible in trace output.
- [ ] Unknown tools, invalid arguments, budgets, and loop limits stop safely.
- [ ] Fixed subcommands bypass unnecessary LLM routing.

## Dependencies

M1, M2, M3.
