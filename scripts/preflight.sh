#!/usr/bin/env bash
set -euo pipefail
echo "== Cencomun ERP Lab preflight =="
echo "date_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "pwd=$(pwd)"
echo "os=$(uname -s 2>/dev/null || true)"
echo "arch=$(uname -m 2>/dev/null || true)"
printf '\n-- resources --\n'
(command -v nproc >/dev/null && echo "cpus=$(nproc)") || true
(command -v free >/dev/null && free -h) || true
(df -h . 2>/dev/null || true)
printf '\n-- tools --\n'
for cmd in git python3 python node npm pnpm yarn java javac gradle docker podman; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '%-10s ' "$cmd"; "$cmd" --version 2>&1 | head -n 1 || true
  else
    printf '%-10s MISSING\n' "$cmd"
  fi
done
printf '\n-- git --\n'
git status --short --branch || true
printf '\n-- pins --\n'
cat versions.lock
