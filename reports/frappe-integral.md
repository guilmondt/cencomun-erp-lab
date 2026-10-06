# Frappe/ERPNext integral validation

**Result: all required checks passed.** No business features were implemented;
work stays on `lab/frappe-baseline`. No branch was merged.

Validation run: `95cb0046cca34b19a8662a6f9cbba493`. Evidence recorded in UTC:
`2026-10-04T20:48:24.834725+00:00`. Machine: Debian 13.6, Linux x86_64, user `agent`,
5 reported CPUs, 33 GiB RAM. Services run below a user-owned `/workspace`
prefix; no Docker-in-Docker or system/root installation was used.

## Required outcomes

| Area | Actual evidence | Result |
| --- | --- | --- |
| Real site | `ccm-frappe.test` created on MariaDB 11.8.6 with Redis 8.0.2 | Passed |
| App installation | Frappe 16.36.1, ERPNext 16.36.1, Cencomun 0.0.1 installed; real Module Def and hooks confirmed | Passed |
| Build/web | Assets compiled; login HTML and actual manifest-selected Desk JavaScript served via Nginx | Passed |
| Authentication | Password login, cookie identity, API token identity, rejected wrong password/token | Passed |
| Access denial/logout | Anonymous identity/private Note denied; logout and replay of revoked cookie denied | Passed |
| API | Synthetic standard Note created, read, updated and read back through REST | Passed |
| Persistence | Updated Note content read unchanged after all services stopped and restarted | Passed |
| Restart | Seven service process identities changed; five listening ports were closed before restart | Passed |
| Redis/worker | Both instances pinged; real Frappe job completed with expected result before/after restart | Passed |
| Socket.IO | Engine.IO polling handshake succeeded through the Unix socket proxy before/after restart | Passed |

Final executed checks: **17 HTTP before restart + 14 HTTP after restart +
4 infrastructure before + 4 after = 39 passed**, zero failed/skipped.
The graceful restart orchestration passed in
3.64 seconds, including readiness and post-restart checks.
Five existing skeleton tests also passed in Bench's real Python environment.
Real installation/module registration was checked separately through Frappe.
No zero-test framework run is presented as success.

## Exact reproducible inputs

- Frappe tag v16.36.1, commit `97a5dd93ca5883bcc9c4ef9834120c5cba397b67`.
- ERPNext tag v16.36.1, commit `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba`.
- Cencomun custom app 0.0.1; its business source is unchanged from the baseline.
- Python 3.14.0; Node 24.19.0; Bench 5.29.0; Yarn 1.22.22.
- MariaDB package `1:11.8.6-0+deb13u1`; Redis
  `5:8.0.2-3+deb13u3`; Nginx `1.26.3-3+deb13u9`.
- Signed Debian indexes, exact package versions and SHA-256 values for 13
  artifacts: `labs/frappe/integral/debian-packages.lock.json`.
- 152 frozen Python runtime dependency entries, including immutable Gunicorn
  and PyPika Git commits: `labs/frappe/integral/python-runtime.lock`.
- Bench-tool lock, Yarn tool npm lock, upstream frozen frontend locks and the
  resolved banking lock are retained under `labs/frappe/integral/`.
- Native `mysqlclient==2.2.7` uses the pinned MariaDB shared client library.
- `versions.lock` unchanged; Frappe and ERPNext Git statuses clean.
- Runner/config/lock SHA-256 values are recorded in the JSON evidence.

## Reproduce in this prepared Debian 13 amd64 environment

```sh
cd /workspace/cencomun-erp-lab
bash scripts/frappe-integral/install.sh
bash scripts/frappe-integral/run.sh
```

The installer was executed successfully after the initial setup and repeated.
It verifies cached Debian artifacts and installed content, reuses the site,
installs exact dependencies, uses frozen frontend locks, rebuilds assets and
checks real app registration. It never force-drops an existing database.
The runner was repeated and exercises HTTP before and after a complete
service restart; it also runs the five existing package tests and guardrails.

Machine-local output is `reports/generated/frappe-integral/evidence.json`
(ignored by Git). To prepare the explicit public report:

```sh
source scripts/frappe-integral/env.sh
python scripts/frappe-integral/publish_evidence.py \
  --output reports/frappe-integral-evidence.json
```

The collector rejects mixed run IDs, incomplete/failed outcomes, wrong branch,
modified upstreams and any known credential value. It publishes only explicit
check outcomes and metadata, not logs, requests, cookies, tokens or site config.

## Start and stop

```sh
cd /workspace/cencomun-erp-lab
source scripts/frappe-integral/env.sh
python scripts/frappe-integral/services.py start
python scripts/frappe-integral/services.py status
# Stop only these lab-owned processes when needed:
python scripts/frappe-integral/services.py stop
```

The startup readiness function checks a real `pong` response; see
`validate_restart.py`. Nginx listens on loopback 8080, Gunicorn on 8000,
MariaDB on 3307, Redis cache/queue on 13000/11000. Socket.IO uses a Unix socket.
These are internal validation endpoints, not public previews.
Live processes do not survive environment publication. The current-instance
startup/restart commands were tested; they must run again on a restored machine.

## Synthetic data and credential handling

Only a fictitious `validation@example.invalid` System Manager and standard
private Notes are used. No custom DocTypes, accounting, inventory, purchasing,
sales or localization features were added. All application writes use supported
Frappe document/HTTP APIs. SQL is used only for database bootstrap administration
and a read-only version query.

Generated local lab passwords and native Frappe API keys remain in private
runtime files below `/workspace/.local/frappe-integral`, outside Git. The site
configuration, database, session material and raw logs are not published.
The whole runtime root is private; credential files have mode 0600.

## Diagnosed setup/runner failures and corrections

Initial failures are **resolved**, and are not counted as passing executions:

1. Empty database password triggered an interactive prompt. The installer now
   creates a password-protected local bootstrap account and supplies its
   generated value without printing it; the private site logs retain the exit code.
2. MySQL client import failed with `TLS_client_method` because a shared-library
   symlink target was missing and the build picked a static archive. The signed
   client-library package was added and mysqlclient 2.2.7 rebuilt. The installer
   validates its import and rebuilds only when necessary.
3. App names were concatenated because `sites/apps.txt` lacked a final newline.
   The installer writes parsed entries with an explicit final newline; real app
   discovery and installation confirm the correction.
4. ERPNext's install hook changed its tracked banking lock. The accidental
   change was restored; the final workflow skips that recursive hook and installs
   banking dependencies outside the checkout using a frozen resolved lock.
5. Gunicorn did not serve static bundles. The tested Nginx configuration now
   serves the real asset manifest path and proxies backend/Socket.IO requests.
   All Nginx temporary directories are explicitly placed under `/workspace`.
6. A runner asserted a cosmetic logout message that Frappe does not return.
   The final test instead proves logout with denied access and denied replay
   of the revoked cookie. A failed worker probe likewise used an unsupported
   forwarded keyword; its call now follows Frappe's enqueue signature.
7. Direct framework probes needed Bench's `sites` working directory for logs.
   The framework probe scripts select that documented directory explicitly.

For a future failure: retain the first failing command and exit status,
inspect its private service log, correct that specific prerequisite, and
rerun the affected check. Do not disable TLS/hashes, weaken permissions or
modify upstream code to make a check pass.

## Remaining limitations

- This is one Debian 13 amd64 cloud instance. Installation refresh and cold
  process restart passed; independent fresh-machine/snapshot restoration was
  not tested. Locked Debian mirror revisions may eventually need an archival
  source; the verified downloaded artifacts are retained in the prepared runtime.
- Restart was graceful, not a power failure, database crash, backup restore or
  upgrade trial. io_uring is unavailable; MariaDB successfully uses libaio.
- The synthetic API user has standard System Manager permissions. Role-matrix,
  multi-tenant and production authorization audits were not performed.
- Login HTML/assets and Socket.IO handshake were checked; a complete browser
  interaction and authenticated realtime event flow were not exercised.
- Public deployment/TLS, email, PDFs, background scheduler, load/performance,
  all upstream test suites and Cencomun Core Test business correctness are unrun.
- Contact/license metadata remain explicit placeholders. No production-readiness
  or ERP accounting/inventory parity claim follows from these checks.
- Repository CI guardrails are separate from the 39 live-machine functional
  checks; the full service workflow was not executed in GitHub Actions.

The user requested evidence publication on the Frappe branch only. The review
PR is updated with these results; no branch merge or issue closure is required
by this validation.
