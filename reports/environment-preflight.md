# Issue #1 — Environment preflight

Date: 2026-10-04. Executed before Issue #3 on `lab/axelor-baseline`.

## Initial state

Checkout: `/workspace/cencomun-erp-lab`; HEAD `33c413764de947b9e6610318ccc673ec6ac0150f`. The checkout was clean before setup. Switched from the clean Frappe branch to the user-requested Axelor branch using the existing checkout; no worktree or reset was used.

Read `docs/CODEX_CLOUD_SETUP.md` first, then root and Axelor agent instructions, version pins, charter, comparison protocol and Tasks 001/020. GitHub Issues #1/#3 were read with existing authentication. No credentials were printed or requested.

## Resources and initial tools

| Item | Version / availability |
| --- | --- |
| OS / architecture | Debian GNU/Linux 13 (trixie), Linux x86_64 |
| CPU | 5 visible processors; cgroup quota 4 CPUs |
| Memory | 32 GiB cgroup limit; approximately 32 GiB available; no swap |
| Disk | Approximately 30 GiB free in `/workspace` |
| Git | 2.52.0 |
| Python | 3.12.14 |
| Node / npm / pnpm | 24.19.0 / 11.9.0 / 11.19.0 |
| Java runtime | OpenJDK 21.0.12.1 |
| Java compiler | Missing from the initial runtime; JDK installation required |
| Gradle | Global Gradle absent; use the pinned host wrapper only |
| Docker client | 28.4.0; full-stack tests not selected for cloud |
| Yarn / Podman | Missing; not prerequisites for the selected module compilation |

## Checks, pins and networking

- `./scripts/preflight.sh`: passed at 2026-10-04T14:53:05Z on the Axelor branch.
- `./scripts/verify-repo.sh`: passed.
- Existing Git authentication and branch fetch: passed.
- Initial Git status: clean; `versions.lock` unchanged.
- Pinned baseline: AOS `v9.1.8`, AOP family `8.2`, Java `21`, PostgreSQL `>= 12`. Frappe pins unchanged.
- Saved policy: restricted networking, preset `package_managers`, existing custom domains `api.github.com` and `repository.axelor.com`. No additional domains added during preflight.
- Existing-instance HEAD request to the Axelor Maven public repository: HTTP 200. Individual build artifact resolution still needs validation.

## Limitations and next step

Issue #1's preflight and initial limitations are recorded before Issue #3. Install a complete, pinned Java 21 JDK; verify the official Gradle 8.14.3 distribution checksum; use the pinned webapp host for the isolated module. Exact installed versions and compilation/test outcomes will be recorded in `reports/axelor-baseline.md`.

The configuration tool does not expose an environment name. This report describes the attached instance and does not establish that two separately named saved environments exist. No publication or fresh-task validation is claimed.

## Post-setup verification

After Issue #3 setup, Java and javac both report OpenJDK 21.0.12.1 from the
checksum-verified local JDK. The host wrapper reports Gradle 8.14.3. With that
JDK activated, preflight was repeated successfully at 2026-10-04T15:06:31Z.
Repository guardrails, custom compilation and two named tests passed;
`versions.lock` and upstream tracked files remain unchanged. The available
cloud development workflow and installation repeatability are validated;
full-stack/database/server checks remain unrun.
