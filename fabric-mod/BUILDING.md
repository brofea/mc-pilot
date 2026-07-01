# Build Requirements

## Prerequisites

- **JDK 25** (required by Minecraft 26.2)
- **Gradle 9.6+** (needed for JDK 25 class file support)
- **Fabric Loom 1.10+** (included via Gradle plugin)

## Environment Setup

```bash
# Ensure JDK 25 is used
export JAVA_HOME=/path/to/jdk-25

# Verify
java -version  # should show JDK 25
gradle --version  # should show Gradle 9.6+

# Build
cd fabric-mod
gradle build
```

## Known Issues

- Gradle 8.x cannot parse JDK 25 class files (major version 69)
- Fabric Loom 1.10.5's remapper may have issues with newer JDK bytecode
- If `gradle build` fails at `:remapJar`, try upgrading Fabric Loom or using a newer Gradle
- As of 2026-07, building for Minecraft 26.2 requires the very latest toolchain

## Test Build (with Minecraft 1.21.4)

To verify the mod code structure compiles correctly:

```bash
gradle build -Pminecraft_version=1.21.4 \
  -Pyarn_mappings=1.21.4+build.3 \
  -Ploader_version=0.16.10 \
  -Pfabric_version=0.112.0+1.21.4
```
