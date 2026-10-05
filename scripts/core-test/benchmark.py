"""20 warmups + 1000 serial HTTP samples per frozen selected operation."""

import csv, json, math, os, platform, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path("/workspace/cencomun-erp-lab")
OUT = REPO / "reports/evidence/frappe-core"
private = json.loads((ROOT / "core-private.json").read_text())
spec = json.loads((REPO / "fixtures/ccm-core-v1/benchmark.json").read_text())
loaded = json.loads((OUT / "benchmark-loaded.json").read_text())
u = private["users"]["operator"]
auth = "token " + u["api_key"] + ":" + u["api_secret"]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
ROWS = []


def invoke(kind, index, warmup):
    p = {"company_id": "CCM-LAB-001"}
    method = "GET"
    data = None
    headers = {"Authorization": auth, "Content-Type": "application/json"}
    if kind == "search":
        path = "/products/search?" + urllib.parse.urlencode(
            {**p, **spec["selected"]["search"]}
        )
    elif kind == "inventory":
        path = "/inventory/BENCH-P0000?" + urllib.parse.urlencode(
            {**p, "warehouse": loaded["warehouse"]}
        )
    else:
        identifier = ("BENCH-WARM-" if warmup else "BENCH-SAMPLE-") + f"{index:04}"
        path = "/cashea/orders"
        method = "POST"
        headers["Idempotency-Key"] = identifier
        data = json.dumps(
            {
                **p,
                "id": identifier,
                "customer_id": "BENCH-C000",
                "warehouse": loaded["warehouse"],
                "channel": "STORE",
                "currency": "USD",
                "tax_rate": "0",
                "financed_amount": "6.00",
                "shipping_expense": "0.00",
                "guide": None,
                "datetime": spec["clock"],
                "lines": [
                    {"product_id": "BENCH-P0000", "qty": "1", "unit_price": "10.00"}
                ],
            }
        ).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:8090" + path, data=data, headers=headers, method=method
    )
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=120) as response:
            body = json.load(response)
            status = response.status
    except urllib.error.HTTPError as exc:
        body = json.load(exc)
        status = exc.code
    elapsed = (time.perf_counter() - started) * 1000
    meta = body.get("_meta", {})
    ROWS.append(
        {
            "operation": kind,
            "warmup": int(warmup),
            "sample": index,
            "http_status": status,
            "elapsed_ms": round(elapsed, 5),
            "server_ms": meta.get("server_ms"),
            "query_count": meta.get("query_count"),
            "db_ms": meta.get("db_ms"),
        }
    )
    assert status == (201 if kind == "create" else 200), {
        "kind": kind,
        "status": status,
        "body": body,
    }
    assert "query_count" in meta and "db_ms" in meta, "Native DB metrics missing"
    if kind == "search":
        assert [r["id"] for r in body["items"]] == ["BENCH-P0000"]
    if kind == "inventory":
        assert body["on_hand"] == "5"
    if kind == "create":
        assert body["status"] == "NEW" and not body["replay"]
    return elapsed


results = []
try:
    for kind in ["search", "inventory", "create"]:
        for i in range(20):
            invoke(kind, i, True)
        measured = [invoke(kind, i, False) for i in range(1000)]
        ordered = sorted(measured)
        results.append(
            {
                "operation": kind,
                "samples": 1000,
                "warmup": 20,
                "errors": 0,
                **{
                    f"p{p}": round(ordered[math.ceil(p / 100 * len(ordered)) - 1], 5)
                    for p in [50, 95, 99]
                },
            }
        )
        print(kind, results[-1], flush=True)
    status = "PASS"
except Exception as e:
    status = "FAIL"
    results.append({"error": type(e).__name__ + ": " + str(e)})
finally:
    with (OUT / "benchmark-raw.csv").open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "operation",
                "warmup",
                "sample",
                "http_status",
                "elapsed_ms",
                "server_ms",
                "query_count",
                "db_ms",
            ],
        )
        w.writeheader()
        w.writerows(ROWS)
    resources = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "cpu_affinity": len(os.sched_getaffinity(0)),
        "memory_total_kb": int(
            next(
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemTotal:")
            )
        ),
        "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip()
        if Path("/sys/fs/cgroup/cpu.max").exists()
        else None,
        "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if Path("/sys/fs/cgroup/memory.max").exists()
        else None,
    }
    (OUT / "benchmark.json").write_text(
        json.dumps(
            {
                "status": status,
                "seed": 100,
                "loaded": loaded,
                "operations": results,
                "resources": resources,
                "units": "milliseconds",
                "percentile": "nearest-rank",
                "serial": True,
                "native_query_recorder": True,
                "note": "Fixed business payload; deterministic per-sample IDs exercise real creation. Warmup and measured IDs are disjoint; no replay timed as creation. Read operations do not mutate their initial state; NEW creation does not change stock/accounting.",
            },
            indent=2,
        )
        + "\n"
    )
