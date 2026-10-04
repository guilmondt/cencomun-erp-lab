# AGENTS.md — Cencomun ERP Lab

## Mission
This repository is a controlled technical evaluation of **ERPNext/Frappe v16** versus **Axelor Open Suite 9.1** as the transactional base for Cencomun OS.

The objective is to generate reproducible evidence about extensibility, maintainability, performance, ERP correctness, upgrade safety, API ergonomics, and suitability for continuous development.

## Non-negotiable rules
1. Never modify upstream framework/ERP source code to implement Cencomun features.
2. No production credentials, customer data, bank data, private source code, or private vendor material in this repository.
3. Do not copy proprietary Venezuelan localization code or closed documentation. Implement from public law/regulation, public specifications, public behavior, and Cencomun-owned requirements.
4. Pin versions. Do not silently upgrade dependencies, frameworks, runtimes, databases, or build tools.
5. Do not use latest, master, main, or floating dependency versions as a reproducible baseline unless the task explicitly requires upstream exploration.
6. Every bug fix must include a regression test where technically possible.
7. Every feature must include acceptance tests tied to the shared Cencomun Core Test.
8. Do not optimize for implementation speed at the expense of correctness or fairness.
9. Do not bypass framework business logic with direct database writes.
10. Do not weaken permissions, validation, audit, accounting, or inventory rules merely to make a test pass.
11. No destructive migrations without an explicit rollback/recovery plan.
12. Never claim parity or success without running the required checks.

## Required workflow
Before editing: read this file and nested AGENTS.md files, PROJECT_CHARTER, COMPARISON_PROTOCOL and the task; run ./scripts/preflight.sh; inspect Git status and versions.lock; create an ExecPlan for substantial work.

During implementation: prefer supported extension points; keep platform work scoped; record compromises in docs/DECISIONS.md; add tests.

Before finishing: run available platform checks and ./scripts/verify-repo.sh; report exactly what was and was not tested.

## Architecture principles
- ERP is the transactional system of record for ERP-domain data.
- Chatwoot remains the communications system unless a later decision changes that.
- EvoNexus/AI is orchestration/reasoning, not financial source of truth.
- AI never replaces deterministic accounting, payroll, tax, inventory, reconciliation, or approval logic.
- External systems integrate through documented APIs/adapters/events, never direct DB coupling.
- Search may become a separate Cencomun service; ERP-native search is still benchmarked.

## Venezuela clean-room requirement
Treat Venezuelan localization as a Cencomun-owned implementation based on public sources and Cencomun requirements.

## Definition of done
Requirements met; tests added/passing where runnable; no unauthorized upstream core edits; documentation updated; limitations recorded; comparison remains reproducible.
