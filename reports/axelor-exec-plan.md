# Execution plan — Issue #3 / Task 020

## Objective

Prepare only Axelor on `lab/axelor-baseline`: a minimal version-controlled module under `com.cencomun.*`, no business features, no upstream core edits. Keep the user-specified host, gitlink, Java toolchain, Gradle wrapper and AOP plugin exact.

## Sequence

1. [x] Read setup/agent/project instructions; execute Issue #1 preflight and guardrails; record the initial report before implementation.
2. [x] Fetch host `axelor/open-suite-webapp` at `1119727a3b53c8387b7fab535e184c25154d2eac`, verify tag and gitlink `0c70d561b19fc454eba9fdd41689258846626d75`. Set only local submodule URL to HTTPS.
3. [x] Install/activate a pinned JDK 21 including compiler outside the checkout. Verify official Gradle 8.14.3 checksum; configure wrapper validation externally without changing upstream tracked files.
4. [x] Inspect supported module integration and create only the isolated Cencomun skeleton and meaningful import/compile/unit validation.
5. [x] Build/test with the host wrapper and bounded resources; diagnose failures without weakening verification, assertions or source restrictions. Two tests pass, including a final frozen-lock run; scoped settings preserve the official root/buildSrc.
6. [x] Record full-stack runner requirements separately, final versions/check results and decisions. Test reusable setup instructions and save installation/start instructions in the draft. A subsequent read confirmed a new active configuration without a pending draft, and startup/tests passed after reconnection. Restoration in an independently created new task remains unverified.

## Validation and preservation

Use the existing isolated checkout without a Git worktree. Keep `versions.lock` and upstream tracked files unchanged. Keep tool/dependency caches outside the laboratory checkout. Before finishing run guardrails, verify Git changes, check actual test counts and report skipped/unrun checks. Use TLS and checksum/signature verification throughout. Do not save untested commands as verified or claim publication/fresh-task restoration.
