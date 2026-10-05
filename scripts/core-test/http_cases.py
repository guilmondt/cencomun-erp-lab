"""Real HTTP/token/MCP stdio/concurrent native-effect acceptance tests."""

import json, os, subprocess, sys, time, urllib.request, urllib.error, urllib.parse, concurrent.futures
from pathlib import Path

REPO = Path("/workspace/cencomun-erp-lab")
ROOT = Path("/workspace/.local/frappe-integral")
OUT = REPO / "reports/evidence/frappe-core"
PRIVATE = json.loads((ROOT / "core-private.json").read_text())
MAPPING = json.loads((OUT / "http-mapping.json").read_text())
COMPANY = "CCM-LAB-001"
CASES = []
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def auth(actor):
    u = PRIVATE["users"][actor]
    return "token " + u["api_key"] + ":" + u["api_secret"]


def req(path, p=None, actor="reader", key=None, native=False, method=None):
    headers = {"Content-Type": "application/json"}
    if actor:
        headers["Authorization"] = auth(actor)
    if key:
        headers["Idempotency-Key"] = key
    if native:
        headers["Host"] = "ccm-core.test"
    if p is not None:
        raw = json.dumps(p).encode()
        method = method or "POST"
    else:
        raw = None
        method = method or "GET"
    path = urllib.parse.quote(path, safe="/?=&%:+,")
    request = urllib.request.Request(
        ("http://127.0.0.1:8000" if native else "http://127.0.0.1:8090") + path,
        data=raw,
        headers=headers,
        method=method,
    )
    try:
        with OPENER.open(request, timeout=120) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as e:
        # Never publish framework tracebacks/headers; only its neutral body or sanitized status.
        body = json.load(e)
        if native:
            body = {
                "native_error": body.get("exc_type", "HTTPError"),
                "http_status": e.code,
            }
        return e.code, body


def ncall(op, p, actor, key):
    status, body = req(
        "/api/method/cencomun_erp.core.api.execute",
        {"operation": op, "payload": p, "key": key},
        actor,
        native=True,
    )
    if status == 200:
        status = body["message"]["status"]
        body = body["message"].get("result") or body["message"].get("error")
    return status, body


def p(value):
    return {"company_id": COMPANY, **value}


def expect(actual, expected):
    if actual != expected:
        raise AssertionError({"expected": expected, "actual": actual})
    return actual


def check(case, criteria, fn):
    selected = os.environ.get("CCM_HTTP_CASES", "")
    if selected and case not in selected.split(","):
        return
    t = time.monotonic()
    try:
        actual = fn()
        CASES.append(
            {
                "case": case,
                "criteria": criteria,
                "status": "PASS",
                "actual": actual,
                "seconds": round(time.monotonic() - t, 4),
            }
        )
        print(case, "PASS", flush=True)
    except Exception as e:
        CASES.append(
            {
                "case": case,
                "criteria": criteria,
                "status": "FAIL",
                "error": type(e).__name__ + ": " + str(e),
                "seconds": round(time.monotonic() - t, 4),
            }
        )
        print(case, "FAIL", str(e)[:200], flush=True)


def six_routes():
    reads = {
        "/products/search?" + urllib.parse.urlencode(p({"q": "P001"})): ("items", None),
        "/inventory/P001?"
        + urllib.parse.urlencode(p({"warehouse": MAPPING["warehouse"]})): (
            "on_hand",
            "5",
        ),
        "/customers/C002/balance?" + urllib.parse.urlencode(p({})): (
            "balances",
            {"USD": "0.00"},
        ),
        "/cash/status?" + urllib.parse.urlencode(p({"id": "CS001"})): (
            "state",
            "CONFIRMED",
        ),
    }
    actual = []
    for path, (field, value) in reads.items():
        status, body = req(path)
        expect(status, 200)
        if value is not None:
            expect(body[field], value)
        else:
            expect([x["id"] for x in body[field]], ["P001"])
        actual.append({"route": path, "status": status, "result": body})
    status, po = req(
        "/purchases/drafts",
        p({"id": "API-PO", "amount": "199.99"}),
        "operator",
        "API-PO",
    )
    expect(status, 201)
    expect(po["state"], "Draft")
    base = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())[0]
    order = p({**base, "id": "API-CO", "warehouse": MAPPING["warehouse"]})
    status, co = req("/cashea/orders", order, "operator", "API-CO")
    expect(status, 201)
    expect(co["status"], "NEW")
    status, replay = req("/cashea/orders", order, "operator", "API-CO")
    expect(status, 200)
    expect(replay["replay"], True)
    expect(replay["id"], co["id"])
    altered = {**order, "financed_amount": "74.00"}
    expect(req("/cashea/orders", altered, "operator", "API-CO")[0], 409)
    return {
        "reads": actual,
        "purchase": po,
        "order": co,
        "replay": replay,
        "conflict": 409,
    }


check("API01-06-SIX-ROUTES", [3, 9], six_routes)


def concurrent_creation():
    base = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())[0]
    data = p(
        {
            **base,
            "id": os.environ.get("CCM_CREATE_ID", "IDEM-CREATE"),
            "warehouse": MAPPING["warehouse"],
        }
    )
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        responses = list(
            pool.map(
                lambda _: req("/cashea/orders", data, "operator", data["id"]), range(2)
            )
        )
    expect(sorted(r[0] for r in responses), [200, 201])
    expect(sorted(r[1]["replay"] for r in responses), [False, True])
    expect(req("/cashea/orders", data, "reader", data["id"])[0], 403)
    expect(req("/cashea/orders", data, "operator", data["id"] + "-DIFFERENT")[0], 409)
    return {
        "responses": responses,
        "replay_without_permissions": 403,
        "same_external_id_different_key": 409,
    }


check("IDEM01-02-CREATE-CONCURRENT", [3, 4, 9], concurrent_creation)


def permission_matrix():
    result = []
    expect(
        req("/products/search?" + urllib.parse.urlencode(p({"q": "P001"})), actor=None)[
            0
        ],
        401,
    )
    expect(
        req(
            "/products/search?" + urllib.parse.urlencode(p({"q": "P001"})),
            actor="other",
        )[0],
        403,
    )
    expect(
        req(
            "/products/search?"
            + urllib.parse.urlencode({"company_id": "OTHER-LAB", "q": "P001"})
        )[0],
        403,
    )
    for actor in ["reader", "buyer", "manager", "director", "simulator", "other"]:
        status, body = req(
            "/purchases/drafts",
            p({"id": "DENY-" + actor, "amount": "200.00"}),
            actor,
            "DENY-" + actor,
        )
        expect(status, 403)
        result.append({"actor": actor, "action": "draft", "code": status})
    base = json.loads((REPO / "fixtures/ccm-core-v1/orders.json").read_text())[0]
    invalid = p(
        {
            **base,
            "id": "API-BAD",
            "warehouse": MAPPING["warehouse"],
            "lines": [{"product_id": "P001", "qty": "0.5", "unit_price": "50.00"}],
        }
    )
    expect(req("/cashea/orders", invalid, "operator", "API-BAD")[0], 422)
    for actor, op, payload in [
        ("operator", "purchaseAction", p({"id": "PO01", "action": "Approve"})),
        ("director", "confirmClosing", p({"id": "CS001"})),
        (
            "director",
            "authorizeRate",
            p(
                {
                    "id": "DENY-RATE",
                    "date": "2026-10-04",
                    "rate": "40.00",
                    "reason": "Denied LAB test",
                }
            ),
        ),
        ("mcp", "transitionOrder", p({"id": "API-CO", "target": "APPROVED"})),
        (
            "simulator",
            "transitionOrder",
            p({"id": "TAX-CONC-S", "target": "FULFILLED"}),
        ),
        ("operator", "transitionOrder", p({"id": "API-CO", "target": "REVIEWED"})),
    ]:
        status, body = ncall(op, payload, actor, "DENY:" + actor + ":" + op)
        expect(status, 403)
        result.append({"actor": actor, "action": op, "code": status})
    # Native API permission/hook checks, not UI visibility.
    expect(req("/api/resource/Item/P001", {"ccm_company": ""}, "operator", native=True, method="PUT")[0], 403)
    expect(req("/api/resource/Item/P001", {"ccm_id": "DETACHED"}, "operator", native=True, method="PUT")[0], 403)

    for dt in ["Bin", "Contact"]:
        expect(
            req(
                "/api/method/frappe.client.get_list",
                {"doctype": dt, "fields": ["name"]},
                "other",
                native=True,
            )[1]["message"],
            [],
        )
    expect(req("/api/resource/Item/P001", actor="other", native=True)[0], 403)
    expect(
        req(
            "/api/method/frappe.client.get_list",
            {"doctype": "Item", "fields": ["name"]},
            "other",
            native=True,
        )[1]["message"],
        [],
    )
    expect(
        req(
            "/api/resource/Item/P001",
            {"cashea_price": 0},
            "reader",
            native=True,
            method="PUT",
        )[0],
        403,
    )
    expect(
        req(
            "/api/resource/Item/P001",
            {"cashea_price": 0},
            "operator",
            native=True,
            method="PUT",
        )[0],
        417,
    )
    native_doc = {
        "doctype": "Sales Invoice",
        "company": COMPANY,
        "customer": "Cliente ficticio Alfa",
        "currency": "USD",
        "items": [{"item_code": "P001", "qty": 1, "rate": 50}],
    }
    expect(
        req("/api/resource/Sales Invoice", native_doc, "operator", native=True)[0], 403
    )
    expect(
        req(
            "/api/method/erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
            {"dt": "Sales Invoice", "dn": MAPPING["invoice"]},
            "mcp",
            native=True,
        )[0],
        403,
    )
    expect(
        req("/api/resource/CCM Audit?limit_page_length=1", actor="reader", native=True)[
            0
        ],
        403,
    )
    return {
        "neutral_errors": [401, 403, 422, 409],
        "matrix": result,
        "native_read_write_denials": True,
    }


check("PERM-API-NATIVE", [3, 9], permission_matrix)


def closing_api():
    status, body = req(
        "/api/method/frappe.client.get_list",
        {
            "doctype": "CCM Cash Closing",
            "fields": ["name"],
            "filters": {"company": COMPANY, "external_id": "CS001"},
        },
        "manager",
        native=True,
    )
    expect(status, 200)
    name = body["message"][0]["name"]
    route = "/api/resource/CCM Cash Closing/" + name
    status, before = req(route, actor="manager", native=True)
    expect(status, 200)
    expect(
        req(
            route,
            {"note": "Attempt silent HTTP edit"},
            "manager",
            native=True,
            method="PUT",
        )[0],
        403,
    )
    expect(
        req(route, {"state": "DRAFT"}, "operator", native=True, method="PUT")[0], 403
    )
    status, after = req(route, actor="manager", native=True)
    expect(status, 200)
    fields = ["state", "snapshot", "note", "confirmed_by", "confirmed_at"]
    expect(
        {k: after["data"][k] for k in fields}, {k: before["data"][k] for k in fields}
    )
    return {
        "native_closing": name,
        "before": {k: before["data"][k] for k in fields},
        "after": {k: after["data"][k] for k in fields},
        "manager_edit": 403,
        "operator_edit": 403,
    }


check("CASH04-06-HTTP-IMMUTABLE", [3, 6, 9], closing_api)


def search():
    spec = json.loads((REPO / "fixtures/ccm-core-v1/scenarios.json").read_text())[
        "search"
    ]
    result = []
    for query, expected in spec["products"].items():
        status, body = req(
            "/products/search?" + urllib.parse.urlencode(p({"q": query}))
        )
        expect(status, 200)
        expect([r["id"] for r in body["items"]], expected)
        result.append({"q": query, "ids": expected})
    seen = []
    for page in [1, 2]:
        status, body = req(
            "/products/search?"
            + urllib.parse.urlencode(p({"q": "ficticio", "page": page, "page_size": 2}))
        )
        expect(status, 200)
        expect(body["total"], 3)
        seen.extend(r["id"] for r in body["items"])
    expect(seen, ["P001", "P002", "P003"])
    for field, q in [
        ("customer_name", "Cliente ficticio Alfa"),
        ("mobile_no", "+12025550101"),
    ]:
        status, body = req(
            "/api/method/frappe.client.get_list",
            {
                "doctype": "Customer",
                "fields": ["ccm_id"],
                "filters": {"ccm_company": COMPANY, field: q},
            },
            "reader",
            native=True,
        )
        expect(status, 200)
        expect(body["message"], [{"ccm_id": "C001"}])
        result.append({"native_field": field, "ids": ["C001"]})
    status, body = req(
        "/api/method/frappe.client.get_list",
        {
            "doctype": "Sales Invoice",
            "fields": ["name"],
            "filters": {"company": COMPANY, "po_no": "INV-CCM-001"},
        },
        "reader",
        native=True,
    )
    expect(status, 200)
    expect(body["message"], [{"name": MAPPING["invoice"]}])
    status, body = req(
        "/api/method/frappe.client.get_list",
        {
            "doctype": "Serial No",
            "fields": ["item_code"],
            "filters": {"company": COMPANY, "serial_no": "SER-P001-001"},
        },
        "reader",
        native=True,
    )
    expect(status, 200)
    expect(body["message"], [{"item_code": "P001"}])
    return {
        "queries": result,
        "complete_pages": seen,
        "invoice_reference": "INV-CCM-001",
        "native_invoice": MAPPING["invoice"],
        "serial": "SER-P001-001",
        "serial_inventory_tracking_tested": False,
    }


check("SEARCH01-04-NATIVE", [3, 12], search)


def concurrent_tax():
    outputs = []
    for identifier, wh in MAPPING["concurrent"].items():
        target = "SHIPPED" if identifier.endswith("W") else "FULFILLED"
        payload = p({"id": identifier, "target": target})
        key = identifier + ":PHYSICAL"
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            responses = list(
                pool.map(
                    lambda _: ncall("transitionOrder", payload, "operator", key),
                    range(2),
                )
            )
        expect([r[0] for r in responses], [200, 200])
        expect(sorted(r[1]["replay"] for r in responses), [False, True])
        conflict = ncall("transitionOrder", payload, "operator", key + ":distinct")
        expect(conflict[0], 409)
        settle = p({"id": identifier, "target": "SETTLED"})
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            paid = list(
                pool.map(
                    lambda _: ncall(
                        "transitionOrder", settle, "simulator", identifier + ":SETTLED"
                    ),
                    range(2),
                )
            )
        expect([r[0] for r in paid], [200, 200])
        expect(sorted(r[1]["replay"] for r in paid), [False, True])
        expect(
            req("/inventory/P001?" + urllib.parse.urlencode(p({"warehouse": wh})))[1][
                "on_hand"
            ],
            "3",
        )
        outputs.append(
            {
                "id": identifier,
                "physical": responses,
                "state_conflict": conflict,
                "settlement": paid,
            }
        )
    return outputs


check("TAX02-04-IDEM-CONCURRENT", [3, 4, 5, 9], concurrent_tax)


def bank_concurrent():
    csv = (REPO / "fixtures/ccm-core-v1/benchmark-bank.csv").read_text()
    payload = p({"id": "BANK-CONCURRENT", "account_id": "BANK-USD-001", "csv": csv})
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        r = list(
            pool.map(
                lambda _: ncall("importBank", payload, "operator", "BANK-CONCURRENT"),
                range(2),
            )
        )
    expect([a[0] for a in r], [200, 200])
    expect(sorted(a[1]["replay"] for a in r), [False, True])
    expect([a[1]["created"] for a in r], [1000, 1000])
    return {
        "responses": [
            {"status": a[0], "created": a[1]["created"], "replay": a[1]["replay"]}
            for a in r
        ],
        "expected_native_unique": 1000,
    }


check("BANK-CONCURRENT-1000", [8, 9], bank_concurrent)


class MCP:
    def __init__(self):
        environment = dict(os.environ)
        environment["CCM_MCP_AUTH"] = auth("mcp")
        self.process = subprocess.Popen(
            [sys.executable, str(REPO / "scripts/core-test/mcp.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        self.id = 0

    def call(self, method, params=None):
        self.id += 1
        self.process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": self.id,
                    "method": method,
                    **({"params": params} if params else {}),
                }
            )
            + "\n"
        )
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def stop(self):
        self.process.stdin.close()
        self.process.wait(timeout=5)


def mcp():
    process = MCP()
    result = []
    try:
        init = process.call(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ccm-lab-test", "version": "1"},
            },
        )
        expect(init["result"]["protocolVersion"], "2025-03-26")
        names = [r["name"] for r in process.call("tools/list")["result"]["tools"]]
        expect(
            set(names),
            {
                "searchProducts",
                "getInventory",
                "getCustomerBalance",
                "createPurchaseDraft",
                "getCashStatus",
                "createCasheaOrder",
            },
        )
        args = [
            ("searchProducts", p({"q": "P001"})),
            (
                "getInventory",
                p({"product_id": "P001", "warehouse": MAPPING["warehouse"]}),
            ),
            ("getCustomerBalance", p({"customer_id": "C002"})),
            ("getCashStatus", p({"id": "CS001"})),
            (
                "createPurchaseDraft",
                p({"id": "MCP-PO", "amount": "199.99", "idempotency_key": "MCP-PO"}),
            ),
            (
                "createCasheaOrder",
                p(
                    {
                        **json.loads(
                            (REPO / "fixtures/ccm-core-v1/orders.json").read_text()
                        )[0],
                        "id": "MCP-CO",
                        "warehouse": MAPPING["warehouse"],
                        "idempotency_key": "MCP-CO",
                    }
                ),
            ),
        ]
        for name, arg in args:
            answer = process.call("tools/call", {"name": name, "arguments": arg})[
                "result"
            ]
            body = json.loads(answer["content"][0]["text"])
            if answer["isError"]:
                raise AssertionError({"tool": name, "response": body})
            expect(
                body["status"],
                201
                if name.startswith("create") and not body["result"].get("replay")
                else 200,
            )
            result.append({"tool": name, **body})
        replay = process.call(
            "tools/call", {"name": "createCasheaOrder", "arguments": args[-1][1]}
        )["result"]
        expect(json.loads(replay["content"][0]["text"])["result"]["replay"], True)
        denied = process.call(
            "tools/call", {"name": "approvePurchase", "arguments": p({"id": "MCP-PO"})}
        )
        expect(denied["error"]["code"], -32602)
        status, _ = ncall(
            "purchaseAction",
            p({"id": "MCP-PO", "action": "Approve"}),
            "mcp",
            "MCP-deny",
        )
        expect(status, 403)
        return {
            "initialize": init,
            "tools": names,
            "operations": result,
            "replay": True,
            "approval_denied": True,
        }
    finally:
        process.stop()


check("MCP01-06-STDIO", [3, 9, 10], mcp)
if os.environ.get("CCM_HTTP_CASES") and (OUT / "http.json").exists():
    old = json.loads((OUT / "http.json").read_text())["cases"]
    updates = {c["case"]: c for c in CASES}
    CASES = [updates.pop(c["case"], c) for c in old] + list(updates.values())
(OUT / "http.json").write_text(
    json.dumps({"profile": "LAB-ONLY-v1", "cases": CASES}, indent=2) + "\n"
)
print(
    "HTTP cases",
    len(CASES),
    "PASS",
    sum(x["status"] == "PASS" for x in CASES),
    "FAIL",
    sum(x["status"] == "FAIL" for x in CASES),
    flush=True,
)
