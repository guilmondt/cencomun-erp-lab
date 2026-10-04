#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
runtime_dir=${CCM_AXELOR_RUNTIME:-/workspace/ccm-axelor-runtime}
export JAVA_HOME="$runtime_dir/jdk/usr/lib/jvm/java-21-openjdk-amd64"
export GRADLE_USER_HOME="$runtime_dir/gradle-home"
export PATH="$JAVA_HOME/bin:$PATH"
# Regression: a separate build named buildSrc has no application projects.
# Gradle implicitly applies Java when it builds buildSrc; represent that in an
# isolated fixture without editing or treating upstream buildSrc as standalone.
fixture_dir=$(mktemp -d "$runtime_dir/ccm-init-scope.XXXXXX")
trap 'rm -rf "$fixture_dir"' EXIT
printf "rootProject.name = 'buildSrc'\n" > "$fixture_dir/settings.gradle"
printf "plugins { id 'java' }\n" > "$fixture_dir/build.gradle"
"$runtime_dir/verified-wrapper/gradlew" \
  -p "$fixture_dir" \
  --init-script "$repo_dir/labs/axelor/ci/full-stack.init.gradle" \
  --no-daemon --max-workers=2 --console=plain :jar

# Regression: simulate AOP resolving runtimeClasspath during project evaluation.
# Use built-in Java/tasks and a minimal node extension, with no network packages.
mkdir -p "$fixture_dir/host/modules/axelor-base" "$fixture_dir/locks"
export CCM_CI_STATE="$fixture_dir"
cat > "$fixture_dir/host/settings.gradle" <<'GRADLE'
rootProject.name = 'axelor-erp'
include 'modules:axelor-base'
GRADLE
cat > "$fixture_dir/host/build.gradle" <<'GRADLE'
plugins { id 'java' }
tasks.register('run', JavaExec)
afterEvaluate { configurations.runtimeClasspath.resolve() }
GRADLE
cat > "$fixture_dir/host/modules/axelor-base/build.gradle" <<'GRADLE'
plugins { id 'java' }
extensions.add('node', [
  version: objects.property(String).convention('24.5.0'),
  yarnVersion: objects.property(String).convention('1.22.19'),
  download: objects.property(Boolean).convention(true)
])
tasks.register('installFrontDeps') { ext.args = [] }
GRADLE
"$runtime_dir/verified-wrapper/gradlew" \
  -p "$fixture_dir/host" \
  --init-script "$repo_dir/labs/axelor/ci/full-stack.init.gradle" \
  --no-daemon --max-workers=2 --console=plain :jar --write-locks
