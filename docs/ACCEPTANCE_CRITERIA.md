# Acceptance Criteria

1. Shared domain objects use supported framework mechanisms.
2. No Cencomun feature requires upstream core edits.
3. Critical actions enforce permissions server-side.
4. Invalid state transitions are rejected.
5. Monetary calculations are deterministic and tested.
6. Confirmed cash closing leaves an audit trail and cannot be silently changed.
7. Purchase thresholds are automated and tested.
8. Bank import is idempotent for repeated transaction/file keys.
9. APIs require no direct DB access.
10. MCP-facing operations can use the neutral adapter.
11. Synthetic fixtures load successfully.
12. Search/list results are complete and non-duplicated.
13. Platform + Cencomun tests pass after a patch upgrade trial.
14. Setup is reproducible from repository instructions.
