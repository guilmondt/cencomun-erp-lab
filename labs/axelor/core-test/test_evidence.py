"""Regression tests for coverage integrity and native accounting evidence rejection."""
import unittest
from pathlib import Path
from run import assert_native_economics, assert_native_bank_book, assert_native_fx, assert_native_fx_conversions, criteria_for, rows_for, verify_bundle, verified_build_status, run_product_cases
from finalize import BASELINE, baseline_pin_blob

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures/ccm-core-v1"


class EvidenceTests(unittest.TestCase):
    def test_focused_address_notice_cannot_approve_core_groups(self):
        import json
        import tempfile
        from extract_log_evidence import extract
        from run import REFERENCE
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'run.log'
            notice = {'scope': 'native address fixture prerequisite, not a Core group',
                'reference': REFERENCE, 'lab_commit': '1' * 40, 'status': 'PASS'}
            log.write_text('timestamp ##[notice]' + json.dumps(notice) + '\n')
            result = extract(log, Path(tmp) / 'results', 'synthetic', '1' * 40, FIXTURES)
            self.assertEqual({'UNRUN': 34}, result['counts'])
            self.assertTrue((Path(tmp) / 'results/address-preflight.json').is_file())

    def test_address_preflight_rejects_null_or_incomplete_required_metadata(self):
        import importlib.util
        import copy
        path = Path(__file__).resolve().parents[1] / 'ci/address-preflight.py'
        spec = importlib.util.spec_from_file_location('address_preflight', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        prepared = {'address_id': 1, 'repository': 'com.axelor.apps.base.db.repo.AddressBaseRepository'}
        committed = {'address_id': 1, 'template_id': 2, 'read_boundary': 'separate-http-after-address-commit',
            'street': '1 Synthetic LAB Street', 'city': 'Synthetic LAB City', 'zip': '00000',
            'formatted_full_name': 'Synthetic LAB preflight\n1 Synthetic LAB Street\nSynthetic LAB City 00000',
            'full_name': 'SYNTHETIC LAB PREFLIGHT 1 SYNTHETIC LAB STREET SYNTHETIC LAB CITY 00000',
            'lines': [{'id': i+1, 'field_id': i+100, 'field': field, 'model': 'com.axelor.apps.base.db.Address',
                'required': field in ('streetName', 'city', 'zip'), 'template_id': 2}
                for i, field in enumerate(('floor','streetName','postBox','city','zip'))]}
        module.assert_address(prepared, committed)
        for mutation in ('missing_collection', 'empty_collection', 'no_required_fields', 'missing_metadata', 'uncommitted_read'):
            value = copy.deepcopy(committed)
            if mutation == 'missing_collection': value['lines'] = None
            if mutation == 'empty_collection': value['lines'] = []
            if mutation == 'no_required_fields':
                for line in value['lines']: line['required'] = False
            if mutation == 'missing_metadata': value['lines'][1]['field_id'] = 0
            if mutation == 'uncommitted_read': value['read_boundary'] = 'inside-save-transaction'
            with self.subTest(mutation=mutation), self.assertRaises((AssertionError, TypeError)):
                module.assert_address(prepared, value)

    def test_native_fx_failure_does_not_skip_independent_payment_dates(self):
        import io
        import json
        import urllib.error
        from unittest.mock import Mock
        from run import run_fx_payment_cases
        items = json.loads((FIXTURES / "fx.json").read_bytes())["payments"]
        operator, admin = Mock(), Mock()
        state = {"company_id": 1, "company_code": "CCM-LAB-001", "invoices": [], "payments": []}
        admin.action.side_effect = lambda *args: json.loads(json.dumps(state))
        def post(path, item):
            if item["id"] == "FX01":
                raise urllib.error.HTTPError(path, 500, "Native failure", {}, io.BytesIO(b'Native invoice prerequisite missing'))
            identity = len(state["invoices"]) + 1
            state["invoices"].append({"id": identity})
            payment_ids = [identity * 10 + n for n in range(len(item["lines"]))]
            state["payments"].extend({"id": p} for p in payment_ids)
            return {"native_invoice_id": identity, "native_payment_ids": payment_ids}
        operator.request.side_effect = post
        evidence = {"steps": []}
        with self.assertRaisesRegex(RuntimeError, "FX01"):
            run_fx_payment_cases(operator, admin, items, lambda item: item, evidence)
        self.assertEqual(operator.request.call_count, 3)
        self.assertEqual([a["case"] for a in evidence["payment_attempts"]], ["FX01", "FX02", "MONEY-ROUND"])
        self.assertTrue(evidence["payment_failures"][0]["native_effects_unchanged"])
        self.assertEqual(evidence["native_http_error"], "Native invoice prerequisite missing")
        self.assertEqual(len(evidence["steps"]), 2)
        self.assertEqual(admin.action.call_count, 6)

    def test_failed_customer_and_diagnostic_do_not_skip_independent_serial_query(self):
        import contextlib
        import io
        import json
        import tempfile
        import urllib.error
        import urllib.parse
        from unittest.mock import Mock, patch
        from run import run_search_cases
        reader, admin = Mock(), Mock(); reader.samples = []
        specification = json.loads((FIXTURES / "scenarios.json").read_bytes())["search"]
        def reply(path, data=None):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
            if query.get("company_id") == ["OTHER-LAB"]:
                raise urllib.error.HTTPError(path, 403, "Denied", {}, io.BytesIO())
            if path.startswith("/ws/ccm/products/search"):
                if "page" in query:
                    codes = ["P001", "P002"] if query["page"] == ["1"] else ["P003"]
                    return {"total": 3, "items": [{"id": c} for c in codes]}
                return {"items": [{"id": c} for c in specification["products"][query["q"][0]]]}
            if path.startswith("/ws/ccm/lab/search/diagnostics"):
                raise urllib.error.HTTPError(path, 500, "Native diagnostic error", {}, io.BytesIO(b'Native filter failed'))
            if "TrackingNumber" in path:
                return {"status": 0, "data": [{"trackingNumberSeq": "SER-P001-001", "product.code": "P001"}]}
            return {"status": 0, "data": []}
        reader.request.side_effect = reply
        admin.request.return_value = {"status": 0, "data": [{"partnerSeq": "C001"}]}
        row = next(r for r in rows_for(verify_bundle(FIXTURES)) if r["case"] == "SEARCH01-04-NATIVE")
        with tempfile.TemporaryDirectory() as directory, patch("run.NativeClient", return_value=reader), contextlib.redirect_stdout(io.StringIO()):
            result = run_search_cases(admin, "unused", FIXTURES, Path(directory), row)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["subcase_failures"]), 2)
        self.assertIn("native-serial-query", [s["case"] for s in result["steps"]])
        self.assertTrue(any("Invoice/search" in c.args[0] for c in reader.request.call_args_list))
        customer_queries = [q for q in result["native_queries"] if q["model"].endswith("Partner")]
        self.assertEqual(len(customer_queries), 2)
        self.assertTrue(all(q["response"]["data"] == [] for q in customer_queries))
        self.assertTrue(all(q["reader_filter_diagnostics_http_error"] == "Native filter failed" for q in customer_queries))

    def test_large_native_fx_failure_remains_complete_extractable_json(self):
        import json
        import tempfile
        from run import REFERENCE, fx_notice_summary
        from extract_log_evidence import extract
        evidence = {"case": "FX01-03-MONEY01-03", "reference": REFERENCE, "revision": 1,
            "status": "FAIL", "complete": False, "error_type": "RuntimeError",
            "error": "Catalog must commit first: " + "native stack\n" * 300,
            "inspection_error": "No committed company: " + "native stack\n" * 300,
            "native_http_error": '{"error":"Native prerequisite missing", "stack":"' + "native stack\\n" * 300 + '"}'}
        summary = fx_notice_summary(evidence)
        self.assertLessEqual(len(json.dumps(summary)), 3200)
        self.assertIn("Catalog must commit first", summary["error"])
        self.assertGreater(len(evidence["error"]), 3200)  # Complete artifact data was not mutated.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); log = root / "run.log"
            log.write_text("##[notice]" + json.dumps(summary) + "\n")
            result = extract(log, root / "out", "test", "test", FIXTURES)
            row = next(r for r in result["groups"] if r["case"] == evidence["case"])
            self.assertEqual(row["status"], "FAIL")
            self.assertFalse(row["complete"])

    def test_native_invoice_fixture_rejects_missing_address_or_default_tax_regime(self):
        import copy
        from run import assert_native_configuration
        configuration = {"company_id": 1, "legal_partner_id": 4, "legal_vat_system": 2,
            "customers": [{"code": c, "invoicing_address_id": i} for i,c in enumerate(["C001", "C002", "CBANK"], 1)],
            "accounts": [{"code": c, "id": i, "vat_system": 1} for i,c in enumerate(["CCM-AR", "CCM-REVENUE", "CCM-TAX"], 1)]}
        assert_native_configuration(configuration)
        missing = copy.deepcopy(configuration); missing["customers"][0]["invoicing_address_id"] = 0
        with self.assertRaisesRegex(AssertionError, "Native invoicing address missing"):
            assert_native_configuration(missing)
        default = copy.deepcopy(configuration); default["accounts"][1]["vat_system"] = 0
        with self.assertRaisesRegex(AssertionError, "Native accrual account regime required"):
            assert_native_configuration(default)

    def test_fx_complete_requires_four_posted_payments_and_committed_liquidation(self):
        import copy
        import json
        from decimal import Decimal, ROUND_HALF_UP
        from run import review_native_fx
        fixture = json.loads((FIXTURES / "fx.json").read_bytes())
        observed, invoices, payments, rates = [], [], [], []
        def move(identity, currency, day, debit_account, credit_account, usd, foreign):
            return {"id": identity, "status": 3, "company_id": 1, "date": day,
                "currency": currency, "company_currency": "USD", "lines": [
                    {"id": identity*10+1, "account": debit_account, "debit": str(usd), "credit": "0",
                     "currencyAmount": str(foreign), "currencyRate": str((usd/foreign).quantize(Decimal(".000001"), rounding=ROUND_HALF_UP)), "amountRemaining": "0"},
                    {"id": identity*10+2, "account": credit_account, "debit": "0", "credit": str(usd),
                     "currencyAmount": str(-foreign), "currencyRate": str((usd/foreign).quantize(Decimal(".000001"), rounding=ROUND_HALF_UP)), "amountRemaining": "0"}]}
        for index, expected in enumerate(fixture["payments"], 1):
            reference = "FX-" + expected["id"]
            day = expected["date"]
            usd = sum(map(Decimal, expected["lines"]))
            foreign = expected.get("expected_lines", [expected["expected_total"]])
            native_invoice = {"id": index, "reference": reference, "company_id": 1,
                "customer": "C002", "date": day, "currency": "USD", "status": 3,
                "total": str(usd), "paid": str(usd), "remaining": "0",
                "move": move(100+index, "USD", day, "CCM-AR", "CCM-REVENUE", usd, usd)}
            invoices.append(native_invoice)
            native_ids = []
            for part, (source, amount) in enumerate(zip(expected["lines"], foreign), 1):
                identity = 10+len(payments)
                posted = move(200+identity, "VES", day, "CCM-CASH-VES", "CCM-AR", Decimal(source), Decimal(amount))
                payments.append({"id": identity, "reference": reference+"-"+str(part), "invoice_id": index,
                    "date": day, "currency": "VES", "amount": amount, "status": 1, "move": posted,
                    "reconcile": {"id": identity+500, "status": 2, "amount": source,
                        "debit_line_id": native_invoice["move"]["lines"][0]["id"], "credit_line_id": posted["lines"][1]["id"]}})
                native_ids.append(identity)
            rate = ["40", "41", "40.5"][index-1]
            rates.append({"id": index, "source": "USD", "target": "VES", "from_date": day, "to_date": day, "rate": rate})
            observed.append({"id": expected["id"], "date": day, "rate": rate, "native_conversion_id": index,
                "lines": foreign, "total": expected["expected_total"], "native_invoice_id": index, "native_payment_ids": native_ids})
            for payment in payments:
                if payment["invoice_id"] == index:
                    payment.update(observed_payment_day_conversion_id=index, observed_payment_day_rate=rate)
        persisted = {"company_id": 1, "company_code": "CCM-LAB-001", "read_boundary": "separate-http-after-payment-commit",
            "invoices": invoices, "payments": payments, "rates": rates,
            "authorizations": [{"id": 7, "company_id": 1, "native_conversion_id": 3, "approved_by": "ccm-manager",
                "external_id": "FX-AUTH", "reason": fixture["manual_rate"]["reason"]}]}
        assert_native_fx(observed, fixture, persisted)
        mutations = []
        missing = copy.deepcopy(persisted); missing["payments"] = []; mutations.append(missing)
        before_commit = copy.deepcopy(persisted); before_commit.pop("read_boundary"); mutations.append(before_commit)
        draft = copy.deepcopy(persisted); draft["payments"][0]["move"]["status"] = 1; mutations.append(draft)
        wrong_date = copy.deepcopy(persisted); wrong_date["payments"][1]["date"] = "2026-10-01"; mutations.append(wrong_date)
        unliquidated = copy.deepcopy(persisted); unliquidated["invoices"][0]["remaining"] = "1"; mutations.append(unliquidated)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                with self.assertRaises(AssertionError):
                    assert_native_fx(observed, fixture, candidate)
                row = {"status": "PASS", "complete": True}
                review_native_fx(row, {"observations": observed, "persisted": candidate}, fixture)
                self.assertNotEqual("PASS", row["status"])
                self.assertFalse(row["complete"])

    def test_bank_book_keeps_signed_native_credit_and_positive_unallocated_amount(self):
        import json
        import copy
        from decimal import Decimal
        fixtures = json.loads((FIXTURES / "bank-book.json").read_bytes())
        vouchers = []
        for index, row in enumerate(fixtures, 1):
            vouchers.append({"id": index, "reference": row["reference"], "status": 2,
                "company_id": 1, "company_code": "CCM-LAB-001", "partner_id": 9,
                "customer_id": row["customer_id"], "currency": row["currency"], "payment_date": row["date"],
                "paid_amount": row["amount"], "remaining_amount": row["amount"], "allocation_ids": [],
                "move": {"id": index, "status": 3, "voucher_id": index, "company_id": 1, "date": row["date"],
                    "lines": [{"id": index*2, "account": "CCM-BANK", "debit": row["amount"], "credit": "0", "remaining": row["amount"]},
                              {"id": index*2+1, "account": "CCM-AR", "debit": "0", "credit": row["amount"], "remaining": str(-Decimal(row["amount"]))}]}})
        native = {"company_id": 1, "vouchers": vouchers}
        self.assertEqual("255.00", assert_native_bank_book(native, fixtures)["unallocated_total"])
        wrong = copy.deepcopy(native)
        wrong["vouchers"][0]["move"]["lines"][1]["remaining"] = "100.00"
        with self.assertRaises(AssertionError):
            assert_native_bank_book(wrong, fixtures)

    def test_fx_aggregate_rounding_and_unauthorized_approver_are_rejected(self):
        import json
        import copy
        specification = json.loads((FIXTURES / "fx.json").read_bytes())
        observations, rates = [], []
        for index, row in enumerate(specification["payments"], 1):
            rate = ["40.000000", "41.000000", "40.500000"][index-1]
            observations.append({"id": row["id"], "date": row["date"], "rate": rate,
                "native_conversion_id": index, "lines": row.get("expected_lines", [row["expected_total"]]), "total": row["expected_total"]})
            rates.append({"id": index, "source": "USD", "target": "VES", "from_date": row["date"], "to_date": row["date"], "rate": rate})
        persisted = {"rates": rates, "authorizations": [{"id": 7, "company_id": 1, "native_conversion_id": 3,
            "approved_by": "ccm-manager", "external_id": "FX-AUTH", "reason": specification["manual_rate"]["reason"]}]}
        assert_native_fx_conversions(observations, specification, persisted)
        with self.assertRaises(AssertionError):
            assert_native_fx(observations, specification, persisted)
        aggregate = copy.deepcopy(observations)
        aggregate[-1].update(lines=["0.405", "0.405"], total="0.81")
        with self.assertRaises(AssertionError):
            assert_native_fx_conversions(aggregate, specification, persisted)
        unauthorized = copy.deepcopy(persisted)
        unauthorized["authorizations"][0]["approved_by"] = "ccm-operator"
        with self.assertRaises(AssertionError):
            assert_native_fx_conversions(observations, specification, unauthorized)

        # Reproduce the old complete six-step PASS, with valid calculations and
        # real-shaped rate/role evidence but no payments. It must remain partial.
        import tempfile
        from extract_log_evidence import extract
        from run import REFERENCE
        group = "FX01-03-MONEY01-03"
        steps = [{"case": o["id"], "native_conversion": o} for o in observations[:2]]
        steps += [{"case": "missing-rate", "http_status": 422, "native_effects_unchanged": True},
                  {"case": "operator-denied", "http_status": 403, "native_effects_unchanged": True},
                  {"case": "manager-authorized", "persisted": persisted},
                  {"case": "MONEY-ROUND", "native_conversion": observations[2]}]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            notices = [{"case": group, "step": s} for s in steps]
            notices.append({"case": group, "reference": REFERENCE, "revision": 1, "status": "PASS", "complete": True})
            log.write_text("\n".join("timestamp ##[notice]" + json.dumps(n) for n in notices) + "\n")
            result = extract(log, Path(tmp) / "results", "synthetic", "1" * 40, FIXTURES)
            row = next(r for r in result["groups"] if r["case"] == group)
            self.assertEqual("UNRUN", row["status"])
            self.assertFalse(row["complete"])
            self.assertEqual("PASS", row["partial_conversion_status"])
            saved = json.loads((Path(tmp) / "results" / (group + ".json")).read_text())
            self.assertEqual("PASS", saved["reported_status"])
            self.assertEqual("UNRUN", saved["status"])

    def test_fx_pass_notice_without_conversion_and_role_evidence_stays_unrun(self):
        import json
        import tempfile
        from extract_log_evidence import extract
        from run import REFERENCE
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text("timestamp ##[notice]" + json.dumps({"case": "FX01-03-MONEY01-03",
                "reference": REFERENCE, "revision": 1, "status": "PASS", "complete": True}) + "\n")
            result = extract(log, Path(tmp) / "results", "synthetic", "1" * 40, FIXTURES)
            self.assertEqual({"UNRUN": 34}, result["counts"])

    def test_bank_book_payments_without_posted_native_moves_fail(self):
        import json
        fixtures = json.loads((FIXTURES / "bank-book.json").read_bytes())
        vouchers = []
        for index, row in enumerate(fixtures, 1):
            vouchers.append({"id": index, "reference": row["reference"], "status": 2,
                "company_id": 1, "company_code": "CCM-LAB-001", "partner_id": 9,
                "customer_id": row["customer_id"], "currency": row["currency"],
                "payment_date": row["date"], "paid_amount": row["amount"],
                "remaining_amount": row["amount"], "allocation_ids": [],
                "move": {"id": index, "status": 1, "voucher_id": index, "lines": []}})
        with self.assertRaises(AssertionError):
            assert_native_bank_book({"company_id": 1, "vouchers": vouchers}, fixtures)

    def test_bank_book_pass_notice_without_native_details_stays_unrun(self):
        import json
        import tempfile
        from extract_log_evidence import extract
        from run import REFERENCE
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            log.write_text("timestamp ##[notice]" + json.dumps({"case": "BANK-BOOK-FIXTURE",
                "reference": REFERENCE, "revision": 1, "status": "PASS", "complete": True}) + "\n")
            result = extract(log, Path(tmp) / "results", "synthetic", "1" * 40, FIXTURES)
            self.assertEqual({"UNRUN": 34}, result["counts"])

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
        setup = {"company_id": 1, "profiles": [
            {"id": i, "product_id": i, "product_code": f"P{i:03}"} for i in (1, 2, 3)]}
        persisted_setup = {"company_id": 1,
            "profiles": [{**p, "company_id": 1} for p in setup["profiles"]],
            "users": [{"active": True, "blocked": False, "native_role_present": True,
                       "credentials_match": True, "company_id": 1} for _ in range(2)]}
        admin.action.side_effect = lambda name, case: persisted_setup if name.endswith("inspect") else setup
        row = next(r for r in rows_for(verify_bundle(FIXTURES)) if r["case"] == "PROD01-04")
        with tempfile.TemporaryDirectory() as tmp, patch("run.NativeClient", return_value=operator), contextlib.redirect_stdout(io.StringIO()):
            result = run_product_cases(admin, "unused", FIXTURES, Path(tmp), row)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual("FAIL", row["status"])
        self.assertFalse(row["complete"])
        self.assertEqual("ccm-operator", result["actor"])
        self.assertIn("warrantyQuantity", result["error"])

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

    def test_build_proof_rejects_upstream_difference_and_any_failed_suite(self):
        proof = {"lab_commit": "1" * 40, "host_commit": "1119727a3b53c8387b7fab535e184c25154d2eac",
                 "aos_commit": "0c70d561b19fc454eba9fdd41689258846626d75", "upstream_diff_exit_codes": {"host": 0, "aos": 1},
                 "baseline_pin_blob_sha256": "2" * 64, "expected_baseline_pin_blob_sha256": "2" * 64,
                 "suites": {name: {"tests": count, "failures": 0, "errors": 0, "skipped": 0}
                            for name, count in {"CencomunModuleTest": 2, "MoneyPolicyTest": 7, "TestTaxNumberHelper": 16}.items()},
                 "war_sha256": "3" * 64}
        self.assertEqual("FAIL", verified_build_status(proof))
        proof["upstream_diff_exit_codes"]["aos"] = 0
        self.assertEqual("PASS", verified_build_status(proof))
        proof["suites"]["NativeAddressTemplateTest"] = {"tests": 8, "failures": 1, "errors": 0, "skipped": 0}
        self.assertEqual("FAIL", verified_build_status(proof))
        proof["suites"]["NativeAddressTemplateTest"]["failures"] = 0
        self.assertEqual("PASS", verified_build_status(proof))


if __name__ == "__main__":
    unittest.main()
