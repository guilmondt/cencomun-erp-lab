"""Private supervisor for the two loopback-only laboratory services."""

import importlib.util, sys, os
from pathlib import Path

REPO = Path("/workspace/cencomun-erp-lab")
ROOT = Path("/workspace/.local/frappe-integral")
spec = importlib.util.spec_from_file_location(
    "supervisor", REPO / "scripts/frappe-integral/services.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.STATE = ROOT / "core-http-services.json"
m.specifications = lambda: {
    "adapter": [
        str(ROOT / "bench/env/bin/python"),
        str(REPO / "scripts/core-test/adapter.py"),
    ],
    "consumer": [
        str(ROOT / "bench/env/bin/python"),
        str(REPO / "scripts/core-test/consumer.py"),
    ],
}
os.environ["CCM_ENABLE_FAULTS"] = "1"
getattr(m, sys.argv[1])(["adapter", "consumer"])
