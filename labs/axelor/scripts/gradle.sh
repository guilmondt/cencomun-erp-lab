#!/usr/bin/env bash
set -euo pipefail

runtime_dir=${CCM_AXELOR_RUNTIME:-/workspace/ccm-axelor-runtime}
export JAVA_HOME="$runtime_dir/jdk/usr/lib/jvm/java-21-openjdk-amd64"
export GRADLE_USER_HOME="$runtime_dir/gradle-home"
export PATH="$JAVA_HOME/bin:$PATH"
test -x "$JAVA_HOME/bin/javac"

# Java does not consume HTTPS_PROXY itself. Configure host/port only; never log
# credentials or put proxy values in the repository or the saved configuration.
proxy_flags=()
proxy_arguments=$(python3 - <<'PY'
import os
from urllib.parse import urlsplit
for protocol in ("https", "http"):
    value = os.environ.get(protocol.upper() + "_PROXY") or os.environ.get(protocol + "_proxy")
    if value:
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            raise SystemExit("Authenticated Java proxies require supported runtime configuration")
        if parsed.hostname:
            print(f"-D{protocol}.proxyHost={parsed.hostname}")
            print(f"-D{protocol}.proxyPort={parsed.port or 80}")
PY
)
if test -n "$proxy_arguments"; then
  while IFS= read -r flag; do
    proxy_flags+=("$flag")
  done <<< "$proxy_arguments"
fi

settings_flags=()
if test "${CCM_AXELOR_FULL_STACK:-0}" != 1; then
  settings_flags=(--settings-file "$runtime_dir/open-suite-webapp/ccm-cloud.settings.gradle")
fi

# The wrapper must receive JVM properties before project/settings arguments,
# so the very first distribution download uses the proxy too.
exec "$runtime_dir/verified-wrapper/gradlew" \
  "${proxy_flags[@]}" \
  -p "$runtime_dir/open-suite-webapp" \
  "${settings_flags[@]}" --no-daemon --max-workers=2 --console=plain "$@"
