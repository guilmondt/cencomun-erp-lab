"""Regression tests for coverage integrity and native accounting evidence rejection."""
import unittest
from pathlib import Path
from run import assert_native_economics, criteria_for, rows_for, verify_bundle, verified_build_status

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures/ccm-core-v1"


class EvidenceTests(unittest.TestCase):
    def test_obsolete_revision_cannot_pass(self):
        rows = rows_for(verify_bundle(FIXTURES))
        for row in rows:
            row.update(status="PASS", observed_revision=row["minimum_revision"])
        next(r for r in rows if r["case"] == "MCP01-06-STDIO")["observed_revision"] = 1
        criteria = {r["criterion"]: r["status"] for r in criteria_for(rows)}
        self.assertEqual("UNRUN", criteria[10])
        self.assertEqual("BLOCKED", criteria[13])

    def test_unit_success_cannot_fill_unrun_native_groups(self):
        rows = rows_for(verify_bundle(FIXTURES))
        self.assertEqual(34, len(rows))
        self.assertTrue(all(r["status"] == "UNRUN" for r in rows))
        statuses = {r["criterion"]: r["status"] for r in criteria_for(rows)}
        self.assertEqual("UNRUN", statuses[2])
        self.assertEqual("UNRUN", statuses[5])

    def test_passing_gate_needs_physical_stock_not_only_calculated_money(self):
        expected = {"stock": [3, 4, 5], "stock_value": "430.00"}
        native = {"stock": [{"code": "P001", "current_qty": "5", "avg_price": "30"},
                            {"code": "P002", "current_qty": "5", "avg_price": "10"},
                            {"code": "P003", "current_qty": "5", "avg_price": "60"}]}
        with self.assertRaises(AssertionError):
            assert_native_economics(native, expected)

    def test_non_native_fixture_bytes_are_rejected(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fixtures"
            shutil.copytree(FIXTURES, target)
            path = target / "bank.csv"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(AssertionError):
                verify_bundle(target)

    def test_build_pass_label_without_upstream_evidence_is_unrun(self):
        self.assertEqual("UNRUN", verified_build_status({"status": "PASS"}))

    def test_any_upstream_difference_fails_even_when_all_unit_suites_pass(self):
        proof = {"lab_commit": "1" * 40, "host_commit": "1119727a3b53c8387b7fab535e184c25154d2eac",
                 "aos_commit": "0c70d561b19fc454eba9fdd41689258846626d75", "upstream_diff_exit_codes": {"host": 0, "aos": 1},
                 "baseline_pin_blob_sha256": "2" * 64, "expected_baseline_pin_blob_sha256": "2" * 64,
                 "suites": {name: {"tests": count, "failures": 0, "errors": 0, "skipped": 0}
                            for name, count in {"CencomunModuleTest": 2, "MoneyPolicyTest": 7, "TestTaxNumberHelper": 16}.items()},
                 "war_sha256": "3" * 64}
        self.assertEqual("FAIL", verified_build_status(proof))


if __name__ == "__main__":
    unittest.main()
