# M7: Verification and Course Delivery

## Goal

Make the web MVP reproducible and produce evidence for every required course capability.

## Requirements

- About ten focused automated tests covering recipe graphs, official hashes, bilingual death parsing/deduplication, agent limits, RAG evidence boundaries, degradation, and redaction.
- Separate opt-in DeepSeek connectivity/tool-call smoke tests.
- Ruff, mypy, pytest, Docker build/config/run, and macOS log-mount verification.
- README, `.env.example`, architecture/tool-contract docs, prompts, eval samples, sanitized logs, and demonstration commands.
- Capture success, failure, refusal, cost, and environment evidence for the report.

## Acceptance Criteria

- [ ] Default verification is offline, deterministic, and green.
- [ ] Real-model tests run explicitly and report sanitized evidence.
- [ ] A new user can follow README commands to reproduce the web MVP.
- [ ] No secret, game file, raw Wiki dump, model weight, or private log is tracked.

## Dependencies

M1 through M6.
