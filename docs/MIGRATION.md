# Migration preparation and release handoff

The source baseline is pinned in `.github/migration-source.json`, currently main
commit `6210d4cbab53ad6b2a44ae48382d80a13d89a99d` from PR #7605. Preparatory CI can
build those foundations from source; no dependency on a formal publication is
required to review the migration, compile clients/examples, or run their tests.

## Prepared in this branch

- Replace JDK8/Spring Boot 2 source with the current main implementation; Java 17
  is the minimum, and Java 21 verification uses main's push-only policy.
- Import client API/HTTP registration modules and all current main client/starter
  tests. The inventory records every imported source/resource path and rejects
  accidental omissions. Main-owned foundation classes cannot be copied back here.
- Remove local registry API ownership, gateway beat/beat-starter ownership and Motan.
- Import nineteen client-facing example roots, including SDK providers with
  transitive client/example dependencies. Their shared example helpers use new
  client-only artifact names. SDK/protocol/registry dependencies continue to come
  from main.
- Separate client and foundation versions. Build unreleased foundations from a
  fixed SHA rather than tracking a moving branch or importing main client modules.
- Replay protocol-JAR fixtures through the actual HTTP sender, preserving request
  field types, the v1 headers, unquoted success responses and retry/lifecycle behavior.
- Run a client-owned source runtime job with the pinned main Admin/bootstrap,
  independently built HTTP example and main-owned ZooKeeper provider. Check
  registration, scheduled heartbeats, proxying and upstream removal on Java 17;
  use main's push-only policy for Java 21.
- Include registry weight updates, migrated gRPC unary/streaming calls and MCP
  nested registration plus actual Streamable HTTP tool calls in the runtime job.
- Disable deployment and enforce a release profile gate until reviewed published
  foundation versions, ownership handoff and runtime compatibility are available.

## Upgrading from the JDK8-adapted source

Use the restored main-owned packages in XML configuration and custom integrations:

| Old copied type | Current main-owned type |
| --- | --- |
| `org.apache.shenyu.client.core.register.config.ShenyuClientConfig` | `org.apache.shenyu.register.common.config.ShenyuClientConfig` |
| `org.apache.shenyu.client.core.register.config.ShenyuRegisterCenterConfig` | `org.apache.shenyu.register.common.config.ShenyuRegisterCenterConfig` |
| `org.apache.shenyu.client.core.register.HttpClientRegisterRepository` | `org.apache.shenyu.register.client.http.HttpClientRegisterRepository` |
| `org.apache.shenyu.client.core.dto.URIRegisterDTO` | `org.apache.shenyu.register.common.dto.URIRegisterDTO` |

The moved examples already use the current package names. The current listener
reads `shenyu.discovery.type` from the Spring environment and defaults to `local`
for URI publication; the old copied `discoveryLocalMode` workaround is unnecessary.
Current source retains `instanceInfo` population and the main shutdown/lifecycle implementation.
The prior copied JDK8 models are not a second protocol definition.

## Verification required before enabling a release

1. Merge/release the reviewed main protocol, shared MCP/register and foundation
   changes. Replace the preparation SNAPSHOT with a verified released
   `shenyu.foundation.version`, and remove source preparation from release CI.
2. Choose the external client's actual release version with the release owner.
   Do not use the temporary `-migration-SNAPSHOT` version as a release coordinate.
3. Confirm that main no longer deploys business-client coordinates once ownership
   transfers. Keep gateway beat modules in main. Remove main source only after
   the external artifacts and runtime compatibility jobs are ready.
4. Run the client candidate on Java 17, and Java 21 under the same main policy,
   against the latest stable and oldest explicitly supported released Admin and
   bootstrap versions. Pin actual image tags/digests in a reviewed client-owned
   matrix. Never add a client dependency to the main reactor for these tests.
5. Record main/client commits, exact dependency/image versions, JDKs, commands,
   route visibility, gateway proxy responses and shutdown/removal observations.
   Only then update the preparation/deployment guards through a reviewed PR.

## Client-owned runtime scenarios

The source-candidate runner does not require Docker or published artifacts:

```bash
python3 script/verify-runtime.py
# Or reuse an existing clean checkout at the manifest's exact main SHA:
python3 script/verify-runtime.py --main-source /absolute/path/to/main-checkout
```

Set `JAVA_HOME` to select the runtime/build JDK. `--maven-repo` uses the same
optional Maven repository for both builds. The runner builds main foundations,
Admin/bootstrap and the external example using their own wrappers. It resolves
their classpaths separately and rejects business-client artifacts in main's
runtime and server-test dependencies. It also builds the moved gRPC and MCP
examples. The HTTP example's `runtime-compatibility`
profile explicitly adds main's ZooKeeper provider. ZooKeeper server support
libraries come from Admin's test dependencies, not the business application.

Every run uses loopback ports, an in-memory H2 database, temporary registry data
under `target/runtime-compatibility/<run-id>` and generated Admin/sync secrets.
Services are stopped on success or failure. `report.json` records source commits,
client build-input fingerprint, dirty paths, JDK, exact JAR paths/checksums,
commands, ports and check outcomes. `registration-traffic.json` records the
actual authenticated registration requests and Admin responses while excluding
credentials/tokens/login bodies. Application logs suppress the shared utility's
login response logging. CI uploads reports, traffic and process/build logs even
on failure.

Test JVMs use `-Xms768m -Xmx1024m`: the pinned main timer queue requires more than
256 MiB of free committed heap, so a small implicit initial heap can discard a
registration-recovery task even with unused room below the maximum heap. Earlier
undersized-heap failures remain in their run reports; they are not passing evidence.

The runner verifies the real example's metadata, selector, rules, numeric URI
port, v1/client headers and unquoted `success`. It waits for two scheduled URI
heartbeats, checks JSON-string `instanceInfo` and renewed Admin heartbeat times,
then stops the application and requires an authenticated offline request, empty
Admin upstreams, an empty namespace-scoped discovery frame consumed by bootstrap
and the gateway's `-119` no-healthy-upstream response. Backend connection failure
alone does not pass removal verification.

For ZooKeeper, it starts two independently running examples under one service,
checks the `/shenyu/register/instance/<appName>` listener and verifies upstream
counts `1 -> 2 -> 1 -> 0` in Admin and gateway frames. The remaining instance must
still proxy after the first exits. It updates one registered instance's weight
from 50 to 80 through main's registry API and requires the update in both Admin
and bootstrap's received discovery data. Discovery mode must not also send a local URI.
The runner's evidence guards have negative tests in `script/test-runtime.py`.
`--skip-build` is only for local replay of an earlier runner build; it refuses
changed client Java, POM, resource or migration-manifest inputs.

The runner enables gRPC and MCP only in its fresh in-memory Admin. gRPC verifies
method and class annotation registration, a real echo response, unary invocation,
ten server-stream responses, client-stream completion and bidirectional messages
through the gateway. The gRPC example honors `server.address` so its RPC listener
can bind to loopback along with its HTTP listener.

For MCP, it verifies three annotated tools and exact preservation of their nested
metadata, namespaces and JSON-string request configuration in Admin's rule handles.
The example's MCP and HTTP metadata ports follow `server.port`. The `id` tool
parameter is declared as a query parameter to match the controller's `@RequestParam`;
declaring it as a path parameter made real tool calls return HTTP 400.

A small client-owned Java probe uses the already resolved main registry/MCP SDK
classpath, with no new business dependency in main. The MCP probe explicitly uses
protocol `2025-03-26`, supported by this pinned server and SDK; their default latest
protocol versions differ. It initializes Streamable HTTP, lists tools and calls
both a parameterless tool and `findOrderById(id=7602)` against the real backend.
The HTTP upstream must be present in bootstrap before invoking tools. Both gRPC
and the MCP backend's HTTP registration must send offline on shutdown and reach
an empty gateway discovery snapshot. The runner preserves probe output and checks
for one JSON evidence record, including when logs contain ANSI color prefixes.

This is evidence for the pinned source candidate. It does not certify released
pairs, other registry providers, other MCP transports/protocol versions or other
RPC starters, and does not replace the released-version matrix below.

Start Admin and bootstrap from the selected released images and a moved Spring MVC
example built from this candidate. Configure HTTP registration, matching Admin
credentials, a namespace, and `shenyu.discovery.type=local`. Verify metadata/rules
and URI registration, repeat heartbeat renewal, route visibility in Admin,
configuration synchronization and an actual proxied request. Stop the example and
verify the intended offline lifecycle according to the v1 contract.

For discovery, run the moved example against a registry provider with explicit
provider dependencies. Check instance add/update/removal and Admin's listener path,
then ensure bootstrap consumes the changed upstream set. Preserve `instanceInfo`
and its JSON-string representation. Register/URI port is numeric; instance beat
port is a string. Also test MCP nested metadata/namespace/request configuration and
all migrated RPC starters before claiming support for those runtime flows.

Local fixture tests deliberately accept `success` responses without capability or
version response headers, allowing new clients to work with older Admin endpoints.
Versionless legacy client acceptance remains tested in main. Breaking changes need
new protocol versions and dual-support Admin releases before client rollout.

Runtime evidence for released pairs is still outstanding. This preparation branch
does not mark #6366, #6367 or #7602 complete and does not delete main client source.

## Rollback and contribution

Before publication, restore the prior source/release owner from Git if preparation
cannot proceed. After client publication, roll back business services to a tested
client release and retain v1 support in Admin. Main rollback must not introduce a
reverse dependency or resume publishing transferred client coordinates.

Change DTOs/endpoints/defaults in main and add immutable protocol fixtures there.
Change annotation scanning, business-client registration/retry/shutdown and starter
behavior here. Keep the source inventory and all relevant tests when updating the
baseline. Changes affecting a wire contract require coordinated review in both
repositories; release timing does not have to be synchronized.
