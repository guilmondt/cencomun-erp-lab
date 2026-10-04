# Comparison Protocol

For each platform record setup complexity, files changed, Cencomun-owned LOC, upstream files changed (target zero), migrations, test count/runtime, API calls for equivalent business actions, build time, measurable p50/p95/p99, query/DB timing, upgrade breakage, documentation gaps, and developer interventions.

Use only synthetic shared fixtures.

A feature is complete only when it meets docs/ACCEPTANCE_CRITERIA.md.

Any critical configuration performed in a web UI must be exportable/versionable or recorded as a negative finding.

After the Core Test is stable, perform a patch upgrade trial: snapshot, upgrade, migrate, run full regression, record changes needed.
