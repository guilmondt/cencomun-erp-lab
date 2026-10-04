#!/usr/bin/env bash
set -euo pipefail
echo "== repository verification =="
required=(AGENTS.md README.md versions.lock docs/PROJECT_CHARTER.md docs/COMPARISON_PROTOCOL.md docs/CORE_TEST_SPEC.md docs/ACCEPTANCE_CRITERIA.md docs/VENEZUELA_REQUIREMENTS.md contracts/ccm-adapter.yaml)
for f in "${required[@]}"; do
  test -f "$f" || { echo "Missing required file: $f" >&2; exit 1; }
done
if find . -type f \( -name '.env' -o -name '*.pem' -o -name '*.key' -o -name 'id_rsa' \) -not -path './.git/*' | grep -q .; then
  echo "Potential secret-bearing files found." >&2; exit 1
fi
echo "Repository guardrails passed."
