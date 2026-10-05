"""Synthetic durable event consumer with unique event IDs and failure injection."""

import json, sqlite3, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/workspace/.local/frappe-integral")
DB = ROOT / "core-consumer.sqlite"
with sqlite3.connect(DB) as c:
    c.execute(
        "CREATE TABLE IF NOT EXISTS receipts(event_id TEXT PRIMARY KEY,payload TEXT NOT NULL,deliveries INTEGER NOT NULL)"
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if (ROOT / "core-consumer-fail").exists():
            self.send_response(503)
            self.end_headers()
            return
        with sqlite3.connect(DB) as c:
            c.execute(
                "INSERT INTO receipts VALUES(?,?,1) ON CONFLICT(event_id) DO UPDATE SET deliveries=deliveries+1",
                (data["event_id"], json.dumps(data)),
            )
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"accepted":true}')


if __name__ == "__main__":
    ThreadingHTTPServer(
        ("127.0.0.1", int(os.environ.get("CCM_CONSUMER_PORT", "8091"))), Handler
    ).serve_forever()
