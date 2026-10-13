# Apache ShenYu Java Client

Business-service Java clients and Spring Boot starters for Apache ShenYu.
The migration preparation branch targets **Java 17 and Spring Boot 3**, with Java 21
compatibility verification following the main repository's push-only CI policy.

This branch prepares [apache/shenyu#7602](https://github.com/apache/shenyu/issues/7602).
It imports current client implementation and tests from the pinned main commit in
[the migration manifest](.github/migration-source.json), including the protocol
prerequisites in [main PR #7605](https://github.com/apache/shenyu/pull/7605).
The version `2.7.2-migration-SNAPSHOT` identifies unpublished preparation artifacts;
it is not a proposed official release number.

## Build the preparation branch

```bash
python3 script/test-migration.py
python3 script/test-runtime.py
python3 script/check-migration.py
python3 script/prepare-foundations.py
./mvnw clean verify -Dmaven.javadoc.skip=true -Djacoco.skip=true
./mvnw clean verify -Pexamples -Dmaven.javadoc.skip=true -Djacoco.skip=true -Ddocker.skip=true
```

`prepare-foundations.py` fetches a **fixed commit**, builds only main-owned foundation
modules and their main-owned dependencies, and installs their SNAPSHOTs locally.
It can reuse a clean checkout at the same commit:

```bash
python3 script/prepare-foundations.py --main-source /absolute/path/to/shenyu
```

For an isolated Maven repository, pass `--maven-repo /absolute/path/outside/this-checkout`
and the same `-Dmaven.repo.local=...` argument to subsequent Maven commands. Keep
that repository outside `target`, which `clean` removes. CI runs this preparation
before the complete client/starter/example reactor so it can execute before any
formal main release is available.

Set `JAVA_HOME` to your Java 21 installation and rerun the commands for local
compatibility verification. The Maven wrapper is required. Checkstyle and Apache
RAT run during validation. Docker image building is an explicit example profile
operation; ordinary verification uses `-Ddocker.skip=true`.

## Ownership and migration content

This repository owns business client implementation, client API/HTTP registration,
eight business-service starters and their tests, and the nineteen client-dependent
example roots listed in the manifest. Current implementation replaces the old
JDK8-adapted copies of common/register/timer/DTO logic. Existing main client and
starter test sources are preserved and checked by the migration inventory.

The main repository owns registration protocol DTOs/constants/fixtures,
`shenyu-common`, `shenyu-register-common`, shared MCP generation, Disruptor, SPI,
registry API/providers, protocol/SDK foundations, Admin and gateway runtime.
The duplicated registry API, beat sender, beat starter and removed Motan module
are absent here. Gateway heartbeat remains a main-repository responsibility.

The dependency direction is strictly:

```text
shenyu-client-java -> main-owned protocol/foundation artifacts
```

Client modules use `${project.version}` for internal client dependencies and
`${shenyu.foundation.version}` for main-owned dependencies. Their release clocks
are independent. The examples include two client-only helper coordinates,
`shenyu-client-examples-common` and `shenyu-client-examples-dubbo-api`, so helpers
are not published under main-owned coordinates. All preparation deployment is
skipped; the `release` profile rejects this preparation state.

## Registration compatibility

HTTP requests report `X-Shenyu-Register-Protocol-Version: 1`. Packaged clients also
report their own JAR's `Implementation-Version` in `X-Shenyu-Client-Version`;
unpackaged development classes may omit this optional header. Shared HTTP transport
and login come from main, while business-client headers and error propagation are
client-owned. The existing bounded registration retry and heartbeat/shutdown policies
are retained.

`RegistrationWireContractTest` captures real HTTP requests for metadata, URI,
URI heartbeat, offline, API documentation, discovery configuration, MCP and
instance heartbeat. It loads all eight JSON fixtures from the protocol JAR,
checks serialized field values/types, token/protocol headers, and accepts old-style
Admin `success` responses without new headers. Lifecycle, annotation, SPI, retry,
shutdown and starter tests accompany the imported implementation.

`python3 script/verify-runtime.py` also builds the pinned source Admin/bootstrap
and independent HTTP example, then verifies actual registration, scheduled
heartbeats, gateway proxy responses and shutdown. It covers local URI mode and
two ZooKeeper instances with upstream transitions `1 -> 2 -> 1 -> 0`. It also
covers registry weight updates, gRPC unary/streaming calls and MCP Streamable HTTP
initialization, tool listing and real parameterized/parameterless tool calls. It
also checks nested MCP namespace/request configuration preservation. Java 17 CI
runs it for pull requests; Java 21 follows main's push-only policy. Every run
saves reports, traffic and logs under `target/runtime-compatibility` and cleans
up its processes. The [migration guide](docs/MIGRATION.md) explains replay options
and the exact scope of this source-candidate evidence.

These local contract tests do not certify a released Admin/client pair. See
[the preparation and release checklist](docs/MIGRATION.md) for cross-repository
verification and the remaining release gates.
