"""Regression for the CI21 stop before ERP startup after adding two tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('ci_suites', Path(__file__).parents[1] / 'ci/validate-test-suites.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class CurrentRunSuitesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.host, self.module, self.results = (self.root / x for x in ['host', 'module', 'results'])
        self.upstream = self.host / 'modules/axelor-open-suite/axelor-base/build/test-results/test/TEST-com.axelor.apps.base.service.partner.registrationnumber.TestTaxNumberHelper.xml'
        self.write(self.upstream, 'TestTaxNumberHelper', 16)
        for name, count in ci.NATIVE_SUITES.items():
            self.write(self.path(name), name, count)

    def path(self, name):
        return self.module / 'build/full/test-results/test' / f'TEST-com.cencomun.core.{name}.xml'

    def write(self, path, name, count, failures=0, errors=0, skipped=0):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<testsuite name="{name}" tests="{count}" failures="{failures}" errors="{errors}" skipped="{skipped}"/>')

    def run_validation(self):
        with patch('builtins.print'):
            return ci.validate(self.host, self.module, self.results)

    def test_seven_finance_tests_required_and_recorded(self):
        suites = self.run_validation()
        self.assertEqual(7, int(suites['NativeFinanceModelTest']['tests']))
        self.assertEqual(45, sum(int(x['tests']) for x in suites.values()))
        self.assertEqual(7, len(list(self.results.glob('*.json'))))

    def test_old_five_test_suite_rejected_without_receipts(self):
        self.write(self.path('NativeFinanceModelTest'), 'NativeFinanceModelTest', 5)
        with self.assertRaisesRegex(AssertionError, 'expected 7 tests'):
            self.run_validation()
        self.assertFalse(self.results.exists())

    def test_failures_errors_and_skips_still_rejected(self):
        for field in ['failures', 'errors', 'skipped']:
            with self.subTest(field=field):
                self.write(self.path('NativeFinanceModelTest'), 'NativeFinanceModelTest', 7, **{field: 1})
                with self.assertRaises(AssertionError):
                    self.run_validation()
                self.assertFalse(self.results.exists())

    def test_missing_suite_rejected(self):
        self.path('NativeOrderModelTest').unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_validation()
        self.assertFalse(self.results.exists())
