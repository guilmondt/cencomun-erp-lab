# Project Charter — Cencomun ERP Lab

## Decision
Determine whether ERPNext/Frappe or Axelor is the stronger long-term transactional platform for Cencomun OS.

## Neutralized factor
Venezuelan localization availability is not treated as a platform advantage. Cencomun will own the localization implementation.

## What matters most
1. Continuous extension without upstream core modification.
2. ERP correctness: accounting, inventory, purchasing, sales, AR/AP, multi-currency, audit.
3. Safe upgrades.
4. API/event integration.
5. MCP/AI integration without making AI transactional source of truth.
6. Performance/search at realistic volume.
7. Permissions/auditability.
8. Developer productivity.
9. Dev/Test/Staging/Production reproducibility.
10. Long-term control of code and data.

## Principles
Evidence beats preference. Same test, same data, same acceptance criteria. Document workarounds. Count maintenance cost, not only implementation speed.
