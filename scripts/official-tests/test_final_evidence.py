import unittest
import tempfile
from pathlib import Path
from closure import sites_workdir
from final_diagnostics import classify
from publish_observations import selected_events
from run import parse_parallel_results


class FinalEvidenceTests(unittest.TestCase):
    def test_missing_rate_requires_same_native_pair_and_linked_offline_error(self):
        terminal = ('frappe.exceptions.ValidationError: Exchange Rate is mandatory. '
                    'Maybe Currency Exchange record is not created for INR to USD.\n')
        events = [
            {'kind': 'native_state', 'stage': 'before_test', 'fx_settings': {'disabled': 0}},
            {'kind': 'native_fx_error_log', 'pid': 123,
             'terminal_exception': 'requests.exceptions.ConnectionError: Official offline reproduction: external HTTP prohibited'},
            {'kind': 'fx_return', 'pid': 123, 'result': 0.0, 'entries': [],
             'from_currency': 'INR', 'to_currency': 'USD'},
        ]
        self.assertEqual(classify(terminal, events)[0], 'DEMONSTRATED_OFFLINE_MISSING_NATIVE_RATE')
        events[0]['fx_settings']['disabled'] = 1
        self.assertEqual(classify(terminal, events)[0], 'UNKNOWN')
        events[0]['fx_settings']['disabled'] = 0
        events[2]['to_currency'] = 'EUR'
        self.assertEqual(classify(terminal, events)[0], 'UNKNOWN')
        events[2]['to_currency'] = 'USD'
        events[1]['pid'] = 999
        self.assertEqual(classify(terminal, events)[0], 'UNKNOWN')

    def test_revaluation_imbalance_is_not_attributed_from_a_linked_fx_error(self):
        events = [{'kind': 'native_fx_error_log', 'terminal_exception': 'Official offline reproduction'}]
        self.assertEqual(classify('frappe.exceptions.ValidationError: Total Debit must be equal to Total Credit. The difference is 100.0\n', events)[0], 'UNKNOWN')

    def test_readonly_closure_supports_native_site_log_paths(self):
        from frappe.utils.logger import create_handler
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            bench = Path(folder) / 'bench'
            (bench / 'logs').mkdir(parents=True)
            site = 'closure-fixture.test'
            (bench / 'sites' / site / 'logs').mkdir(parents=True)
            with sites_workdir(bench):
                handlers = create_handler('closure-proof', site, 100_000, 1, False)
                try:
                    self.assertEqual(len(handlers), 2)
                    self.assertEqual(Path(handlers[1].baseFilename),
                                     bench / 'sites' / site / 'logs' / 'closure-proof.log')
                finally:
                    for handler in handlers:
                        handler.close()
            self.assertEqual(Path.cwd(), previous)

    def test_local_refusal_does_not_claim_an_inevitable_environment_block(self):
        category, cause = classify("requests.exceptions.ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=8002): [Errno 111] Connection refused\n", [])
        self.assertEqual(category, 'DEMONSTRATED_LOCAL_HTTP_REFUSAL_CAUSE_UNKNOWN')
        self.assertIn('UNKNOWN', cause)
    def test_responses_refusal_is_not_tcp_refusal(self):
        block = ('  File "/env/site-packages/responses/__init__.py", line 1046, in _on_request\n'
                 "requests.exceptions.ConnectionError: Connection refused by Responses - the call doesn't match any registered mock.\n"
                 'Request: GET http://127.0.0.1:8002/api/resource/User\n')
        category, cause = classify(block, [])
        self.assertEqual(category, 'DEMONSTRATED_NATIVE_HTTP_MOCK_REJECTION')
        self.assertIn('before socket', cause)
        block = "requests.exceptions.ConnectionError: Connection refused, 127.0.0.1\n"
        self.assertEqual(classify(block, [])[0], 'UNKNOWN')
    def test_native_outcome_after_progress_without_newline_keeps_its_known_id(self):
        identifier = 'frappe.tests.TestOfficial.test_one'
        result = parse_parallel_results('frappe.tests.TestOfficial\nprogress without newline ✔ test_one\nTests: 1, Failing: 0, Errors: 0\n',
                                        'frappe', [identifier])
        self.assertEqual(result['cases'], [{'id': identifier, 'status': 'PASS'}])
    def test_fixture_skip_is_recorded_without_inflating_native_counter(self):
        result = parse_parallel_results('  = setUpClass (frappe.tests.TestOfficial)\nTests: 0, Failing: 0, Errors: 0\n',
                                        'frappe', ['frappe.tests.TestOfficial.test_one'])
        self.assertEqual(result['actual_tests_run'], 0)
        self.assertEqual(result['cases'][0]['status'], 'SKIP')
        self.assertEqual(result['cases'][0]['id'], 'frappe.tests.TestOfficial.setUpClass')
    def test_bare_exception_type_cannot_replace_a_known_ci_test_class(self):
        identifier = 'frappe.tests.TestOfficial.test_one'
        log = ('frappe.tests.TestOfficial\nfrappe.exceptions.AuthenticationError\n'
               '  ✔ test_one\nTests: 1, Failing: 0, Errors: 0\n')
        result = parse_parallel_results(log, 'frappe', [identifier])
        self.assertEqual(result['cases'], [{'id': identifier, 'status': 'PASS'}])
    def test_readonly_home_requires_terminal_evidence(self):
        category, _ = classify("OSError: [Errno 30] Read-only file system: '/home/agent/.cache'\n", [])
        self.assertEqual(category, 'DEMONSTRATED_READONLY_HOME')
        category, _ = classify("  old_error = OSError: [Errno 30] Read-only file system: '/home/agent'\nAssertionError: unequal\n", [])
        self.assertEqual(category, 'UNKNOWN')

    def test_linked_network_rejection_does_not_alone_prove_failure_cause(self):
        category, _ = classify('AssertionError: unexpected value\n', [{'kind': 'external_http_rejected'}])
        self.assertEqual(category, 'UNKNOWN')

    def test_terminal_offline_rejection_is_a_demonstrated_limit(self):
        category, _ = classify('requests.exceptions.ConnectionError: Official offline reproduction: external HTTP prohibited\n', [])
        self.assertEqual(category, 'DEMONSTRATED_OFFLINE_TRANSPORT_REJECTION')

    def test_compact_full_observations_keep_boundaries_failures_and_transport(self):
        events = [{'kind': 'native_state', 'stage': 'before_test', 'test': 'frappe.mod.C.test_' + str(i)} for i in range(5)]
        events.append({'kind': 'external_http_rejected', 'test': 'frappe.mod.C.test_2'})
        result = {'ci_parallel': True, 'site': 'ccm-upstream-frappe-final.test',
                  'cases': [{'id': 'frappe.mod.C.test_2', 'status': 'FAILED_EVENT'}]}
        chosen = selected_events(events, result)
        self.assertEqual(chosen, [events[0], events[2], events[4], events[5]])

    def test_scoped_observation_history_is_not_compacted(self):
        events = [{'kind': 'native_state', 'stage': 'before_test', 'test': 'frappe.mod.C.test_' + str(i)} for i in range(5)]
        self.assertEqual(selected_events(events, {'site': 'ccm-upstream-frappe-diagnostic.test'}), events)


if __name__ == '__main__':
    unittest.main()
