"""Read-only authenticated startup probe; never print credentials or tracebacks."""

import json
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("/workspace/.local/frappe-integral")


def main():
    private = json.loads((ROOT / "core-private.json").read_text())
    actor = private["users"]["reader"]
    headers = {"Authorization": "token " + actor["api_key"] + ":" + actor["api_secret"]}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(base, path, native=False):
        request = urllib.request.Request(
            base + path,
            headers={**headers, **({"Host": "ccm-core.test"} if native else {})},
        )
        with opener.open(request, timeout=30) as response:
            assert response.status == 200
            return json.load(response)

    mapping = json.loads((REPO / "reports/evidence/frappe-core/http-mapping.json").read_text())
    config = json.loads((ROOT / "bench/sites/ccm-core.test/site_config.json").read_text())
    assert config.get("ccm_lab_enabled") == 1
    assert config.get("ccm_measure_queries", 0) == 0
    expected = json.loads((REPO / "fixtures/ccm-core-v1/products.json").read_text())[0]
    query = urllib.parse.urlencode({"company_id": mapping["company_id"], "q": expected["id"]})
    found = get("http://127.0.0.1:8090", "/products/search?" + query)["items"]
    found = [row for row in found if row["id"] == expected["id"]]
    assert len(found) == 1
    assert found[0]["price"] == expected["price"]
    native = get("http://127.0.0.1:8000", "/api/resource/Item/P001", True)["data"]
    assert native["ccm_id"] == found[0]["id"]
    assert Decimal(str(native["cashea_price"])) == Decimal(found[0]["price"])
    query = urllib.parse.urlencode({"company_id": mapping["company_id"], "warehouse": mapping["warehouse"]})
    stock = get("http://127.0.0.1:8090", "/inventory/P001?" + query)
    query = urllib.parse.urlencode({
        "filters": json.dumps({"item_code": "P001", "warehouse": mapping["warehouse"]}),
        "fields": json.dumps(["actual_qty"]),
    })
    bins = get("http://127.0.0.1:8000", "/api/resource/Bin?" + query, True)["data"]
    assert len(bins) == 1 and Decimal(stock["on_hand"]) == Decimal(str(bins[0]["actual_qty"]))
    print("PASS Core readiness: LAB flag active, metrics off, authenticated product/price/stock match native records.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL Core readiness:", type(error).__name__, "— follow scripts/core-test/README.md startup diagnosis.")
        raise SystemExit(1) from None
