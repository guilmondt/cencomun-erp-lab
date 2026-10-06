#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
baseline=e0190090fd137576ce273e350d7ce6686d66baf9
# Fail early if history is missing; never substitute the current pins for the reference.
git -C "$repo_dir" cat-file -e "$baseline^{commit}"
git -C "$repo_dir" cat-file -e "$baseline:versions.lock"
git -C "$repo_dir" diff --exit-code "$baseline" -- versions.lock
