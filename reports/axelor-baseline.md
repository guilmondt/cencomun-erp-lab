# Issue #3 — Axelor baseline

Date: 2026-10-04. Branch: `lab/axelor-baseline`. Cloud compilation and custom
module unit validation completed after Issue #1. Full-stack readiness is not
claimed.

## Verified references and tool versions

| Component | Verified baseline |
| --- | --- |
| Laboratory starting HEAD | `33c413764de947b9e6610318ccc673ec6ac0150f` |
| Official webapp | `v9.1.8`, `1119727a3b53c8387b7fab535e184c25154d2eac` |
| AOS submodule gitlink and checkout | `0c70d561b19fc454eba9fdd41689258846626d75` |
| AOP Gradle plugin / core / web / test | `8.2.3` |
| Java and compiler | OpenJDK / javac `21.0.12.1`, Debian package `21.0.12.1+1-1~deb13u1` |
| Gradle | Host wrapper `8.14.3`; no global Gradle used |
| JUnit resolved by `axelor-test` | Jupiter / Platform `6.0.3` |
| Custom module | `com.cencomun:cencomun-baseline:0.1.0` |

The JDK/JRE package SHA-256 values were obtained from Debian trixie's signed
package indexes and checked before extraction. The wrapper distribution used
the official checksum, retrieved over verified TLS:
`bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531`.
Original upstream wrapper files remain untouched; enforcement is configured in
a local copy of the host wrapper. No verification was disabled.

## Deliverables and isolation

The new module has a 12-line empty `AxelorModule` subclass under
`com.cencomun.baseline.module` and 42 lines of framework/metadata unit tests.
There are no business features, domain entities, fixtures, migrations, custom
database operations or upstream core changes. The plugin generates discovery
metadata; that metadata is checked in the test and packaged in the JAR.

New helper scripts prepare dependencies, activate Java/proxy/wrapper settings
and validate the module. A generated 387-line lockfile freezes its resolved
compile/runtime/test dependency graph in strict mode. No pre-existing
dependency declaration, source, test or lockfile was changed.

The official host and AOS are dependency caches under
`/workspace/ccm-axelor-runtime`, not separate laboratory project repositories.
An ignored module symlink and ignored local settings file register the module
and limit cloud configuration to it. The root build and `buildSrc` are still
the official host's files. This validates an isolated custom extension on AOP,
not runtime integration with every AOS module.

## Executed checks

| Check | Outcome |
| --- | --- |
| Issue #1 preflight and repository guardrails before implementation | Passed |
| Exact tag, host HEAD, gitlink and submodule HEAD | Passed |
| Signed-index package hashes, JDK activation, official wrapper checksum and `--version` | Passed |
| `setup-cloud.sh`, repeated on prepared state | Passed; no duplicate registration/configuration drift |
| Exact saved installation script, executed from `/workspace` | Passed after draft saving |
| Custom `generateCode`, `compileJava`, `processResources`, `jar`, test generation/compilation | Passed |
| `registersWithThePlatformInjectorWithoutADatabase` | Passed |
| `generatedMetadataIdentifiesTheCustomModule` | Passed |
| Test execution and XML/JAR verification | 2 executed; 0 failures, errors or skipped |
| Initial scoped validation | Passed in 50 seconds |
| Repeated validation | Passed in 14 seconds |
| Lockfile generation and frozen validation | Passed; final frozen run 15 seconds, 9 tasks executed |
| Available application task discovery | Passed; embedded Tomcat `run` task registered |
| Saved start instructions after environment reconnection | Passed; compilation/JAR and 2 tests rerun in 18 seconds |
| `versions.lock` diff, host and AOS tracked diffs | Empty; pins and upstream source unchanged |
| PostgreSQL, HTTP startup/functional request, all AOS tests, frontend build | Unrun; dedicated runner scope |

`validate.sh` forces task execution and checks that the named two tests completed
in the current result XML; stale results and zero-test runs are not treated as
validation. Global host `help` was interrupted during unnecessary AOS/Studio
dependency downloads; it was not a successful whole-suite check.

## Observed problems, impact and resolution

**Initial Java runtime had no compiler.** Compilation could not use that
runtime alone.

1. Downloaded exact matching JDK and JRE Debian packages using the existing
   allowed destinations and authenticated package metadata.
2. Verified SHA-256 and extracted them into the runtime directory, preserving
   system installation and the existing patch version.
3. Activated that JDK through the helper. `javac -version` reports 21.0.12.1;
   module compilation and both tests passed.

**Full host configuration downloaded unrelated AOS/Studio dependencies.** It
increased setup time without helping the empty module baseline.

1. Interrupted only the Gradle processes started for that diagnostic.
2. Generated local scoped settings with the official plugin declarations and
   root build, including the representative custom module only.
3. Verified that compilation and tests execute, and reserved whole-suite
   coverage for the dedicated runner.

**The first external settings file was outside the host root.** Gradle could
not resolve seven classes provided by the host's `buildSrc`, so that attempt
failed before compiling the module.

1. Moved the generated settings configuration to an ignored local file beside
   the original host settings, preserving discovery of the official `buildSrc`.
2. Reran the affected compile/test/JAR tasks.
3. All passed; original root settings/build/source files have empty diffs.

The pinned build and local alternate-settings mechanism emit Gradle deprecation
warnings for Gradle 9. Keep 8.14.3; any future wrapper migration needs a separate
upgrade validation. These warnings did not fail the selected tasks.

**A subsequent setup with an empty Gradle cache failed on the first wrapper
download with `UnknownHostException: services.gradle.org`.** Java proxy
properties were passed after project/settings arguments, so distribution
bootstrap did not receive them. Retained Gradle files had hidden this failure.

1. Moved proxy JVM properties before the project/settings arguments in the
   helper, retaining the same restricted networking, TLS trust and checksum.
2. Repeated first-download installation with the corrected helper; verified
   Gradle 8.14.3 bootstrap and package/distribution checks.
3. Added `verify-clean-setup.sh` to exercise committed source and an empty
   dependency directory, including compilation/JAR and both module tests.
   This is the regression procedure for the bootstrap failure; its latest
   complete outcome is reported with the subsequent verification.

## Networking, saved configuration and limits

Networking remains restricted with the `package_managers` preset. Existing
custom domains are `api.github.com` and `repository.axelor.com`; no additional
domain was needed during this setup. Git/API access and Maven/Gradle/package
downloads worked. No production secret or additional secret requirement was
used, saved or printed.

Saved configuration: the draft tool confirmed `status: saved` and
`requires_publish: true` for `install_script`, `start_skill`, and the laboratory
repository declaration at the exact starting HEAD and `cencomun-erp-lab` mount
path. The host/submodule were identified as pinned dependency caches rather
than additional project checkouts. Existing networking and secret requirements
were preserved. A draft save does not publish or execute the scripts. No live
server is needed for this cloud workflow, and no process is assumed to survive
a snapshot. A subsequent configuration read after reconnection shows a new
active version, no pending draft, both saved scripts and the exact repository
reference/mount. The source, toolchain and caches were retained, and executing
the saved development-start commands passed again. No additional configuration
save is needed for those unchanged instructions.

The environment name/separate saved-environment membership is not exposed by
the tools; this report describes the attached machine only. At the end of the
initial setup the source and reports were local for review. A subsequent task
continuation verifies and records the baseline in `lab/axelor-baseline`;
generated caches/results stay outside source control. Issue closure is outside
this setup's scope.
The active configuration and retained files were verified after reconnection;
restoration in an independently created new task has not been tested.

Full-stack requirements and untested startup commands are documented separately
in `labs/axelor/FULL_STACK_RUNNER.md`.
