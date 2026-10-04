#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
runtime_dir=${CCM_AXELOR_RUNTIME:-/workspace/ccm-axelor-runtime}
host_dir="$runtime_dir/open-suite-webapp"
host_commit=1119727a3b53c8387b7fab535e184c25154d2eac
aos_commit=0c70d561b19fc454eba9fdd41689258846626d75
jdk_version=21.0.12.1+1-1~deb13u1
gradle_sha256=bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531

cd "$repo_dir"
./scripts/preflight.sh
./scripts/verify-repo.sh
test "$(uname -m)" = x86_64
. /etc/os-release
test "$ID" = debian && test "$VERSION_ID" = 13
python3 - <<'PY'
import tomllib
with open('versions.lock', 'rb') as stream:
    pins = tomllib.load(stream)
assert pins['axelor']['aos_reference'] == 'v9.1.8'
assert pins['axelor']['aop_family'] == '8.2'
assert pins['axelor']['java'] == '21'
PY

mkdir -p "$runtime_dir/debs" "$runtime_dir/jdk"
# These SHA-256 values came from the authenticated Debian trixie package index.
# Exact package versions preserve the existing JRE patch level, without apt
# installing globally or writing package-manager configuration outside /workspace.
for entry in \
  'jdk:f3abafb6c644b03df042824e707cd211ea33254761d7f7b75be3f8dc0df97c7a' \
  'jre:e95f36193e45464ac758e5436f940bf3eaecc77de67188275a42104f58aa7674'; do
  component=${entry%%:*}
  digest=${entry#*:}
  artifact="openjdk-21-${component}-headless_${jdk_version}_amd64.deb"
  package_file="$runtime_dir/debs/$artifact"
  if ! test -f "$package_file"; then
    curl --fail --location --silent --show-error \
      "https://deb.debian.org/debian/pool/main/o/openjdk-21/$artifact" \
      -o "$package_file.part"
    mv "$package_file.part" "$package_file"
  fi
  printf '%s  %s\n' "$digest" "$package_file" | sha256sum --check -
  dpkg-deb --extract "$package_file" "$runtime_dir/jdk"
done
export JAVA_HOME="$runtime_dir/jdk/usr/lib/jvm/java-21-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
javac -version
test "$(javac -version 2>&1)" = 'javac 21.0.12.1'

if ! test -d "$host_dir/.git"; then
  git clone --no-checkout https://github.com/axelor/open-suite-webapp.git "$host_dir"
  git -C "$host_dir" checkout --detach "$host_commit"
fi
test "$(git -C "$host_dir" rev-parse HEAD)" = "$host_commit"
test "$(git -C "$host_dir" rev-parse 'v9.1.8^{commit}')" = "$host_commit"
test "$(git -C "$host_dir" ls-tree HEAD modules/axelor-open-suite | awk '{print $3}')" = "$aos_commit"
git -C "$host_dir" diff --exit-code
git -C "$host_dir" diff --cached --exit-code
# Only local Git configuration is changed; .gitmodules remains untouched.
git -C "$host_dir" config submodule.axelor-open-suite.url https://github.com/axelor/axelor-open-suite.git
git -C "$host_dir" submodule update --init --depth 1
test "$(git -C "$host_dir/modules/axelor-open-suite" rev-parse HEAD)" = "$aos_commit"
git -C "$host_dir/modules/axelor-open-suite" diff --exit-code

python3 - "$host_dir" <<'PY'
from pathlib import Path
import sys
host = Path(sys.argv[1])
assert "id 'com.axelor.app' version '8.2.3'" in (host / 'settings.gradle').read_text()
assert 'JavaLanguageVersion.of(21)' in (host / 'build.gradle').read_text()
assert 'gradle-8.14.3-bin.zip' in (host / 'gradle/wrapper/gradle-wrapper.properties').read_text()
PY
official_digest=$(curl --fail --location --silent --show-error \
  https://services.gradle.org/distributions/gradle-8.14.3-bin.zip.sha256)
test "$official_digest" = "$gradle_sha256"
mkdir -p "$runtime_dir/verified-wrapper/gradle/wrapper"
cp "$host_dir/gradlew" "$runtime_dir/verified-wrapper/gradlew"
cp "$host_dir/gradle/wrapper/gradle-wrapper.jar" "$runtime_dir/verified-wrapper/gradle/wrapper/"
cp "$host_dir/gradle/wrapper/gradle-wrapper.properties" "$runtime_dir/verified-wrapper/gradle/wrapper/"
printf '\ndistributionSha256Sum=%s\n' "$gradle_sha256" >> \
  "$runtime_dir/verified-wrapper/gradle/wrapper/gradle-wrapper.properties"
chmod +x "$runtime_dir/verified-wrapper/gradlew"

module_link="$host_dir/modules/cencomun-baseline"
module_source="$repo_dir/labs/axelor/cencomun-baseline"
if test -L "$module_link"; then
  test "$(readlink -f "$module_link")" = "$module_source"
elif test -e "$module_link"; then
  echo 'Refusing to replace an existing custom module path.' >&2
  exit 1
else
  ln -s "$module_source" "$module_link"
fi
# Dependency host checkout: keep local integration out of tracked upstream files.
if ! rg --quiet --fixed-strings '/modules/cencomun-baseline' "$host_dir/.git/info/exclude"; then
  printf '\n/modules/cencomun-baseline\n' >> "$host_dir/.git/info/exclude"
fi

# A local settings file retains the official root build and buildSrc, but limits
# cloud configuration to the representative custom module. Full AOS/services
# are tested separately by the dedicated runner using the original settings.
python3 - "$host_dir" <<'PY'
from pathlib import Path
import sys
host = Path(sys.argv[1])
original = (host / 'settings.gradle').read_text()
start = original.index('def modules = []')
end = original.index('gradle.ext.appModules = modules', start)
scoped = original[:start] + "def modules = [file('modules/cencomun-baseline')]\n\n" + original[end:]
destination = host / 'ccm-cloud.settings.gradle'
if destination.exists() and destination.read_text() != scoped:
    raise SystemExit('Refusing to overwrite modified local cloud settings')
destination.write_text(scoped)
PY
if ! rg --quiet --fixed-strings '/ccm-cloud.settings.gradle' "$host_dir/.git/info/exclude"; then
  printf '\n/ccm-cloud.settings.gradle\n' >> "$host_dir/.git/info/exclude"
fi

bash "$repo_dir/labs/axelor/scripts/gradle.sh" --version
./scripts/verify-repo.sh
