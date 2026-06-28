# M2: Official Recipe Data and Trees

## Goal

Build a deterministic Java 26.2 recipe catalog and N-level recipe/material tree from Mojang-verified release data.

## Requirements

- Fetch Mojang release metadata; reject non-26.2/non-release versions.
- Download from the official CDN, optionally fall back to configured mirrors, and always verify the official SHA-1.
- Extract recipes, item tags, and required localization without redistributing game files.
- Store normalized recipes in SQLite.
- Compute direct recipes, quantities, byproducts, N-level trees, leaf totals, alternative recipes, tags, cycle limits, and node limits without an LLM.
- Expose typed service/API contracts and test fixtures.

## Acceptance Criteria

- [ ] Hash mismatch and development versions are rejected.
- [ ] A known target produces stable direct and N-level results.
- [ ] Alternative recipes are deterministic and user-switchable.
- [ ] Depth, cycles, tags, and node limits return explicit metadata.
- [ ] No Minecraft JAR or full derived dataset is committed.

## Dependency

M1.
