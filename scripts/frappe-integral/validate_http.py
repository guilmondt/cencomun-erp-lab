"""Real HTTP assertions for the synthetic site, with secret-free evidence."""

import argparse
import json
import time
import uuid
from pathlib import Path

import requests

ROOT = Path("/workspace/.local/frappe-integral")
BASE = "http://127.0.0.1:8080"
SITE = "ccm-frappe.test"
PRIVATE = json.loads((ROOT / "secrets.json").read_text())
RESULTS = []


def client(token=False):
    session = requests.Session()
    session.trust_env = False  # Local requests must remain local.
    session.headers["Host"] = SITE
    if token:
        session.headers["Authorization"] = f"token {PRIVATE['api_key']}:{PRIVATE['api_secret']}"
    return session


def check(name, function):
    started = time.perf_counter()
    try:
        evidence = function()
        RESULTS.append({"check": name, "status": "passed", "seconds": round(time.perf_counter() - started, 4),
                        **(evidence or {})})
        print(f"PASS {name}")
    except Exception as error:
        # Do not serialize the exception/request: they can contain authentication headers.
        RESULTS.append({"check": name, "status": "failed", "exception_type": type(error).__name__})
        print(f"FAIL {name}: {type(error).__name__}")
        raise


def json_request(session, method, path, expected=200, **kwargs):
    response = session.request(method, BASE + path, timeout=30, **kwargs)
    assert response.status_code == expected, f"Unexpected HTTP status {response.status_code}"
    return response.json()


def denied(session, path):
    response = session.get(BASE + path, timeout=30)
    assert response.status_code in (401, 403), f"Expected denied request, got {response.status_code}"
    return {"http_status": response.status_code}


def login(session, password):
    response = json_request(session, "POST", "/api/method/login",
                            data={"usr": PRIVATE["validation_email"], "pwd": password})
    assert response["message"] == "Logged In"
    assert session.cookies.get("sid")


def run(phase):
    anonymous, cookie, token = client(), client(), client(True)
    marker_file = ROOT / "persistence-marker.json"

    def health():
        assert json_request(anonymous, "GET", "/api/method/ping")["message"] == "pong"
        return {"http_status": 200, "response": "pong"}

    check("public_api_health", health)

    def login_page():
        response = anonymous.get(BASE + "/login", timeout=30)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("Content-Type", "")
        assert "Login" in response.text
        return {"http_status": 200, "html_verified": True}

    check("login_page_served", login_page)

    def built_asset():
        assets = json.loads((ROOT / "bench/sites/assets/assets.json").read_text())
        response = anonymous.get(BASE + assets["desk.bundle.js"], timeout=30)
        assert response.status_code == 200
        assert "javascript" in response.headers.get("Content-Type", "")
        assert len(response.content) > 1000
        return {"http_status": 200, "bytes": len(response.content), "manifest_asset_verified": True}

    check("built_desk_asset_served", built_asset)
    check("anonymous_identity_denied", lambda: denied(anonymous, "/api/method/frappe.auth.get_logged_user"))
    check("password_login", lambda: login(cookie, PRIVATE["user_password"]))

    def identity(session):
        response = json_request(session, "GET", "/api/method/frappe.auth.get_logged_user")
        assert response["message"] == PRIVATE["validation_email"]
        return {"http_status": 200, "identity": "validation@example.invalid"}

    check("session_identity", lambda: identity(cookie))
    check("token_identity", lambda: identity(token))

    def invalid_token():
        invalid = client()
        invalid.headers["Authorization"] = "token deliberately-invalid:deliberately-invalid"
        return denied(invalid, "/api/method/frappe.auth.get_logged_user")

    check("invalid_token_denied", invalid_token)

    if phase == "before":
        title = "CCM synthetic validation " + uuid.uuid4().hex
        content = "Synthetic integration marker created through the standard Frappe REST API."

        def create_note():
            response = json_request(token, "POST", "/api/resource/Note",
                                    json={"title": title, "content": content, "public": 0})
            note = response["data"]
            assert note["doctype"] == "Note" and note["title"] == title
            marker_file.write_text(json.dumps({"name": note["name"], "title": title, "content": content}))
            return {"http_status": 200, "doctype": "Note", "synthetic": True}

        check("api_document_create", create_note)
    marker = json.loads(marker_file.read_text())
    path = "/api/resource/Note/" + requests.utils.quote(marker["name"], safe="")

    def read_note():
        note = json_request(token, "GET", path)["data"]
        assert note["title"] == marker["title"] and note["content"] == marker["content"]
        return {"http_status": 200, "doctype": "Note", "content_verified": True}

    check("api_document_read" if phase == "before" else "document_survives_restart", read_note)
    check("anonymous_private_document_denied", lambda: denied(anonymous, path))

    if phase == "before":
        def update_note():
            marker["content"] = "Synthetic integration marker updated before a complete service restart."
            note = json_request(token, "PUT", path, json={"content": marker["content"]})["data"]
            assert note["content"] == marker["content"]
            marker_file.write_text(json.dumps(marker))
            return {"http_status": 200, "content_verified": True}

        check("api_document_update", update_note)
        check("updated_document_readback", read_note)

    previous_sid = cookie.cookies.get("sid")

    def logout():
        response = cookie.post(BASE + "/api/method/logout", timeout=30)
        assert response.status_code == 200
        assert cookie.cookies.get("sid") != previous_sid
        return {"http_status": 200, "client_session_cleared": True}

    check("logout", logout)
    check("logged_out_session_denied", lambda: denied(cookie, "/api/method/frappe.auth.get_logged_user"))

    def replay_revoked_session():
        replay = client()
        replay.headers["Cookie"] = "sid=" + previous_sid
        return denied(replay, "/api/method/frappe.auth.get_logged_user")

    check("revoked_session_replay_denied", replay_revoked_session)

    def wrong_password():
        response = client().post(BASE + "/api/method/login",
                                 data={"usr": PRIVATE["validation_email"], "pwd": "deliberately-invalid"}, timeout=30)
        assert response.status_code in (401, 403)
        return {"http_status": response.status_code}

    check("incorrect_password_denied", wrong_password)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["before", "after"])
    args = parser.parse_args()
    if args.phase == "before":
        (ROOT / "validation-run-id").write_text(uuid.uuid4().hex)
    succeeded = False
    try:
        run(args.phase)
        succeeded = True
    finally:
        (ROOT / f"http-{args.phase}.json").write_text(json.dumps({
            "run_id": (ROOT / "validation-run-id").read_text(),
            "phase": args.phase, "site": SITE, "all_executed_checks_passed": succeeded,
            "checks": RESULTS,
        }, indent=2))
