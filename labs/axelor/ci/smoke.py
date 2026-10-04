#!/usr/bin/env python3
"""Exercise the real authenticated API without writing business data."""
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def smoke(base_url, output, timeout):
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def request(path, data=None):
        headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
        for cookie in cookies:
            if cookie.name == "CSRF-TOKEN":
                headers["X-CSRF-Token"] = cookie.value
        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode()
        with client.open(urllib.request.Request(base_url + path, data, headers), timeout=15) as response:
            body = response.read()
            return json.loads(body) if body else None

    started = time.monotonic()
    deadline = started + timeout
    last_error = "server not yet contacted"
    while time.monotonic() < deadline:
        try:
            info = request("/ws/public/app/info")
            assert isinstance(info.get("application"), dict)
            assert isinstance(info.get("authentication"), dict)
            break
        except (OSError, ValueError, AssertionError) as error:
            last_error = f"{type(error).__name__}: {error}"
            time.sleep(3)
    else:
        raise RuntimeError(f"Application readiness failed: {last_error}")

    # The pinned upstream initializer creates this synthetic administrator in
    # an empty database. It is reachable only inside the disposable network.
    callback = urllib.parse.urlsplit(info["authentication"]["callbackUrl"])
    context = urllib.parse.urlsplit(base_url).path
    assert callback.path.startswith(context + "/callback"), callback.path
    login_path = callback.path[len(context):] + "?client_name=AxelorFormClient"
    request(login_path, {"username": "admin", "password": "admin"})
    info = request("/ws/public/app/info")
    assert info["user"]["login"] == "admin"
    assert info["application"]["aopVersion"] == "8.2.3", info["application"]
    modules = request("/ws/rest/com.axelor.meta.db.MetaModule?limit=200")
    assert modules["status"] == 0, modules
    found = {row["name"]: row for row in modules["data"]}
    assert found["cencomun-baseline"]["moduleVersion"] == "0.1.0", found.get("cencomun-baseline")
    assert found["axelor-base"]["moduleVersion"] == "9.1.8", found.get("axelor-base")
    result = {
        "status": "passed", "authenticated": True, "aop": "8.2.3",
        "aos": "9.1.8", "cencomun": "0.1.0", "module_count": len(found),
        "seconds": round(time.monotonic() - started, 2),
        "checks": ["public application API", "framework login", "authenticated identity",
                   "PostgreSQL-backed module REST read", "Cencomun and AOS versions"],
    }
    Path(output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    smoke(sys.argv[1], sys.argv[2], int(sys.argv[3]))
