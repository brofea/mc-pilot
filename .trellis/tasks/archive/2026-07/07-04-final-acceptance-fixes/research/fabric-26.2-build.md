# Fabric 26.2 build compatibility

## Sources

- Fabric 26.2 release guidance: https://fabricmc.net/2026/06/15/262.html
- Fabric developer version selector: https://fabricmc.net/develop/

## Findings

- Minecraft 26.2 development requires Java 25 bytecode support.
- Fabric recommends Loom 1.17 and Gradle 9.5.1 for 26.2.
- Current recommended runtime dependencies are Fabric Loader 0.19.3 and Fabric API 0.154.0+26.2.
- The existing Loom 1.10 configuration fails while merging Java 25 class files with `Unsupported class file major version 69`.

## Decision

Upgrade to the official 26.2 toolchain and commit the Gradle 9.5.1 wrapper so builds do not depend on a host-installed Gradle version.
