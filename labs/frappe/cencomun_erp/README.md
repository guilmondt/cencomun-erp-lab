# Cencomun ERP

Minimal custom app for the Frappe/ERPNext evaluation. App name: `cencomun_erp`;
module: `Cencomun ERP`; initial version: `0.0.1`. No DocTypes, business logic,
fixtures, permissions, scheduled jobs, API endpoints or migrations are implemented.

Bench owns the Frappe/ERPNext dependencies; they are deliberately absent from
the app's pip requirements. The baseline is Frappe and ERPNext `v16.36.1`,
Python `3.14`, Node `24`, and MariaDB `11.8`, as recorded in the repository's
`versions.lock`. Use supported extension points within this package only.

The structure follows the pinned framework's boilerplate: `hooks.py`,
`modules.txt`, a module package with `.frappe`, `patches.txt`, public assets,
templates and configuration namespaces. Flit builds the app distribution.

Run the DB-free build/install checks from the lab repository:

```sh
bash scripts/verify-frappe-baseline.sh
```

These tests validate package imports, registration and packaged discovery
resources. They do not load the Frappe runtime or demonstrate ERP behavior.
See `../FULL_STACK.md` for the separate dedicated-runner workflow.

Contact metadata uses the explicit placeholder `maintainers@example.invalid`.
No license has been granted by this skeleton (`app_license = "UNLICENSED"`).
Set owner-approved contact and licensing metadata before distributing the app.
