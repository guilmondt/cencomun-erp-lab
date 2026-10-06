# Issue #2 — Frappe/ERPNext baseline

This report records the initial DB-free baseline. The later user-authorized
real-site validation is documented in `frappe-integral.md` and
`frappe-integral-evidence.json`; its results supersede the service availability
and unrun full-stack statements below.

Prepared on `lab/frappe-baseline` after Issue #1 acceptance was documented.
Date: 2026-10-04. App: `cencomun_erp` 0.0.1; namespace: `Cencomun ERP`.

## Deliverables

- Custom app: `labs/frappe/cencomun_erp/`, using tagged Frappe boilerplate conventions.
- Registration-only hooks, empty custom module with `.frappe`, module and patch manifests,
  asset/template/configuration directories, and a Flit build manifest.
- Five package-contract tests: `labs/frappe/tests/test_baseline.py`.
- Repeatable cloud check: `bash scripts/verify-frappe-baseline.sh`.
- Pinned, hash-verified build toolchain: `labs/frappe/requirements-build.lock`.
- Separate dedicated-runner requirements and steps: `labs/frappe/FULL_STACK.md`.
- Decision and limitations: ADR-001 in `docs/DECISIONS.md`.

## Verified results

- Editable-package installation: passed, without Frappe/site/service dependencies.
- Source/editable tests: 5 passed; installed-wheel tests: the same 5 passed.
  Five distinct tests, ten successful executions per complete validation run.
  No failed, skipped or expected-failure tests.
- Sdist and wheel: built successfully; wheel built from the sdist.
- Clean wheel installation: passed; package metadata version confirmed as 0.0.1.
- Installed resources: `modules.txt`, `patches.txt`, module `.frappe`, public
  directory and template namespace confirmed present through the tests.
- Complete validation repeated successfully with existing tools and caches.
- Latest validation wall time: 0.766 seconds, including
  dependency checks, tests, packaging and clean-wheel installation.
  Build time alone was not separately instrumented.
- Repository guardrails, shell syntax validation and `git diff --check`: passed.
- `versions.lock`: unchanged.

Generated artifacts are ignored under `reports/generated/frappe-baseline/`:
`cencomun_erp-0.0.1.tar.gz` and `cencomun_erp-0.0.1-py3-none-any.whl`.
Build environment: `/workspace/.venvs/ccm-frappe-build`.
Temporary wheel environments are removed after validation.

## Exact pins and upstream evidence

Python 3.14.0, Node 24.19.0. Packaging tools: build 1.3.0, flit_core 3.12.0,
packaging 25.0, pyproject_hooks 1.2.0. No floating build-tool requirement.
Frappe and ERPNext are managed by Bench, not installed as app pip dependencies.

- Frappe v16.36.1: `97a5dd93ca5883bcc9c4ef9834120c5cba397b67`.
- ERPNext v16.36.1: `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba`.
- Both tags verified through native HTTPS Git reads.
- Inspected the tagged framework's `frappe/utils/boilerplate.py`,
  `frappe/installer.py`, `frappe/__init__.py` and
  `frappe/deprecation_dumpster.py`; used its module-discovery convention.

## Comparison measurements and boundaries

Upstream files edited: 0. Custom-app Python nonblank/noncomment lines:
15 (includes namespace docstrings and metadata). Migration entries:
0. Business DocTypes, domain services, fixtures, APIs and jobs: 0.
Equivalent business API calls, latency percentiles, DB timings, search,
permissions, accounting correctness and upgrade trials: not applicable to
this skeleton and not measured. No platform parity claim.

The full Frappe runtime, Bench assets, site installation, Module Def database
registration and HTTP endpoint were not exercised in cloud. MariaDB/Redis
are not installed. These are separate full-stack checks, not failed cloud
package tests. No Frappe test runner invocation with zero tests is reported as
success. Full-stack dependency/service patch locking remains a runner task.

The app contact is the documented placeholder `maintainers@example.invalid`;
license metadata is `UNLICENSED`, pending owner selection before distribution.
No production secret values were requested or added.

## Local delivery and environment configuration

Existing tracked application/framework code was not modified. New skeleton,
tests, helper and reports are local repository changes; only the required
ADR was added to an existing documentation file. This baseline is prepared
for a version-controlled delivery on `lab/frappe-baseline` and a review PR
against `main`. GitHub issue closure and merge are separate review actions.

The cloud configuration is updated separately with the tested install/start
instructions. Saving a draft does not run or publish it. The selected workflow
is DB-free custom-app development and packaging, not a running ERP deployment.

## If a cloud check fails

1. Run `python3 --version`. If it is not 3.14.0, activate the saved Python path
   from `reports/environment-preflight.md` and rerun the installation script.
2. Run `bash scripts/verify-frappe-baseline.sh` from the repository and retain
   the first failing command, output and exit code.
3. For a dependency-download block, identify the hostname from the error;
   preserve the restricted network policy and request only the required domain.
4. For a checksum/TLS failure, verify the artifact and trust configuration.
   Do not disable hashes, signatures or TLS validation.
5. For an import/resource failure, inspect the current generated wheel and
   failed test, then correct the app packaging in a coding task. Do not weaken
   the assertion or change framework core.
6. Rerun the affected check and `./scripts/verify-repo.sh`. Record any remaining
   failure and keep ERP/service checks marked unrun until a dedicated runner
   supplies actual evidence.
