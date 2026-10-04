# Frappe-specific instructions

Scope: labs/frappe/**

- Use a custom Frappe app for all Cencomun behavior.
- Do not edit ERPNext or Frappe core.
- Prefer supported hooks, DocType extension, fixtures, patches, and versioned app code.
- Avoid critical customizations/server scripts that exist only in the DB/UI; if prototyped, export or convert them into version-controlled app artifacts before completion.
- Pin ERPNext/Frappe according to versions.lock.
- Do not use direct SQL for ordinary business logic when the Document API is appropriate.
- Money/business calculations require server-side tests.
