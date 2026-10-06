"""Prevent zero-test success and inflation of real run counts by JUnit events."""

import unittest
import tempfile
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from run import parse_results, parse_parallel_results, reserve_attempt, SuiteLock, redact, active_runners
from isolate_bench import copy_compiled_assets, archive_test_sources
from recover import interrupted_record


class ResultCountingTests(unittest.TestCase):
    def test_recovered_runner_with_inaccessible_cwd_is_not_treated_as_inactive(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); process = root / '311'; process.mkdir()
            (process / 'cmdline').write_bytes(b'python\0run-parallel-tests\0--app\0erpnext\0')
            with patch('run.os.readlink', side_effect=PermissionError('restricted proc cwd')):
                self.assertEqual(active_runners(root / 'bench', root), [311])

    def test_native_ci_counter_is_not_inflated_by_verbose_subtest_events(self):
        log = ('erpnext.tests.TestOfficial\n  ✔ test_one\n  ✖ test_two\n'
               '  ✖ test_two\n  = test_three\nTests: 3, Failing: 2, Errors: 0\n')
        result = parse_parallel_results(log, 'erpnext')
        self.assertEqual(result['actual_tests_run'], 3)
        self.assertEqual(result['observed_result_events'], 4)
        self.assertEqual(result['counts'], {'PASS': 1, 'SKIP': 1, 'FAIL': 2, 'ERROR': 0})
        self.assertEqual(result['junit_records'], 0)

    def test_native_ci_interruption_keeps_final_count_unknown(self):
        result = parse_parallel_results('erpnext.tests.TestOfficial\n  ✔ test_one\n', 'erpnext')
        self.assertIsNone(result['actual_tests_run'])
        self.assertIsNone(result['counts']['ERROR'])
        self.assertFalse(result['native_summary_complete'])

    def test_native_ci_private_traceback_is_not_published(self):
        result = parse_parallel_results('erpnext.tests.TestOfficial\n  ✖ test_one\n'
                                        'Traceback: password=private-example\n'
                                        'Tests: 1, Failing: 0, Errors: 1\n', 'erpnext')
        self.assertNotIn('private-example', str(result))
        self.assertEqual(result['cases'][0]['status'], 'FAILED_EVENT')

    def test_native_ci_failure_headers_keep_only_id_and_exception_type(self):
        log = ('erpnext.tests.TestOfficial\n  ✖ test_one\n'
               ' ERROR test_one (erpnext.tests.TestOfficial.test_one)\n'
               'Traceback (most recent call last):\n  password = private-example\n'
               'frappe.exceptions.PermissionError\nTests: 1, Failing: 0, Errors: 1\n')
        result = parse_parallel_results(log, 'erpnext')
        self.assertEqual(result['failure_headers'], [{'id': 'erpnext.tests.TestOfficial.test_one',
            'status': 'ERROR', 'exception': 'frappe.exceptions.PermissionError'}])
        self.assertNotIn('private-example', str(result))

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

    def test_interrupted_native_ci_keeps_its_state_and_only_observed_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); base = 'erpnext-ci-attempt-1'
            (root / (base + '.log')).write_text('erpnext.tests.T\n  ✔ test_one\n')
            (root / (base + '-running.json')).write_text(json.dumps({
                'ci_parallel': True, 'site': 'isolated.test', 'command': 'native-ci-command'}))
            result = interrupted_record('erpnext', base, root, root, root)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIsNone(result['actual_tests_run'])
            self.assertTrue(result['ci_parallel'])
            self.assertEqual(result['site'], 'isolated.test')
            self.assertEqual(result['command'], 'native-ci-command')
            self.assertEqual(result['observed_result_events'], 1)
            self.assertIsNone(result['counts']['ERROR'])

    def test_interrupted_truncated_xml_preserves_complete_documents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); base = 'erpnext-full-attempt-2'
            (root / (base + '.log')).write_text('Ran 1 test in 0.01s\nOK\n')
            (root / (base + '.xml')).write_text('<?xml version="1.0"?><testsuites>'
                '<testsuite><testcase classname="T" name="test_one"/></testsuite></testsuites>'
                '<?xml version="1.0"?><testsuites><testsuite>')
            result = interrupted_record('erpnext', base, root, root, root)
            self.assertIsNone(result['actual_tests_run'])
            self.assertTrue(result['truncated_xml_document_preserved'])
            self.assertEqual(result['completed_native_category_counts'], [1])
            self.assertEqual(result['junit_records'], 1)
            self.assertEqual(result['cases'][0]['status'], 'PASS')

    def test_generated_temporary_site_passwords_are_redacted_after_config_deletion(self):
        text = ('bench new-site sample --admin-password=generated-demo-secret '
                '--db-root-password another-demo-secret --password=mysql-demo-secret')
        output = redact(text)
        self.assertNotIn('generated-demo-secret', output)
        self.assertNotIn('another-demo-secret', output)
        self.assertNotIn('mysql-demo-secret', output)
        self.assertEqual(output.count('[REDACTED]'), 3)

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

    def test_source_refresh_archives_generated_fixtures_without_deleting_them(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); apps = root / 'apps'; apps.mkdir()
            (apps / 'generated-test.py').write_text('old fixture data')
            archived = root / 'history/one/apps'
            archive_test_sources(apps, archived)
            self.assertEqual((archived / 'generated-test.py').read_text(), 'old fixture data')
            self.assertFalse(apps.exists())
            with self.assertRaisesRegex(RuntimeError, 'never overwrite'):
                archive_test_sources(apps, archived)


if __name__ == '__main__':
    unittest.main()
