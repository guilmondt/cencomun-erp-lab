# Dedicated Axelor full-stack runner

## GitHub Actions harness

The user's selected default is GitHub Actions. The branch workflow
`.github/workflows/axelor-full-stack.yml` executes `ci/run-host.sh` on an
`ubuntu-24.04` Docker host, outside Codex Cloud. It is triggered by Axelor code,
CI or pin changes pushed to `lab/axelor-baseline`; it does not require merging
the workflow into main. Manual dispatch becomes available when the workflow is
present on the default branch. No production secret or maintained server is
required. Official actions are fixed to commit hashes.

`ci/pins.sh` fixes Debian 13.7 slim and PostgreSQL 16.15 bookworm images by
immutable OCI digests, the exact Debian JDK/compiler patch, Node 24.5.0's
official SHA-256 and Yarn 1.22.19's official npm SHA-512 integrity. Debian slim's
CA bundle is initially bootstrapped with signed APT metadata before HTTPS
installation. Helper OS packages are recorded in an installed-package manifest.

The harness keeps the original host settings/all modules and substitutes only
local runtime configuration: verified frontend executables, frozen Yarn
installation, bounded Java heaps and external dependency locks. It rejects
source-writing formatting/build tasks. The first full build writes locks to a
temporary runner directory; subsequent startup uses the generated embedded
launcher. These per-run lock artifacts describe the resolved dependency graph;
they do not turn the branch into a fully locked replay of all upstream Maven
dependencies. The custom source lockfile is preserved.

The planned checks are: two Cencomun tests; full host/AOS/frontend compilation
and WAR; 16 cases in the existing `TestTaxNumberHelper` suite; real PostgreSQL
initialization; public API response, framework login, authenticated REST reads
of Cencomun/AOS module metadata; and a server restart with the same ephemeral
database. The tax-number suite is a unit suite, not a PostgreSQL test or a
Venezuelan localization evaluation. No Core Test business feature is added.

Only the isolated Docker network exposes the app/database. PostgreSQL gets a
random test credential from a temporary file; the upstream synthetic initial
administrator is used solely for framework login within that network. No host
GitHub token is passed to the container. Credential/configuration files and
database volumes are excluded from artifacts; password-redacted logs, result
JSON/XML, package/image manifests, dependency locks and WAR checksum are retained
for 14 days. The harness removes its containers/network on completion.

Execution evidence and diagnosed blockers will be recorded in
`reports/axelor-full-stack.md`. Until that report records a passing run, these
checks remain unverified. The following original cloud-baseline observations
are historical and do not establish the external runner's result.

These are runner requirements and candidate commands, not a record of a
full-stack test. No PostgreSQL database, server startup, API request, ERP
initialization or upstream AOS test suite was executed in this cloud baseline.

## Retain the same baseline

- Webapp `axelor/open-suite-webapp`, tag `v9.1.8`, commit
  `1119727a3b53c8387b7fab535e184c25154d2eac`.
- AOS gitlink `modules/axelor-open-suite`, commit
  `0c70d561b19fc454eba9fdd41689258846626d75`.
- Java 21 JDK, AOP plugin 8.2.3, host Gradle wrapper 8.14.3 and official
  distribution SHA-256
  `bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531`.
- Full-suite frontend prerequisites declared by AOS `axelor-base`: Node 24.5.0
  and Yarn 1.22.19. Those frontend versions were inspected in the pinned build;
  they were not installed or tested here. Do not replace them with the cloud
  machine's default Node.
- PostgreSQL satisfies the repository baseline `>= 12`. Choose and record an
  exact supported server/image version and immutable image digest before
  executing CI. The repository does not yet pin an exact database release.
- Use synthetic fixtures and an isolated database, filesystem directories and
  test account. Never use production credentials or data. Full suite
  configuration and dependency locking need their own runner evidence; the
  custom module lockfile does not freeze every AOS configuration.

## External configuration and startup

In the pinned AOP source, `SettingsBuilder` supports an external properties/YAML
file through `AXELOR_CONFIG` (or system property `axelor.config`). Use a protected
runner file outside the checkout. Populate `db.default.driver`,
`db.default.url`, `db.default.user`, `db.default.password`, and the required
application/data directories securely. Keep values out of Git and build logs.
Review `db.default.ddl` for a disposable synthetic database; do not point
automatic schema changes at a persistent production database.

The host registers the `run` task for embedded Tomcat. Cloud task discovery and
inspection of the pinned AOP `TomcatSupport`/`TomcatRun` confirmed the task and
its `--port` option; the server itself was not started.

For a runner using the tested cloud filesystem layout:

```bash
cd /workspace/cencomun-erp-lab
bash labs/axelor/scripts/setup-cloud.sh
# Set AXELOR_CONFIG to the runner's existing secure configuration file.
CCM_AXELOR_FULL_STACK=1 bash labs/axelor/scripts/gradle.sh run --port=8080
```

`CCM_AXELOR_FULL_STACK=1` selects the host's original settings and all AOS modules.
This execution path is untested: it requires the extra frontend and database
prerequisites above. On other runner OS/architectures prepare the exact JDK and
verified host wrapper through supported installation rather than reuse the
Debian-only extraction script unchanged.

Compile/package using explicit `classes`, `test`, `war`/distribution tasks as
appropriate. Audit the selected task graph before execution: avoid `build`,
`formatCode` and `spotlessApply`, which can modify upstream source. The
full-suite Gradle graph and frontend installers must be checked for lockfile or
source mutations in the runner before claiming a reproducible package.

## Verification and failure handling

1. Check exact host/gitlink/toolchain/wrapper versions and unchanged source.
2. Confirm PostgreSQL readiness using the runner's configured test connection;
   inspect application startup logs without logging credential values.
3. Make a representative functional HTTP request and verify Cencomun module
   discovery/registration. A listening port alone is insufficient.
4. Run selected database-backed and upstream tests; record test counts,
   failures/skips and timing separately from the two cloud module tests.
5. Recreate/restart the isolated runner, repeat the checks and record exact
   database/configuration/dependency pins before declaring full-stack readiness.

If dependencies fail, record the actual URL/status or TLS error and add only
confirmed blocked destinations to restricted networking. Do not disable TLS,
checksums or assertions. If startup fails, diagnose database/configuration/log
evidence before changing code; repeat the affected functional check afterward.
