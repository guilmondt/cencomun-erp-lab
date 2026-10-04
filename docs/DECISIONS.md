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
