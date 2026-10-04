# Frappe dedicated-runner validation

This workflow is separate from Codex Cloud onboarding. It has not been run
in the cloud machine. The cloud checks exercise the custom package without
loading Frappe, using a site, or connecting to MariaDB/Redis.

## Prerequisites

Use a disposable Linux runner with synthetic data only:

- Frappe `v16.36.1`, commit `97a5dd93ca5883bcc9c4ef9834120c5cba397b67`.
- ERPNext `v16.36.1`, commit `fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba`.
- Python `3.14.0`; the framework requires `>=3.14,<3.15`.
- Node `24.19.0`, Yarn `1.22.22`, Bench `5.29.0`.
- MariaDB `11.8`, with a runner-pinned patch release and configuration
  supporting Frappe's `utf8mb4` database requirements. Do not substitute the
  OS distribution's database if it differs from `versions.lock`.
- A runner-pinned Redis release compatible with Frappe 16 and Bench-generated
  cache/queue configuration. Record its exact version in the runner report.
- Database development headers, pkg-config and a C/C++ toolchain for
  `mysqlclient`; system libraries required by Frappe's PDF/image dependencies.
- An isolated database administrator account for creating the test site,
  supplied securely by the runner; no production access.
- TLS-verified package-registry and upstream Git access. Preserve upstream
  requirements/lockfiles and record resolved Python dependencies and service
  versions; tag pins alone do not freeze their entire dependency graph.

The exact database/Redis patch releases and operating-system dependencies
must be fixed in the runner image before calling its setup reproducible.
No complete full-stack dependency lock or tested runner image is supplied yet.

## Run in order

1. Check out this lab at the reviewed `lab/frappe-baseline` commit and run
   `./scripts/preflight.sh` and `./scripts/verify-repo.sh`.
2. Install the pinned Bench and Yarn into the runner's chosen isolated tools
   environment. Verify `python --version`, `node --version`, `yarn --version`,
   `bench --version`, `mariadb --version`, and `redis-server --version`.
3. Initialize a new Bench and install ERPNext. Replace the Python path with
   the runner's Python 3.14.0 executable:

   ```sh
   bench init --frappe-branch v16.36.1 \
     --python /path/to/python3.14 ccm-frappe-bench
   cd ccm-frappe-bench
   test "$(git -C apps/frappe rev-parse HEAD)" = \
     97a5dd93ca5883bcc9c4ef9834120c5cba397b67
   bench get-app --branch v16.36.1 erpnext https://github.com/frappe/erpnext
   test "$(git -C apps/erpnext rev-parse HEAD)" = \
     fb78e58b8c037bcff4f90b7361ad81ff7b1c42ba
   ```

4. Register this monorepo's app without copying or modifying upstream source.
   Use an absolute path for `CCM_LAB_CHECKOUT`. This is a standalone package
   inside the lab, not a standalone Git repository for `bench get-app`:

   ```sh
   CCM_LAB_CHECKOUT=/absolute/path/to/cencomun-erp-lab
   test ! -e apps/cencomun_erp
   ln -s "$CCM_LAB_CHECKOUT/labs/frappe/cencomun_erp" apps/cencomun_erp
   ./env/bin/python -m pip install \
     -r "$CCM_LAB_CHECKOUT/labs/frappe/requirements-build.lock" --require-hashes
   ./env/bin/python -m pip install --no-build-isolation --no-deps \
     -e apps/cencomun_erp
   if ! rg -qx cencomun_erp sites/apps.txt; then
     echo cencomun_erp >> sites/apps.txt
   fi
   ```

5. Start MariaDB and the Bench-configured Redis/services. In a separate
   terminal run `bench start` and inspect all process output. Create the site
   with `bench new-site ccm-frappe.test`, entering the isolated runner's
   credentials through the interactive prompts. Do not put credentials in
   shell history or the repository.
6. Install the apps and build assets:

   ```sh
   bench --site ccm-frappe.test install-app erpnext
   bench --site ccm-frappe.test install-app cencomun_erp
   bench build --app cencomun_erp
   bench --site ccm-frappe.test list-apps
   ```

7. Verify app/module registration with the real framework:

   ```sh
   bench --site ccm-frappe.test console
   ```

   In the console:

   ```python
   import frappe
   assert "cencomun_erp" in frappe.get_installed_apps()
   assert frappe.get_module_list("cencomun_erp") == ["Cencomun ERP"]
   assert frappe.get_hooks("required_apps", app_name="cencomun_erp") == ["erpnext"]
   assert frappe.get_doc("Module Def", "Cencomun ERP").app_name == "cencomun_erp"
   ```

8. Exercise a real request: `curl --fail http://127.0.0.1:8000/api/method/ping
   -H 'Host: ccm-frappe.test'` must return `{"message":"pong"}`.
   This is an internal validation request, not a public preview link.
9. Execute the five package tests using Bench's Python:

   ```sh
   ./env/bin/python -m unittest discover \
     -s "$CCM_LAB_CHECKOUT/labs/frappe/tests" -v
   ```

10. Record exact runtime/service versions, commits, exit statuses, five-test
    count, build result, app registration and HTTP response in the runner's
    report. Check `git diff --exit-code` in both upstream checkouts. Preserve
    failed and unrun results; do not infer success from a running PID.

There are no Frappe database/business tests in this empty skeleton. Future
Core Test features must add their server-side tests and acceptance evidence
before any ERP correctness or platform parity claim.

## Troubleshooting

1. Python mismatch: activate Python 3.14.0 and recreate only the disposable
   runner environment; do not alter the version pins.
2. `mysqlclient` cannot compile: inspect its build output, install the runner's
   MariaDB development headers and pkg-config, verify `pkg-config --exists
   mysqlclient`, then retry the failed dependency installation.
3. Database or Redis connection failure: inspect service logs, verify the
   runner's versions and Bench/site configuration, and retry a service health
   check before app installation. Do not weaken permissions to bypass failure.
4. App not listed: verify the app symlink, editable package installation and
   exactly one `cencomun_erp` entry in `sites/apps.txt`, then retry installation.
5. Any unresolved failure: retain the command and exit status in the report;
   classify it as setup failure or application defect before claiming readiness.
