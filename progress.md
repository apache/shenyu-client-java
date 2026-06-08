# Client Split Migration Progress

## Baseline

- Working branch: `split-client-jdk8-base`
- Base branch: `origin/2.7.0.1-jdk8-release`
- Goal: keep the split client repository JDK 8 compatible while preparing it to absorb client-only changes from the main ShenYu repository.

## Done

- Selected the existing `2.7.0.1-jdk8-release` branch as the migration base because it already preserves Java 8 source level and Apache release metadata.
- Added the MCP client module from the main ShenYu repository.
- Rebased MCP module POMs onto `shenyu-client-java` and removed Spring Boot 3 / springdoc starter coupling.
- Added MCP registration DTO, disruptor subscriber, RPC/data types, and HTTP register path support in `shenyu-client-core`.
- Added a Java 8 compatible `RequestMethodUtils` for MCP method and parameter discovery.
- Added the Spring Boot starter client modules from the main ShenYu repository.
- Rebased starter POMs onto this split client repo and rewired imports to `shenyu-client-core`.
- Restored the beat register client and beat Spring Boot starter.
- Restored the registry API module needed by instance registration.
- Restored Spring MVC, gRPC, and Spring WebSocket discovery instance auto-configuration.
- Added the minimal client-core DTO/config/registry support needed by beat and discovery without pulling in the full main-repo `shenyu-common` module.
- Updated GitHub Actions CI to run the Maven build on JDK 8, 17, 21, 23, and 25.
- Kept the SOFA starter test dependency on the JDK 8 compatible SOFA Boot 3.1.4 line.
- Upgraded JaCoCo to 0.8.15 so coverage instrumentation recognizes JDK 25 class files.
- Overrode Byte Buddy test dependencies to 1.18.10 so Mockito 3.x tests can run on JDK 21, 23, and 25 while preserving JDK 8 runtime compatibility.

## Verification

- `./mvnw -pl shenyu-client-mcp/shenyu-client-mcp-register -am -DskipTests compile` passed.
- `./mvnw -pl shenyu-spring-boot-starter-client/shenyu-spring-boot-starter-client-beat -am -DskipTests compile` passed.
- `./mvnw -DskipTests compile` passed.
- `./mvnw -DskipTests test` passed.
- `./mvnw -pl shenyu-spring-boot-starter-client/shenyu-spring-boot-starter-client-springmvc -am test` passed.
- `./mvnw test` passed across the full 30-module reactor.
- `JAVA_HOME=$(/usr/libexec/java_home -v 1.8) ./mvnw -B clean test -Prelease` passed across the full 30-module reactor.
- `JAVA_HOME=$(/usr/libexec/java_home -v 17) ./mvnw -B clean test -Prelease` passed across the full 30-module reactor.
- `JAVA_HOME=$(/usr/libexec/java_home -v 21) ./mvnw -B clean test -Prelease` passed across the full 30-module reactor.
- `JAVA_HOME=$(/usr/libexec/java_home -v 25) ./mvnw -B clean test` passed across the full 30-module reactor after the JaCoCo and Byte Buddy upgrades.
- Downloaded Temurin JDK 23.0.2+7 from Adoptium to `/tmp/shenyu-jdks`, verified SHA256 `749993e751f085c7ae713140066a90800075e4aeedfac50a5ed0c5457131c5a0`, and ran `JAVA_HOME=/tmp/shenyu-jdks/jdk-23.0.2+7/Contents/Home ./mvnw -B clean test` successfully across the full 30-module reactor.
- Re-ran `JAVA_HOME=$(/usr/libexec/java_home -v 1.8) ./mvnw -B clean test` successfully after the JaCoCo and Byte Buddy upgrades.
- The CI command now omits `-Prelease` because Maven reports that profile does not exist in this split repository.
- `.github/workflows/ci.yml` YAML parsing passed.
- Compatibility scan found no remaining old `org.apache.shenyu.common`, `org.apache.shenyu.register.common`, `org.apache.shenyu.register.client.http`, or `jakarta.*` imports in the restored beat/discovery code.
- Java 8 syntax scan found no `List.of`, `Map.of`, `Set.of`, or pattern-matching `instanceof` usage in the migrated MCP/starter modules.
- The full test run still logs existing background exceptions from original async tests under JDK 17, but Surefire reports reactor success.

## Next Steps

- Confirm the expanded GitHub Actions matrix on the remote runner after opening the pull request.
- Verify beat and discovery instance registration against matching admin/bootstrap runtime.
- Verify `/shenyu-client/register-mcp` against the matching admin side before treating MCP registration as end-to-end complete.
