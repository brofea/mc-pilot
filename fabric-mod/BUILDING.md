# Build Requirements

## Prerequisites

- **JDK 25** (required by Minecraft 26.2)
- **Gradle 9.5.1** (provided by the committed wrapper)
- **Fabric Loom 1.17** (included via Gradle plugin)

## Environment Setup

```bash
# Ensure JDK 25 is used
export JAVA_HOME=/path/to/jdk-25

# Verify
java -version  # should show JDK 25
./gradlew --version  # should show Gradle 9.5.1

# Build
cd fabric-mod
./gradlew clean build
```

## Known Issues

- Minecraft 26.2 class files use Java 25 (major version 69).
- Use the committed wrapper rather than a host-installed Gradle version.
