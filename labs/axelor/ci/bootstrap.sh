#!/usr/bin/env bash
set -euo pipefail
cd /workspace/cencomun-erp-lab
source labs/axelor/ci/pins.sh
export DEBIAN_FRONTEND=noninteractive
# This is a disposable external build container, not the Codex Cloud machine.
# Debian slim initially has no CA bundle. Bootstrap it with signed APT metadata
# before switching APT to HTTPS; signatures and package hashes remain enforced.
apt-get update
apt-get install --yes --no-install-recommends ca-certificates
sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources
apt-get update
apt-get install --yes --no-install-recommends \
  ca-certificates curl git python3 ripgrep unzip xz-utils procps \
  "openjdk-21-jdk-headless=$CCM_JDK_PACKAGE_VERSION" \
  "openjdk-21-jre-headless=$CCM_JDK_PACKAGE_VERSION"
git config --global --add safe.directory /workspace/cencomun-erp-lab
dpkg-query -W -f='${Package}\t${Version}\n' > "$CCM_CI_STATE/results/debian-packages.tsv"
bash labs/axelor/ci/validate-full-stack.sh
