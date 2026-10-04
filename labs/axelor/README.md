# Axelor cloud baseline

Issue #1 was executed before Issue #3. This baseline contains one empty Axelor
extension module under `com.cencomun.baseline`, with framework compatibility and
generated metadata tests. It has no business features, database writes or model
extensions yet.

## Cloud workflow

Run from `/workspace/cencomun-erp-lab`:

```bash
bash labs/axelor/scripts/setup-cloud.sh
bash labs/axelor/scripts/validate.sh
```

The setup is scoped to Debian 13 x86_64. It downloads exact, checksum-verified
OpenJDK 21.0.12.1 packages into `/workspace/ccm-axelor-runtime`, prepares the
official pinned webapp and submodule, and uses a copy of that host's Gradle
wrapper with the official Gradle 8.14.3 distribution checksum enforced. The
original wrapper files and `.gitmodules` are unchanged.

The dependency host and caches are outside this repository. Local Git
configuration selects HTTPS for the submodule. An ignored symlink registers the
custom module in the host. An ignored `ccm-cloud.settings.gradle` keeps the
official plugin declarations, root build and `buildSrc`, and includes only the
custom module for cloud compilation. It does not validate all AOS modules.

Validation explicitly runs `classes`, `test` and `jar` on
`:modules:cencomun-baseline`, verifies that both tests actually executed, checks
the generated JAR metadata and asserts unchanged upstream tracked files and
baseline pins. It intentionally reruns tasks so restored test results are not
mistaken for a new run. The module's generated lockfile fixes its resolved
compile/runtime/test dependencies; ordinary setup never updates that lockfile.

Use the existing checkout; each cloud task already runs in an isolated
environment. Do not create a Git worktree unless explicitly requested.

For additional module Gradle tasks use:

```bash
bash labs/axelor/scripts/gradle.sh --version
bash labs/axelor/scripts/gradle.sh :modules:cencomun-baseline:compileJava
```

The helper activates the local JDK and translates the existing proxy host/port
into Java system properties without saving credentials. Global Gradle is not
used. Java TLS trust and distribution/package checks remain enabled.

Do not run the host's `build`, `formatCode` or `spotlessApply` tasks during this
baseline: its `build` task invokes formatting which can change upstream source.

## Full-stack runner

See [FULL_STACK_RUNNER.md](FULL_STACK_RUNNER.md). Database-backed tests and
application startup were not executed in Codex Cloud. See the final evidence in
[`reports/axelor-baseline.md`](../../reports/axelor-baseline.md).
