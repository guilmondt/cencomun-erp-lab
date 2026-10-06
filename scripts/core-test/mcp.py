"""MCP stdio JSON-RPC service. ONLY the six adapter routes, no DB/ERP imports."""

import json, os, sys, urllib.request, urllib.error, urllib.parse

TOOLS = {
    "searchProducts": ("GET", "/products/search"),
    "getInventory": ("GET", "/inventory/{product_id}"),
    "getCustomerBalance": ("GET", "/customers/{customer_id}/balance"),
    "createPurchaseDraft": ("POST", "/purchases/drafts"),
    "getCashStatus": ("GET", "/cash/status"),
    "createCasheaOrder": ("POST", "/cashea/orders"),
}


def call(name, args):
    method, path = TOOLS[name]
    payload = dict(args)
    key = payload.pop("idempotency_key", None)
    for k in ("product_id", "customer_id"):
        if "{" + k + "}" in path:
            path = path.replace(
                "{" + k + "}", urllib.parse.quote(str(payload.pop(k)), safe="")
            )
    headers = {
        "Authorization": os.environ["CCM_MCP_AUTH"],
        "Content-Type": "application/json",
    }
    if key:
        headers["Idempotency-Key"] = key
    if method == "GET":
        path += "?" + urllib.parse.urlencode(payload)
        data = None
    else:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(
        os.environ.get("CCM_ADAPTER_URL", "http://127.0.0.1:8090") + path,
        headers=headers,
        data=data,
        method=method,
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=120) as r:
            body = json.load(r)
            status = r.status
    except urllib.error.HTTPError as e:
        body = json.load(e)
        status = e.code
    return {
        "content": [
            {"type": "text", "text": json.dumps({"status": status, "result": body})}
        ],
        "isError": status >= 400,
    }


for line in sys.stdin:
    try:
        q = json.loads(line)
        method = q["method"]
        rid = q.get("id")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ccm-core-lab", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": k,
                        "description": "LAB-only " + k + " via authenticated adapter",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "company_id": {"type": "string"},
                                "idempotency_key": {"type": "string"},
                            },
                            "required": ["company_id"],
                            "additionalProperties": True,
                        },
                    }
                    for k in TOOLS
                ]
            }
        elif method == "tools/call":
            result = call(q["params"]["name"], q["params"]["arguments"])
        else:
            raise KeyError(method)
        print(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}), flush=True)
    except Exception as e:
        print(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": q.get("id"),
                    "error": {
                        "code": -32602,
                        "message": "Invalid MCP method/tool/arguments",
                    },
                }
            ),
            flush=True,
        )
