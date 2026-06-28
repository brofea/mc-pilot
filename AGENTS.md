<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

## Minecraft Pilot milestone commands

When the user says `开始 M1 任务` through `开始 M9 任务` (spacing and case may vary):

1. Resolve the matching task under `.trellis/tasks/07-04-m<N>-*/`.
2. Read its `prd.md`, the parent PRD, and referenced spec/research context.
3. If another milestone is active, report its state; do not silently mark unfinished work complete.
4. Run `python3 ./.trellis/scripts/task.py start <matching-task-dir>`.
5. Follow the Trellis phase workflow and implement only that milestone's scope.

Milestone map: M1 foundation, M2 recipes, M3 Wiki RAG, M4 agent, M5 game log, M6 web/admin, M7 verification, M8 report, M9 Fabric mod.
