# Codex Cloud Setup

Use separate saved environments:
- ccm-erp-lab-frappe
- ccm-erp-lab-axelor

Start with Package managers internet access, not unrestricted internet. Add domains only when setup proves they are required.

No production secrets are needed initially. Keep secrets out of source files and committed .env files.

Do not make the lab depend on Docker-in-Docker in Codex Cloud unless that environment explicitly proves it works reliably. Cloud is for source analysis, coding, compilation, unit tests, static checks, planning and review. Full ERP + DB/service tests belong in CI or a dedicated runner.

## Generic setup prompt
Read AGENTS.md, versions.lock, docs/PROJECT_CHARTER.md, and docs/COMPARISON_PROTOCOL.md before configuring anything. This is a controlled Axelor-vs-Frappe benchmark. Do not change version pins, use floating branches/latest, add secrets, or modify upstream source. Run ./scripts/preflight.sh and ./scripts/verify-repo.sh. Configure only dependencies needed for this platform. Report exact installed versions and any network domains additionally required. Publish the environment only after setup is reproducible and limitations are documented.

## Frappe follow-up
Configure the Frappe side only. Respect versions.lock. Use a custom-app workflow. Do not customize ERPNext/Frappe core. Validate the custom app skeleton and tests. Do not implement business features yet.

## Axelor follow-up
Configure the Axelor side only. Respect versions.lock. Use Java 21 and the project Gradle wrapper. Keep Cencomun code in an isolated custom module namespace. Validate the module skeleton. Do not implement business features yet.
