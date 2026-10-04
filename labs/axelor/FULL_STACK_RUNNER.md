# Dedicated Axelor full-stack runner

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
