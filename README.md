# Cencomun ERP Lab

Controlled evaluation of **ERPNext/Frappe 16** and **Axelor Open Suite 9.1** as the transactional foundation for Cencomun OS.

## What this repository is
A reproducible laboratory, not a production ERP and not a fork of either upstream project.

The shared test workload is defined in `docs/CORE_TEST_SPEC.md` and includes:
- extending the standard Product model,
- Cashea Order,
- cash closing,
- purchase approvals,
- bank import/reconciliation,
- API/adapters,
- event integration,
- MCP-facing capability contract,
- search/performance tests,
- upgrade-resilience tests.

## Repository map
- `labs/frappe/` — Frappe/ERPNext implementation notes and Cencomun app location
- `labs/axelor/` — Axelor implementation notes and Cencomun module location
- `docs/` — shared requirements, decisions, methodology
- `tasks/` — ordered implementation tasks for Codex
- `contracts/` — platform-neutral contracts
- `fixtures/` — synthetic shared test data
- `benchmarks/` — benchmark protocol/results
- `scripts/` — environment and repository checks

## Critical rule
Do not implement Cencomun features by modifying upstream ERP/framework source. Use supported custom-app/module extension mechanisms.

See `AGENTS.md` before any work.
