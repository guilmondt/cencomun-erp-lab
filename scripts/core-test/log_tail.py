"""Print a private log after redacting local synthetic credentials."""

import json, sys
from pathlib import Path

root = Path("/workspace/.local/frappe-integral")
values = []


def walk(v):
    if isinstance(v, dict):
        for k, x in v.items():
            if any(
                s in k.lower() for s in ("password", "api_key", "api_secret")
            ) and isinstance(x, str):
                values.append(x)
            else:
                walk(x)
    elif isinstance(v, list):
        for x in v:
            walk(x)


for name in ("secrets.json", "core-private.json"):
    p = root / name
    if p.exists():
        walk(json.loads(p.read_text()))
s = Path(sys.argv[1]).read_text()
for v in values:
    s = s.replace(v, "[REDACTED]")
print("\n".join(s.splitlines()[-int(sys.argv[2] if len(sys.argv) > 2 else 18) :]))
