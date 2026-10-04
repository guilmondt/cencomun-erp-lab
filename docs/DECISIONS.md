# Architecture Decision Log

## ADR-XXX — Title
- Date:
- Platform: Shared / Frappe / Axelor
- Status: Proposed / Accepted / Rejected / Superseded
- Context:
- Options considered:
- Decision:
- Consequences:
- Upgrade impact:
- Evidence/tests:

## ADR-001 — Frappe baseline without cloud database services
- Date: 2026-10-04
- Platform: Frappe
- Status: Accepted for the baseline task
- Context: Issue #2 requires an isolated custom-app skeleton; cloud policy
  reserves full ERP/database tests for a dedicated runner.
- Options considered: run the full ERP in cloud; create only source files;
  build and install the package in cloud and document the separate runner.
- Decision: use the tagged Frappe v16.36.1 app structure and a pinned Flit
  toolchain; test source and a clean wheel installation. Keep all Cencomun
  code under `labs/frappe/cencomun_erp`; require ERPNext through app hooks.
- Consequences: no upstream edits, business features, database-only artifacts
  or production secrets. Cloud validation proves packaging/registration
  resources, not Frappe site installation or ERP behavior. License and contact
  metadata are explicitly unselected/placeholder values, pending owner choice
  before distribution.
- Upgrade impact: future platform upgrades must rerun packaging checks and
  the dedicated-runner installation/registration and business regression tests.
- Evidence/tests: five tests against the editable package and the same five
  against a clean installed wheel; wheel built from sdist. See
  `reports/frappe-baseline.md` and `labs/frappe/FULL_STACK.md`.

## ADR-002 — User-authorized real-site validation in cloud
- Date: 2026-10-04
- Platform: Frappe
- Status: Accepted for the explicitly requested integral validation
- Context: the user requested real MariaDB/Redis/site validation equivalent
  to the completed Axelor validation, expanding the earlier DB-free setup.
- Decision: run isolated, loopback services under a user-owned `/workspace`
  prefix; use exact upstream commits, Python/Node/tool pins and dependency
  locks. Generate only local synthetic credentials and use supported Frappe
  document/authentication/queue APIs; implement no Cencomun business features.
- Consequences: full-stack setup works without root or Docker-in-Docker.
  MariaDB uses libaio fallback because cloud io_uring is unavailable. Preserve
  upstream source/locks; resolve banking frontend dependencies outside its
  checkout with a frozen local lock. No cross-branch merge is performed.
- Upgrade impact: retain these service/runtime pins and rerun real-site tests
  before any later upgrade. This is no accounting/production-readiness claim.
- Evidence/tests: 39 functional checks, real app/module registration, assets,
  worker execution, graceful restart/persistence and five skeleton tests passed.
  See `reports/frappe-integral.md` and `reports/frappe-integral-evidence.json`.
