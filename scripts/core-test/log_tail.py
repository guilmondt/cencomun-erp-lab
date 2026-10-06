"""Print a private log after redacting local synthetic credentials."""

import json, sys, re
from pathlib import Path

root = Path("/workspace/.local/frappe-integral")
values = []


def walk(v):
    if isinstance(v, dict):
        for k, x in v.items():
            if any(
                s in k.lower() for s in ("password", "api_key", "api_secret", "encryption_key")
            ) and isinstance(x, str) and len(x) >= 8:
                values.append(x)
            else:
                walk(x)
    elif isinstance(v, list):
        for x in v:
            walk(x)


for p in [root / 'secrets.json', root / 'core-private.json',
          *(root / 'official-tests').glob('*private.json'),
          *(root / 'bench/sites').glob('*/site_config.json'),
          root / 'official-bench/sites/common_site_config.json',
          *(root / 'official-bench/sites').glob('*/site_config.json')]:
    if p.exists():
        walk(json.loads(p.read_text()))
s = Path(sys.argv[1]).read_text()
for v in values:
    s = s.replace(v, "[REDACTED]")
s = re.sub(r'(--(?:admin|db-root|db)-password(?:\s+|=))(\S+)', r'\1[REDACTED]', s)
print("\n".join(s.splitlines()[-int(sys.argv[2] if len(sys.argv) > 2 else 18) :]))
