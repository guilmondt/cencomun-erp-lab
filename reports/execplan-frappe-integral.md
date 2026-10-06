# ExecPlan — Frappe/ERPNext integral validation

## Authorized scope

The user explicitly requests a real site with MariaDB/Redis, Cencomun app
installation, authentication, API, persistence and restart, using synthetic
data and publishing reproducible evidence. This expands the earlier DB-free
cloud baseline; do not implement business features or merge branches.
Work remains on `lab/frappe-baseline`. Leave `versions.lock` and upstream
Frappe/ERPNext sources unchanged.

## Sequence

1. Install isolated runtimes/services below `/workspace`: Python 3.14.0,
   Node 24.19.0, Bench 5.29.0, Yarn 1.22.22, MariaDB 11.8 and pinned Redis.
   Verify artifacts using signed package indexes/hashes or pinned Git commits.
2. Initialize Bench at Frappe/ERPNext v16.36.1, register the existing
   `cencomun_erp` package, and build assets.
3. Create a loopback-only synthetic site with generated local test credentials
   outside the repository. Verify real installed-app/module registration.
4. Exercise public health, rejected unauthenticated access, password login,
   authenticated identity, API create/read/update, token authentication,
   logout and denied invalid credentials, through supported framework APIs.
5. Stop and restart the services started by this validation; confirm database
   persistence and re-authenticated API access after restart.
6. Publish redacted evidence, exact versions/dependency locks and tested
   reproduction/start instructions. Update the existing review PR without merge.

## Evidence contract

Record actual command exit codes and functional assertions; distinguish
passed, failed, blocked and unrun checks. No secret values, cookies, tokens,
site configurations, production data or database contents enter Git.
Make no ERP correctness, Core Test parity or production-readiness claim.

## Progress

- Initial branch clean; repository preflight and guardrails passed.
- No MariaDB/Redis/Bench services exist in the restored machine.
- Exact runtimes and signed/hash-verified Debian services installed in a user-owned prefix.
- Real site created; all three apps installed; assets built; upstream checkouts clean.
- 39 HTTP/infrastructure checks passed across a complete graceful service restart.
- Five existing skeleton tests passed in the real framework environment.
- Installation refresh and the full runner repeated successfully without recreating data.
- Publishing reproducible scripts, locks, evidence and startup configuration.
