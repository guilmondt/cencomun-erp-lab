# Axelor external runner validation

Date: 2026-10-04. Branch: `lab/axelor-baseline`. Status: full-stack baseline
passed on the external GitHub Actions runner, including authenticated API and
server restart. This is baseline readiness, not Core Test business acceptance.

## Scope and runner decision

The user delegated runner selection. GitHub Actions is the available managed
runner: repository CI was already working, and it avoids a maintained server
or production secrets. This validates Task 020's empty module with the complete
pinned AOS host; it adds no Core Test business feature or upstream change.

Issue #1 preflight/guardrails were repeated before runner edits and execute
again before every full-stack job. The cloud baseline's two module tests passed
again in 12 seconds, 0 failures/errors/skips. The cloud does not run PostgreSQL,
Docker services or the ERP server.

## Exact runner references

| Component | Pin |
| --- | --- |
| Host / AOS / AOP | Existing v9.1.8 commits and AOP 8.2.3, unchanged |
| Java/compiler | 21.0.12.1; Debian `21.0.12.1+1-1~deb13u1` |
| Gradle | Official host wrapper 8.14.3 with enforced official SHA-256 |
| Build container | Debian 13.7 slim, OCI `sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a` |
| Database | PostgreSQL 16.15 bookworm, OCI `sha256:efedf3595f1d6f415c08568ba171029bf54052e754cc9f030e3f2412b21f3d67` |
| Frontend | Node 24.5.0 with official SHA-256; Yarn 1.22.19 with npm SHA-512 integrity |
| Action checkout | v4.2.2, `11bd71901bbe5b1630ceea73d27597364c9af683` |
| Artifact upload | v4.6.2, `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| Workflow validator | actionlint 1.7.7 with official release SHA-256 |

Image digests and action commits were inspected through official registries/Git;
Node/Yarn checksums came from their official HTTPS release/package metadata.
JDK packages and Gradle distribution retain the cloud baseline's verified pins.
Helper OS package versions are captured in the runner manifest. Ubuntu 24.04 is
the hosted Docker VM label; its complete image is managed by GitHub. The build
and database containers, application runtimes and upstream commits are pinned.

Full-suite locks are written outside source during the first build, then the
Gradle targets are replayed offline with strict locks. This proves use of that
run's graph when successful; branch source does not yet contain a frozen replay
of every upstream Maven configuration. The existing Cencomun lock is preserved.

## Executions and observed problems

| Run | Source | Outcome |
| --- | --- | --- |
| [37226162907](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37226162907) | `618a617` | Workflow rejected before a runner job |
| [37226271713](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37226271713) | `4ff2807` | Runner failed; artifact upload passed; logs blocked in Cloud |
| [37226539574](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37226539574) | `8714452` | Failed in local init script applied to buildSrc, before AOS compilation |
| [37227056487](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37227056487) | `a591039` | 2 module tests and scope regression passed; lock configuration failed before AOS compilation |
| [37227377837](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37227377837) | `2406690` | Full build, 18 tests, frozen Gradle replay and initial PostgreSQL API smoke passed; restart exceeded its 300s budget |
| [37228746936](https://github.com/guilmondt/cencomun-erp-lab/actions/runs/37228746936) | `cdc57c8` | Passed: build, 18 tests, locked replay, first API smoke, restart API smoke and source checks |

**Invalid workflow context.** `runner.temp` is not allowed in a job-level `env`
field; actionlint reported the exact field/context error. GitHub rejected the
workflow before creating jobs.

1. Resolve the result directory from `RUNNER_TEMP` inside the executable step.
2. Add checksum-verified actionlint validation with `ci/check-workflow.sh`.
3. The validator passed locally and subsequent real runner jobs accepted the
   workflow, checked out source and passed preflight.

**Gradle init scope.** Init scripts run for buildSrc as well as the host. The
script looked up `:modules:axelor-base` in `:buildSrc`, which has no such module.
The annotation returned `Project with path ':modules:axelor-base' could not be
found in project ':buildSrc'` at init line 4. Full AOS compilation did not run.

1. Apply host configuration/task policy only when the root is `axelor-erp`.
2. Add `ci/check-init-scope.sh`: execute the same init script against an isolated
   Java build named buildSrc, without application projects or upstream edits.
3. The regression passed locally in 4 seconds. A direct standalone invocation
   of upstream buildSrc was discarded as an invalid test: Java is normally
   applied implicitly by Gradle's embedded buildSrc mechanism. No upstream file
   was changed to make that diagnostic pass. Rerun the complete runner to
   establish application compilation/startup evidence.

**Late dependency lock configuration.** The pinned AOP build resolves the host's
runtimeClasspath while evaluating projects. Activating locks afterward raised
`Cannot change resolution strategy ... after it has been resolved`. The prior
scope correction worked; no AOS compilation/startup success is implied.

1. Configure per-project locking in `beforeProject`, before build scripts can
   resolve any configuration; retain strict mode and external lock locations.
2. Extend the regression helper with a minimal Java host fixture that resolves
   runtimeClasspath during evaluation, using built-in Gradle tasks and a small
   node extension fixture without network dependencies or upstream edits.
3. Both scope/lifecycle fixtures passed locally, 4 seconds each. Rerun the real
   host compilation and frozen-lock replay; fixture success is not ERP evidence.

**Server readiness budget.** The initial full-suite API smoke passed after
431.5 seconds and found 33 modules with AOP 8.2.3, AOS 9.1.8 and Cencomun 0.1.0.
The restarted server began at 19:26:31 UTC; its last recorded phase was detecting
PostgreSQL 16.15 at 19:30:18. The job stopped at 19:31:38, consistent with the
restart's 300-second readiness window plus cleanup. That window was shorter
than the measured successful first startup. No application exception appeared
in the available server tail; restart success was not established.

1. Give restart the same bounded 900-second readiness window as the first boot,
   keeping all functional assertions, authentication and version checks.
2. Put the client exception first in failure annotations and keep the message
   under GitHub's approximately 4 KiB limit. The previous annotation had cut off
   the client tail after the successful first-smoke JSON.
3. A local large-log regression verified that the client error survives the
   annotation limit, credentials remain redacted and failure exit status remains
   nonzero. The corrected cold runner passed initial startup in 422.42 seconds
   and restart in 315.44 seconds. The latter exceeds the previous 300-second
   deadline, confirming that budget was insufficient. The earlier timed-out
   restart remains failed; functional assertions were preserved.

**Restricted evidence downloads.** Git reads and Actions API metadata work.
Downloading job logs redirects to `results-receiver.actions.githubusercontent.com`;
the artifact redirects to `productionresultssa11.blob.core.windows.net`. Both
hosts returned proxy CONNECT HTTP 403. This prevents Cloud from retrieving the
original log/artifact, not GitHub from running the job or uploading evidence.

1. Save the prepared environment-network draft adding only these two observed
   blocked domains, preserving `package_managers`, `api.github.com` and
   `repository.axelor.com`. No wildcard or unrestricted network was added.
2. Retry the download after the runtime policy changes. Do not request another
   token: the required API calls and Git push already work.
3. Verify that proxy 403 is gone, inspect current sanitized logs and parse the
   current test XML. Until then, API-accessible runner annotations expose the
   sanitized failing-stage log and exit status. A local fixture verified
   credential redaction, failure annotation and exit-status preservation.

GitHub reports that the pinned v4 actions target deprecated Node 20 and are
executed using its Node 24 runner engine. Checkout/upload succeeded; this is
separate from the application's verified Node 24.5.0 frontend runtime.

## Validation contract and evidence

The actual job must pass custom compile/JAR plus exactly two tests, full AOS and
frontend/WAR compilation, the 16 existing tax-number unit cases, strict-lock
Gradle replay, PostgreSQL initialization, framework login, authenticated module
REST metadata and a restart against the same disposable DB. The upstream tax
suite is not PostgreSQL coverage or Venezuelan localization. The API reads are
PostgreSQL-backed and write no business fixture.

The harness rejects `build`, formatting and `spotlessApply`; keeps original
upstream settings/source; uses local runtime frontend configuration with frozen
Yarn; and compares tracked upstream/lab files after checks. Database schema
creation is Axelor's supported initializer on a new disposable database. Recovery
is destruction/recreation of that owned database, never a production migration.

No production value, customer data or GitHub credential is passed into the build
container. Temporary generated PostgreSQL credentials, configuration, sessions
and DB volumes are excluded from artifacts. Own containers and anonymous volumes
are removed at exit. Sanitized logs, XML/JSON, package/image manifests, dependency
locks and WAR checksum are uploaded for 14 days. Functional requests remain
inside the isolated runner network; no public application preview is created.

## Final executed result

Run **37228746936**, source **cdc57c8656940fc6c4eed381244fbb514e702fcf**,
completed successfully. Job interval: 19:33:48–19:52:11 UTC, **18m 23s**,
including package setup, compilation, tests and both application startups.
Every job step, including artifact upload, passed.

| Current-run check | Result |
| --- | --- |
| Issue #1 preflight and guardrails before Task 020 validation | Passed |
| Exact host/gitlink, JDK/compiler, wrapper/checksum, Node/Yarn integrity | Passed |
| Cencomun classes/JAR/metadata and unit suite | 2 passed; 0 failures/errors/skips |
| Scope/early-lock lifecycle regression fixtures | Both passed |
| Full original-settings AOS/frontend compilation, WAR and embedded launcher | Passed |
| Existing upstream tax-number suite | 16 passed; 0 failures/errors/skips; XML case time 0.118s |
| Gradle target replay with generated strict locks, no refresh, offline | Passed; reused test outputs are not counted as another 16 cases |
| PostgreSQL | 16.15, Debian package `16.15-1.pgdg12+2` |
| Initial public API, framework login, authenticated identity and module REST read | Passed after 422.42s; AOP 8.2.3, AOS 9.1.8, Cencomun 0.1.0, 33 modules |
| Server stop/restart, same database, fresh authenticated API requests | Passed after 315.44s; same versions and 33 modules |
| Laboratory/upstream tracked diffs after both functional smokes | Empty; original pins/source preserved |
| Containers and anonymous DB volume cleanup; sanitized artifact upload | Passed |

Generated WAR SHA-256:
`d3aeff3f41ff7565941e79573df5869957ad852a30cc9cb28ec83ca119f091d8`.
Artifact: `axelor-full-stack-37228746936-1`, 176347 bytes, official API digest
`sha256:6b9ffd788f1f950568c9428440563224989a480877b305cb0f92d58abd1f6336`.
The current-run machine-generated annotation contains the parsed suite XML
attributes, both functional result JSON objects, PostgreSQL version, exact lab
commit and WAR checksum. It was retrieved through the existing GitHub API;
the complete artifact download remains blocked in Cloud pending network review.

Readiness is established for the empty custom module, complete-host build and
PostgreSQL-backed authenticated metadata workflow, including restart. All AOS
test classes, Core Test business scenarios, ERP accounting/inventory correctness,
performance percentiles, production deployment and independent new-task Cloud
snapshot restoration were not tested. Startup timings include readiness polling
and the functional requests; they are not business-operation latency benchmarks.
No app/library bug was patched, no assertion or permission was disabled and no
baseline version was changed. GitHub's pinned v4 action engine warning did not
fail checkout or upload.
