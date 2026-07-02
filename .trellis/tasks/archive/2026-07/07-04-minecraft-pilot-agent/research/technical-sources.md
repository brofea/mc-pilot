# Technical source notes

These primary sources informed the confirmed PRD. Re-check versions before implementation because APIs and releases can change.

- Minecraft Java Edition 26.2 release notes: <https://www.minecraft.net/en-us/article/minecraft-java-edition-26-2>
- Fabric official site (26.2 support): <https://fabricmc.net/>
- Chinese Minecraft Wiki MediaWiki API: <https://zh.minecraft.wiki/api.php>
- MediaWiki API overview: <https://www.mediawiki.org/wiki/API/zh>
- DeepSeek OpenAI-compatible API: <https://api-docs.deepseek.com/>
- DeepSeek tool calls: <https://api-docs.deepseek.com/guides/tool_calls>
- Qdrant Docker installation: <https://qdrant.tech/documentation/installation/>
- Qdrant payload/filter model: <https://qdrant.tech/documentation/concepts/payload/>
- Minecraft usage guidelines: <https://www.minecraft.net/usage-guidelines>

Key conclusions:

- Target the stable Java 26.2 release and exclude snapshots/pre-releases.
- Keep the Fabric mod thin; share HTTP/WebSocket contracts with the web client.
- Treat Mojang's official version metadata and hashes as the trust root even when a mirror transports bytes.
- Do not redistribute Minecraft JARs or game files; build recipe data locally.
- DeepSeek supports OpenAI-style tool calls, but model identifiers must remain configurable.
- Qdrant payload fields support the version/category/source filtering required by the RAG design.
