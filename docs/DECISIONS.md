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

## ADR-001 — Isolated Axelor cloud module baseline

- Date: 2026-10-04
- Platform: Axelor
- Status: Accepted for the initial laboratory baseline
- Context: Task 020 requires a custom module on Java 21, AOS v9.1.8 and AOP
  8.2, without upstream changes or business features. Full-stack services
  belong in a dedicated runner.
- Options considered: configure/build every AOS module in cloud; prepare a
  representative empty module in the official pinned webapp host.
- Decision: use webapp commit `1119727a3b53c8387b7fab535e184c25154d2eac`, its
  exact AOS gitlink, AOP 8.2.3, Java 21.0.12.1 and a checksum-enforcing local
  copy of its Gradle 8.14.3 wrapper. Register `com.cencomun:cencomun-baseline`
  through local integration, with scoped settings preserving the host root
  build/buildSrc, and lock the new module's dependency graph.
- Consequences: upstream tracked files and `versions.lock` remain unchanged;
  cloud validates module compilation, injection compatibility and generated
  discovery metadata. It does not establish whole-suite/ERP/server/database
  readiness. No Cencomun business behavior is implemented.
- Upgrade impact: the local scoped settings generator requires the pinned
  host's settings layout; Gradle alternate-settings deprecation must be
  revisited in a separately authorized wrapper upgrade. Full-suite frontend
  and database dependencies require dedicated runner validation.
- Evidence/tests: `reports/environment-preflight.md`,
  `reports/axelor-baseline.md`; 2 tests passed, 0 failed/errors/skipped;
  repeated setup and frozen-lock compile/test/JAR validation passed.

## ADR-002 — GitHub Actions for Axelor full-stack validation

- Date: 2026-10-04
- Platform: Axelor
- Status: Accepted; full-stack baseline validated on the hosted runner
- Context: Cloud setup reserves full ERP/database/service tests for an external
  runner. The user delegated the choice and repository GitHub Actions works.
- Options considered: hosted GitHub Actions; a maintained self-hosted server.
- Decision: use a branch-triggered workflow and disposable PostgreSQL/build
  containers on an actual hosted Docker VM. Fix official image/action/runtime
  references; keep the existing AOS/AOP commits, wrapper and Cencomun module.
- Consequences: no server administration or production secrets needed. Preserve
  source, frozen frontend installation and external per-run dependency locks;
  publish sanitized logs/test artifacts and authenticated read-only API evidence.
  Full-suite Maven locks are evidence of each run, not yet a completely frozen
  branch dependency replay. Cloud networking remains restricted and separate.
- Upgrade impact: changing an image/runtime/upstream reference requires its own
  checksum/reference checks and rerunning compilation, API smoke and restart.
- Evidence/tests: `reports/axelor-full-stack.md`,
  `reports/axelor-full-stack-exec-plan.md`, `.github/workflows/axelor-full-stack.yml`;
  run 37228746936 passed full compilation/WAR, 18 unit cases, strict offline
  Gradle replay, PostgreSQL authenticated metadata API and server restart with
  33 modules. First startup 422.42s, restart 315.44s; tracked upstream diffs empty.

## ADR-003 — Native Core entities with an independently retained cloud baseline

- Date: 2026-10-06
- Platform: Axelor
- Status: Accepted within the user-authorized Core Test implementation
- Context: Shared product fields require durable framework entities and real
  foreign keys to native company/product, while the original cloud AOP-only
  compilation and its frozen dependency lock remain reproducible.
- Decision: declare Cencomun models in `com.cencomun.core.db`; the full-stack
  profile depends on the existing pinned AOS base project. Its build directory
  is `build/full`, set before AOP plugin application in the supported CI init
  script. Full dependency locks remain external per-run evidence. Cloud compiles
  the AOP services/policies, generates and parses the domain, and excludes
  native-FK generated classes/resources from its artifact.
- Consequences: full-stack compilation and authenticated native CRUD are
  mandatory for entity acceptance. Cloud unit tests never prove their native
  persistence. Exclude any merged `com.axelor` generated dependency classes
  from the custom compilation; verify that its full JAR contains none. All
  native ERP classes remain supplied by the fixed upstream modules.
- Permissions: product tests use an actual synthetic operator, native Role and
  Permission with `self.company.id = ?1` evaluated from `__user__.activeCompany.id`.
  No global wildcard grant, impersonation or administrator CRUD acceptance.
- Upgrade impact: AOS API or domain changes require recompile and native FK/CRUD
  regression on a separately approved target; no baseline pins are changed.
- Evidence/tests: `PROD01-04` runner implements six warranty quantity/unit
  round trips and price retention on disable, with separate committed REST
  rereads. Acceptance remains pending until the new full-stack run executes it.

## ADR-004 — Native daily currency configuration and scoped rate authorization

- Date: 2026-10-06
- Platform: Axelor
- Status: Implementation authorized; native acceptance pending
- Decision: use AOS CurrencyConversionLine with one-day validity and the pinned
  CurrencyService for payment-day selection and line rounding. Manager
  authorization lives in a Cencomun AOP entity linked to the native conversion,
  with company, reason and actual approving User in one transaction. Native
  overlap validation remains enabled. No external provider or secret is used.
- Permissions: authenticated native Operator/Manager sessions can calculate;
  only Manager can authorize in the LAB company. The custom service checks the
  actual native role and company on each call. No general currency/AppBase CRUD
  grant is given. The service is unavailable unless CCM_CORE_LAB=1.
- Consequences: AOS currencies are global application configuration in this
  isolated database. This test does not establish a production multitenant FX
  policy, the six neutral routes, audit completeness or rate idempotency.
- Evidence: FX01-03-MONEY01-03 compares the fixed fixture results and fresh
  native rate/authorization rows. Missing-rate and operator denials must leave
  those rows unchanged. Native runtime verification is pending the next CI.
