# ExecPlan — Issue #2: Frappe baseline

## Scope and prerequisites

Issue #1 completed first; evidence: `reports/environment-preflight.md`.
Use branch `lab/frappe-baseline`, Frappe/ERPNext v16.36.1, Python 3.14,
and Node 24. Keep upstream source and `versions.lock` unchanged.
Deliver only a Cencomun custom-app skeleton and baseline validation, no Core Test features.

## Implementation

1. Inspect the tagged Frappe boilerplate and installation contract.
2. Add the `cencomun_erp` package under `labs/frappe/`, with hooks, an empty
   module, module/patch declarations, and asset/template directories.
3. Pin the small packaging toolchain. Validate source imports, build wheel
   and sdist, install the wheel in a clean environment, and validate its resources.
4. Document separate full-stack prerequisites, exact upstream commits,
   commands, limitations, and supported extension boundaries.
5. Run repository guardrails and save tested cloud installation/start instructions.

## Acceptance

- Source and installed-wheel tests execute (nonzero count).
- Wheel/sdist build succeeds and includes framework-discovery files.
- No framework source edits, credentials, business models or migrations.
- Full-stack checks clearly marked unrun; no ERP readiness/parity claim.

## Progress

- Issue #1: complete locally before Issue #2.
- Tagged boilerplate and module discovery inspected; upstream tags resolve.
- Skeleton, source/installed-wheel checks, runner guide and ADR complete.
- Packaging checks repeated successfully; final environment configuration saved separately.
