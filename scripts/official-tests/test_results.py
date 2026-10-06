"""Prevent zero-test success and inflation of real run counts by JUnit events."""

import unittest
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from run import parse_results, reserve_attempt, SuiteLock, redact
from isolate_bench import copy_compiled_assets
from recover import interrupted_record


class ResultCountingTests(unittest.TestCase):
    def test_categories_are_separate_xml_documents(self):
        doc = '<?xml version="1.0"?><testsuites><testsuite><testcase classname="Official" name="{name}" time="0.1"/></testsuite></testsuites>'
        result = parse_results(doc.format(name='unit') + doc.format(name='integration'),
                               'Ran 1 test in 0.1s\nRan 1 test in 0.1s\n')
        self.assertEqual(result['actual_tests_run'], 2)
        self.assertEqual(result['xml_documents'], 2)

    def test_fixture_error_and_subtests_do_not_inflate_actual_run_count(self):
        xml = '''<testsuites><testsuite>
        <testcase classname="A" name="test_one"/>
        <testcase classname="A" name="test_two"><failure type="AssertionError">subtest failure</failure></testcase>
        <testcase classname="A" name="test_two"><failure type="AssertionError">another subtest</failure></testcase>
        <testcase classname="" name="setUpClass (B)"><error type="FixtureError">setup failed</error></testcase>
        </testsuite></testsuites>'''
        result = parse_results(xml, 'Ran 2 tests in 1.0s\nFAILED (failures=2, errors=1)')
        self.assertEqual(result['actual_tests_run'], 2)
        self.assertEqual(result['junit_records'], 4)
        self.assertEqual(result['counts']['ERROR'], 1)

    def test_noop_is_not_counted_as_a_suite(self):
        result = parse_results('', 'Testing is disabled for the site!')
        self.assertEqual(result['actual_tests_run'], 0)
        self.assertEqual(result['cases'], [])

    def test_concurrent_unfinished_attempts_reserve_different_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with ThreadPoolExecutor(max_workers=8) as pool:
                names = list(pool.map(lambda _: reserve_attempt('official', root, root), range(16)))
            self.assertEqual(len(set(base for _, base in names)), 16)
            self.assertEqual(sorted(number for number, _ in names), list(range(1, 17)))

    def test_existing_running_log_and_completed_result_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'official-attempt-1.log').write_text('still running')
            (root / 'official-attempt-2.json').write_text('{}')
            self.assertEqual(reserve_attempt('official', root, root)[0], 3)
            self.assertEqual((root / 'official-attempt-1.log').read_text(), 'still running')

    def test_active_suite_is_rejected_then_lock_is_reusable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with SuiteLock(root):
                with self.assertRaisesRegex(RuntimeError, 'active'):
                    with SuiteLock(root):
                        self.fail('duplicate suite accepted')
            with SuiteLock(root):
                pass

    def test_interrupted_run_does_not_promote_completed_unit_summary_to_full_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'erpnext-full-attempt-2.log').write_text(
                'Running 2 unit tests for erpnext\nRan 2 tests in 0.011s\nOK\n'
                'Running 3253 unspecified-category tests for erpnext\n....EEFF')
            (root / 'erpnext-full-attempt-2.xml').write_text('')
            result = interrupted_record('erpnext', 'erpnext-full-attempt-2', root, root, root)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIsNone(result['actual_tests_run'])
            self.assertEqual(result['completed_native_category_counts'], [2])
            self.assertEqual(result['cases'], [])

    def test_recovery_preserves_existing_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = root / 'erpnext-full-attempt-2.json'
            result.write_text('{"status":"BLOCKED"}')
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                interrupted_record('erpnext', 'erpnext-full-attempt-2', root, root, root)
            self.assertEqual(result.read_text(), '{"status":"BLOCKED"}')

    def test_generated_temporary_site_passwords_are_redacted_after_config_deletion(self):
        text = 'bench new-site sample --admin-password=generated-demo-secret --db-root-password another-demo-secret'
        output = redact(text)
        self.assertNotIn('generated-demo-secret', output)
        self.assertNotIn('another-demo-secret', output)
        self.assertEqual(output.count('[REDACTED]'), 2)

    def test_cloned_bench_receives_ignored_compiled_assets_and_manifests(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / 'source'; target = root / 'target'
            for app in ['frappe', 'erpnext']:
                directory = source / 'apps' / app / app / 'public/dist'
                directory.mkdir(parents=True)
                (directory / 'bundle.css').write_text(app + '-pinned-css')
            (source / 'sites/assets').mkdir(parents=True)
            (target / 'sites/assets').mkdir(parents=True)
            for name in ['assets.json', 'assets-rtl.json']:
                (source / 'sites/assets' / name).write_text('{}')
            copy_compiled_assets(source, target)
            for app in ['frappe', 'erpnext']:
                self.assertEqual((target / 'apps' / app / app / 'public/dist/bundle.css').read_text(), app + '-pinned-css')
            self.assertTrue((target / 'sites/assets/assets-rtl.json').exists())


if __name__ == '__main__':
    unittest.main()
