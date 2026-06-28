# M3: Chinese Wiki RAG

## Goal

Create a reproducible, manually updated Java 26.2 knowledge index from the Chinese Minecraft Wiki.

## Requirements

- Collect configured categories through `https://zh.minecraft.wiki/api.php` with pagination, throttling, retry, cache, and revision-based updates.
- Exclude Bedrock-only, historical, development, and non-content pages.
- Clean and section-aware chunk content; retain URL, page/revision ID, category, version, and timestamps.
- Embed with `BAAI/bge-small-zh-v1.5`; index a staging Qdrant collection and atomically switch after validation.
- Retrieve by dense similarity plus exact title/alias boost.
- Return verified content with citations and structurally separate unverified model supplements.

## Acceptance Criteria

- [ ] An offline existing index remains queryable when Wiki is unavailable.
- [ ] Failed updates preserve the live index.
- [ ] Exact entity names, English aliases, and resource IDs resolve reliably.
- [ ] Sources and revision IDs survive the full retrieval round trip.

## Dependency

M1.
