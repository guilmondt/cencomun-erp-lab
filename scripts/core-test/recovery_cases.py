"""Real lost-response + graceful restart + durable outbox consumer tests."""

import sys, json, os, subprocess, time, urllib.request, urllib.error, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Importing HTTP definitions would re-run tests; this standalone client stays separate.
ROOT = Path("/workspace/.local/frappe-integral")
REPO = Path("/workspace/cencomun-erp-lab")
OUT = REPO / "reports/evidence/frappe-core"
CASES = []
private = json.loads((ROOT / "core-private.json").read_text())
mapping = json.loads((OUT / "http-mapping.json").read_text())


def auth(label):
    d = private["users"][label]
    return "token " + d["api_key"] + ":" + d["api_secret"]


def post(payload, lose=False):
    h = {
        "Authorization": auth("operator"),
        "Content-Type": "application/json",
        "Idempotency-Key": "IDEM-LOST",
    }
    if lose:
        h["X-CCM-Lab-Lose-Response"] = "once"
    q = urllib.request.Request(
        "http://127.0.0.1:8090/cashea/orders",
        data=json.dumps(payload).encode(),
        headers=h,
    )
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
        q, timeout=120
    ) as r:
        return r.status, json.load(r)


def shell(args, label, env=None):
    with (ROOT / ("logs/core-" + label + ".log")).open("w") as f:
        r = subprocess.run(args, cwd=REPO, env=env, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError(label + " exit " + str(r.returncode))
    return r.returncode


def checked(case, criteria, fn):
    try:
        r = fn()
        CASES.append(
            {"case": case, "criteria": criteria, "status": "PASS", "actual": r,
             "coverage_revision": 2}
        )
        print(case, "PASS", flush=True)
    except Exception as e:
        CASES.append(
            {
                "case": case,
                "criteria": criteria,
                "status": "FAIL",
                "coverage_revision": 2,
                "error": type(e).__name__ + ": " + str(e),
            }
        )
        print(case, "FAIL", str(e), flush=True)


def lost():
    base = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())[0]
    p = {
        **base,
        "id": "IDEM-LOST",
        "company_id": "CCM-LAB-001",
        "warehouse": mapping["lost_warehouse"],
    }
    try:
        post(p, True)
    except Exception as e:
        transport = type(e).__name__
    else:
        raise AssertionError("Response was not lost")
    shell(
        [sys.executable, str(REPO / "scripts/core-test/http_services.py"), "start"],
        "adapter-recovery",
    )
    time.sleep(0.5)
    status, result = post(p)
    assert status == 200 and result["replay"] is True and result["id"] == "IDEM-LOST"
    shell(
        [
            sys.executable,
            str(REPO / "scripts/frappe-integral/services.py"),
            "stop",
            "mariadb",
            "redis_cache",
            "redis_queue",
            "web",
            "worker",
        ],
        "restart-stop",
    )
    shell(
        [
            sys.executable,
            str(REPO / "scripts/frappe-integral/services.py"),
            "start",
            "mariadb",
            "redis_cache",
            "redis_queue",
            "web",
            "worker",
        ],
        "restart-start",
    )
    ready = False
    for _ in range(40):
        try:
            status, recovered = post(p)
            ready = status == 200 and recovered.get("replay") is True
        except Exception:
            ready = False
        if ready:
            break
        time.sleep(0.25)
    assert ready, "Restart did not recover committed result"
    assert {
        k: recovered[k] for k in ["id", "gross", "commission", "cost", "status"]
    } == {k: result[k] for k in ["id", "gross", "commission", "cost", "status"]}
    return {
        "lost_transport": transport,
        "adapter_exit_injection": 73,
        "before_restart": result,
        "after_restart": recovered,
        "recovered_http": status,
        "services": ["mariadb", "redis_cache", "redis_queue", "web", "worker"],
    }


checked("IDEM03-LOST-RESTART", [4, 9, 14], lost)


def dispatch(label, replay=False):
    script = ROOT / "core-event-dispatch.py"
    script.write_text(
        "import json\nfrom pathlib import Path\nfrom cencomun_erp.core.events import deliver\nPath("
        + repr(str(ROOT / "core-event-result.json"))
        + ").write_text(json.dumps(deliver(replay="
        + str(replay)
        + ")))\n"
    )
    shell(
        [sys.executable, str(REPO / "scripts/core-test/site_command.py"), str(script)],
        label,
    )
    return json.loads((ROOT / "core-event-result.json").read_text())


def events():
    flag = ROOT / "core-consumer-fail"
    flag.write_text("Synthetic 503")
    try:
        failed = dispatch("events-failed")
    finally:
        flag.unlink(missing_ok=True)
    assert failed["failed"] > 0 and failed["delivered"] == 0
    def consumer_snapshot():
        with sqlite3.connect(ROOT / "core-consumer.sqlite") as connection:
            receipts = [{"event_id": row[0], "payload": json.loads(row[1]), "deliveries": row[2]}
                for row in connection.execute("SELECT event_id,payload,deliveries FROM receipts ORDER BY event_id")]
            effects = [{"event_id": row[0], "type": row[1], "object_id": row[2], "applications": row[3]}
                for row in connection.execute("SELECT event_id,effect_type,object_id,applications FROM effects ORDER BY event_id")]
        return {"receipts": receipts, "effects": effects}
    expect_empty = consumer_snapshot()
    assert expect_empty == {"receipts": [], "effects": []}
    # First SUCCESS precedes restart; persistence is checked before re-delivery.
    recovered = dispatch("events-first-success")
    assert recovered["delivered"] == failed["failed"] and recovered["failed"] == 0
    before_restart = consumer_snapshot()
    assert len(before_restart["effects"]) == recovered["delivered"]
    assert all(r["deliveries"] == 1 for r in before_restart["receipts"])
    assert all(r["applications"] == 1 for r in before_restart["effects"])
    service_before = json.loads((ROOT / "core-http-services.json").read_text())["consumer"]
    shell(
        [sys.executable, str(REPO / "scripts/core-test/http_services.py"), "stop", "consumer"],
        "event-consumer-stop",
    )
    shell(
        [sys.executable, str(REPO / "scripts/core-test/http_services.py"), "start", "consumer"],
        "event-consumer-start",
    )
    time.sleep(0.5)
    service_after = json.loads((ROOT / "core-http-services.json").read_text())["consumer"]
    assert service_before != service_after
    after_restart = consumer_snapshot()
    assert after_restart == before_restart
    replay = dispatch("events-replayed", True)
    assert replay["delivered"] == recovered["delivered"] and replay["failed"] == 0
    after_replay = consumer_snapshot()
    receipts = after_replay["receipts"]
    assert after_replay["effects"] == before_restart["effects"]
    assert [{k: v for k, v in r.items() if k != "deliveries"} for r in receipts] == [
        {k: v for k, v in r.items() if k != "deliveries"} for r in before_restart["receipts"]]
    assert len(receipts) == recovered["delivered"] and all(
        r["deliveries"] == 2 for r in receipts
    )
    for r in receipts:
        assert all(
            k in r["payload"]
            for k in [
                "schema_version",
                "event_id",
                "object_id",
                "company_id",
                "actor",
                "occurred_at",
                "correlation_id",
            ]
        )
    return {
        "failed_transport": failed,
        "retry": recovered,
        "replay": replay,
        "sequence": ["503_failure", "successful_delivery", "consumer_restart", "same_event_replay"],
        "before_restart": before_restart,
        "after_restart_before_replay": after_restart,
        "after_replay": after_replay,
        "consumer_process_before": service_before,
        "consumer_process_after": service_after,
        "consumer_unique_effects": len(after_replay["effects"]),
        "receipts": receipts,
    }


checked("IDEM04-EVENTS-RECOVERY", [3, 6, 7, 9], events)
(OUT / "recovery.json").write_text(json.dumps({"cases": CASES}, indent=2) + "\n")
