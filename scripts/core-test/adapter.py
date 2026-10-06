"""Loopback HTTP adapter: six routes, auth forwarding, no ERP DB dependencies."""

import json, os, time, urllib.parse, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTES = {
    "/products/search": "searchProducts",
    "/purchases/drafts": "createPurchaseDraft",
    "/cash/status": "getCashStatus",
    "/cashea/orders": "createCasheaOrder",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def dispatch(self):
        route = urllib.parse.urlsplit(self.path)
        operation = ROUTES.get(route.path)
        parts = route.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "inventory":
            operation = "getInventory"
        if len(parts) == 3 and parts[0] == "customers" and parts[2] == "balance":
            operation = "getCustomerBalance"
        if not operation:
            return self.reply(404, {"code": "404", "message": "Unknown route"})
        auth = self.headers.get("Authorization")
        if not auth:
            return self.reply(
                401,
                {
                    "code": "401",
                    "message": "Authentication required",
                    "correlation_id": "anonymous",
                },
            )
        try:
            if self.command == "POST":
                payload = json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    or "{}"
                )
            else:
                payload = {
                    k: v[0] for k, v in urllib.parse.parse_qs(route.query).items()
                }
            if operation == "getInventory":
                payload["product_id"] = urllib.parse.unquote(parts[1])
            if operation == "getCustomerBalance":
                payload["customer_id"] = urllib.parse.unquote(parts[1])
            data = json.dumps(
                {
                    "operation": operation,
                    "payload": payload,
                    "key": self.headers.get("Idempotency-Key"),
                }
            ).encode()
            req = urllib.request.Request(
                os.environ.get("CCM_FRAPPE_URL", "http://127.0.0.1:8000")
                + "/api/method/cencomun_erp.core.api.execute",
                data=data,
                headers={
                    "Host": os.environ.get("CCM_CORE_SITE", "ccm-core.test"),
                    "Authorization": auth,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(req, timeout=120) as response:
                    result = json.load(response).get("message", {})
            except urllib.error.HTTPError as exc:
                return self.reply(
                    401
                    if exc.code == 401
                    else 403
                    if exc.code == 403
                    else 422
                    if exc.code in [400, 417]
                    else 500,
                    {
                        "code": str(exc.code),
                        "message": "ERP authentication or request rejected",
                        "correlation_id": "backend",
                    },
                )
            if not result.get("ok"):
                return self.reply(
                    result.get("status", 500),
                    result.get("error", {"code": "500", "message": "ERP unavailable"}),
                )
            if (
                os.environ.get("CCM_ENABLE_FAULTS") == "1"
                and self.headers.get("X-CCM-Lab-Lose-Response") == "once"
                and payload.get("id") == "IDEM-LOST"
                and result.get("ok")
            ):
                os._exit(73)
            self.reply(
                result["status"],
                {
                    **result["result"],
                    "_meta": {
                        "correlation_id": result["correlation_id"],
                        "server_ms": result["server_ms"],
                        **{
                            k: result[k]
                            for k in ["query_count", "db_ms"]
                            if k in result
                        },
                    },
                },
            )
        except (ValueError, KeyError, TypeError):
            self.reply(
                422,
                {
                    "code": "422",
                    "message": "Invalid request",
                    "correlation_id": "adapter",
                },
            )
        except Exception:
            self.reply(
                503,
                {
                    "code": "503",
                    "message": "ERP unavailable",
                    "correlation_id": "adapter",
                },
            )

    do_GET = dispatch
    do_POST = dispatch


if __name__ == "__main__":
    ThreadingHTTPServer(
        ("127.0.0.1", int(os.environ.get("CCM_ADAPTER_PORT", "8090"))), Handler
    ).serve_forever()
