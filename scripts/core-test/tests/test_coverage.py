"""Regression: absent/old evidence cannot keep a mandatory criterion approved."""

import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coverage_rules import apply_contract, criterion_status, archive_evidence


class MandatoryCoverageTests(unittest.TestCase):
    contract = {"requirements": [{"case": "AUDIT", "source": "audit",
                                  "criteria": [3, 6], "minimum_revision": 2}]}

    def test_absent_case_is_unrun_and_keeps_required_criteria(self):
        cases, gaps = apply_contract([], self.contract)
        self.assertEqual(criterion_status(cases), "UNRUN")
        self.assertEqual(cases[0]["criteria"], [3, 6])
        self.assertEqual(len(gaps), 1)

    def test_old_pass_does_not_prove_corrected_assertions(self):
        cases, gaps = apply_contract([{"case": "AUDIT", "status": "PASS"}], self.contract)
        self.assertEqual(criterion_status(cases), "UNRUN")
        self.assertEqual(cases[0]["prior_observation_status"], "PASS")
        self.assertTrue(gaps)

    def test_current_pass_approves_and_failure_takes_priority(self):
        cases, gaps = apply_contract([{"case": "AUDIT", "status": "PASS", "coverage_revision": 2}], self.contract)
        self.assertEqual(criterion_status(cases), "PASS")
        self.assertFalse(gaps)
        self.assertEqual(criterion_status(cases + [{"status": "FAIL"}]), "FAIL")

    def test_old_failure_is_preserved_while_coverage_remains_missing(self):
        cases, gaps = apply_contract([{"case": "AUDIT", "status": "FAIL"}], self.contract)
        self.assertEqual(criterion_status(cases), "FAIL")
        self.assertTrue(gaps)

    def test_blocked_never_counts_as_approved(self):
        self.assertEqual(criterion_status([{"status": "BLOCKED"}, {"status": "PASS"}]), "BLOCKED")

    def test_new_run_preserves_bytes_and_cannot_reuse_stale_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            data = b'{"cases":[{"status":"PASS"}]}\r\n'
            (out / "business.json").write_bytes(data)
            archive = out / "runs" / "prior"
            archive_evidence(out, archive)
            self.assertEqual((archive / "business.json").read_bytes(), data)
            self.assertFalse((out / "business.json").exists())
            self.assertEqual(criterion_status([]), "UNRUN")

    def test_archive_failure_preserves_original_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "business.json").write_bytes(b"original")
            with patch.object(Path, "write_bytes", side_effect=OSError("synthetic disk failure")):
                with self.assertRaises(OSError):
                    archive_evidence(out, out / "runs" / "prior")
            self.assertEqual((out / "business.json").read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
