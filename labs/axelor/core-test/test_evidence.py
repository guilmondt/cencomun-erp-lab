"""Regression tests for coverage integrity and native accounting evidence rejection."""
import unittest
from pathlib import Path
from run import assert_native_economics, criteria_for, rows_for, verify_bundle, verified_build_status, run_product_cases
from finalize import BASELINE, baseline_pin_blob

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures/ccm-core-v1"


class EvidenceTests(unittest.TestCase):
    def test_legacy_preparation_failure_retains_explicit_reference_evidence(self):
        import json
        import tempfile
        from extract_log_evidence import extract
        from run import REFERENCE
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            failure = {"case": "CO00", "status": "FAIL", "error":
                "('Fixture preparation failed', {'reference': '" + REFERENCE + "'})"}
            missing_reference = {"case": "TAX01-W", "status": "PASS"}
            log.write_text("\n".join("timestamp ##[notice]" + json.dumps(r)
                for r in [failure, missing_reference]) + "\n")
            result = extract(log, Path(tmp) / "results", "synthetic", "1" * 40, FIXTURES)
            self.assertEqual({"FAIL": 1, "UNRUN": 33}, result["counts"])
            saved = json.loads((Path(tmp) / "results/CO00-gate.json").read_text())
            self.assertIn("native preparation error", saved["reference_evidence"])

    def test_log_extraction_does_not_infer_missing_native_or_build_proof(self):
        import tempfile
        from extract_log_evidence import extract
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text('timestamp ##[notice]{"status":"PASS","message":"build successful"}\n'
                           'timestamp ##[notice]{"case":"CO00","status":"PASS"\n')
            result = extract(log, Path(tmp) / "results", "synthetic", "1" * 40, FIXTURES)
            self.assertEqual({"UNRUN": 34}, result["counts"])
            self.assertEqual("UNRUN", next(r["status"] for r in result["criteria"] if r["criterion"] == 2))

    def test_shallow_checkout_requires_explicit_base_fetch(self):
        import subprocess
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            # No mount ownership, caller branch, credentials or external transport dependencies.
            source = Path(tmp) / "source"
            source.mkdir()
            def command(*args):
                return subprocess.check_output(["git", "-C", str(source), *args], stderr=subprocess.PIPE)
            command("init", "--quiet", "--initial-branch=history-regression")
            command("config", "user.name", "Synthetic History Test")
            command("config", "user.email", "history@example.invalid")
            pin_bytes = (FIXTURES.parent.parent / "versions.lock").read_bytes()
            (source / "versions.lock").write_bytes(pin_bytes)
            command("add", "versions.lock")
            command("commit", "--quiet", "-m", "fixed synthetic baseline")
            base = command("rev-parse", "HEAD").decode().strip()
            (source / "second.txt").write_text("shallow tip\n")
            command("add", "second.txt")
            command("commit", "--quiet", "-m", "synthetic tip")
            clone = Path(tmp) / "shallow"
            subprocess.run(["git", "clone", "--quiet", "--depth=1", "--single-branch",
                            source.as_uri(), str(clone)], check=True)
            self.assertEqual(b"true\n", subprocess.check_output(["git", "-C", str(clone), "rev-parse", "--is-shallow-repository"]))
            with patch("finalize.BASELINE", base):
                with self.assertRaises(subprocess.CalledProcessError):
                    baseline_pin_blob(clone)
                subprocess.run(["git", "-C", str(clone), "fetch", "--quiet", "--no-tags", "--depth=1", "origin", base], check=True)
                self.assertEqual(pin_bytes, baseline_pin_blob(clone))
                (clone / "versions.lock").write_text("altered pins\n")
                self.assertNotEqual((clone / "versions.lock").read_bytes(), baseline_pin_blob(clone))

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

    def test_partial_admin_pass_cannot_pass_a_complete_group_criterion(self):
        rows = rows_for(verify_bundle(FIXTURES))
        for row in rows:
            row.update(status="PASS", observed_revision=row["minimum_revision"], evidence="actual-test.json", complete=True)
        next(r for r in rows if r["case"] == "CO00-NATIVE")["complete"] = False
        criteria = {r["criterion"]: r["status"] for r in criteria_for(rows)}
        self.assertEqual("UNRUN", criteria[5])

    def test_product_save_success_without_durable_warranty_change_fails(self):
        import contextlib
        import io
        import tempfile
        from unittest.mock import Mock, patch
        operator = Mock()
        operator.samples = []
        # Simulate a save success whose separate persisted read stayed unchanged.
        operator.request.side_effect = lambda path, data: ({"status": 0, "data": [{"id": 1, "version": 0,
            "warrantyQuantity": 12, "warrantyUnit": "MONTH"}]} if path.endswith("/fetch") else {"status": 0})
        admin = Mock()
        admin.action.return_value = {"company_id": 1, "profiles": [
            {"id": i, "product_id": i, "product_code": f"P{i:03}"} for i in (1, 2, 3)]}
        row = next(r for r in rows_for(verify_bundle(FIXTURES)) if r["case"] == "PROD01-04")
        with tempfile.TemporaryDirectory() as tmp, patch("run.NativeClient", return_value=operator), contextlib.redirect_stdout(io.StringIO()):
            result = run_product_cases(admin, "unused", FIXTURES, Path(tmp), row)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual("FAIL", row["status"])
        self.assertFalse(row["complete"])

    def test_passing_gate_needs_physical_stock_not_only_calculated_money(self):
        expected = {"stock": [3, 4, 5], "stock_value": "430.00"}
        native = {"stock": [{"code": "P001", "current_qty": "5", "avg_price": "30"},
                            {"code": "P002", "current_qty": "5", "avg_price": "10"},
                            {"code": "P003", "current_qty": "5", "avg_price": "60"}]}
        with self.assertRaises(AssertionError):
            assert_native_economics(native, expected)

    def test_invoice_total_does_not_hide_wrong_native_line_tax_allocation(self):
        import json
        expected = json.loads((FIXTURES / "oracle.json").read_bytes())["TAX01-W"]
        native = {"stock": [{"code": code, "current_qty": qty, "avg_price": price} for code, qty, price in
                  [("P001", "3", "30"), ("P002", "4", "10"), ("P003", "5", "60")]],
                  "sale_order_ids": [1], "deliveries": [{"status": 3}],
                  "invoices": [{"statusSelect": 3, "exTaxTotal": "125.00", "taxTotal": "12.50",
                     "inTaxTotal": "137.50", "amountRemaining": "0.00",
                     "lines": [{"code": "P001", "qty": "2", "ex_tax_total": "100.00", "in_tax_total": "119.00"},
                               {"code": "P002", "qty": "1", "ex_tax_total": "25.00", "in_tax_total": "18.50"}]}]}
        with self.assertRaisesRegex(AssertionError, "native invoice product line"):
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
