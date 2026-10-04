# Axelor external runner execution plan

Date: 2026-10-04. Branch: `lab/axelor-baseline`.

The user delegated runner selection. Use GitHub Actions on a disposable hosted
runner: existing repository CI works, and no maintained server or production
secret is needed. This extends Task 020's validation, without business features.

1. [x] Read cloud setup, agent rules, pins and comparison protocol; rerun Issue
   #1 preflight and guardrails before creating the runner.
2. [x] Verify immutable official image/action/runtime references and inspect
   AOP 8.2.3's external configuration, initialization, login and REST endpoints.
3. [ ] Create an isolated Docker harness for the external runner, signed exact
   JDK installation, verified Node/Yarn, original full-suite host settings,
   frozen frontend installation and explicit non-formatting Gradle targets.
4. [ ] Execute the actual GitHub Actions job, retaining current logs and test
   XML. Diagnose failures and rerun only after a concrete correction.
5. [ ] Verify PostgreSQL-backed authenticated metadata requests, Cencomun/AOS
   discovery and restart against the same disposable database. Confirm source
   and pins remain unchanged; record passed, failed and unrun checks separately.
6. [ ] Update the full-stack instructions and baseline report with measured
   results, limitations and numbered remedies for any external blocker.

Docker services run only on the external host, never in Codex Cloud. Temporary
configuration and generated test credentials stay outside source/artifacts.
Destroy only the containers/network/database created by this harness. Do not
merge main, close issues, modify upstream, refresh module locks or disable
assertions, authentication, TLS or checksums. GitHub Actions is independent of
the cloud's existing restricted package-manager network configuration.
