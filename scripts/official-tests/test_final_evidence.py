import unittest
from final_diagnostics import classify
from publish_observations import selected_events
from run import parse_parallel_results


class FinalEvidenceTests(unittest.TestCase):
    def test_local_refusal_does_not_claim_an_inevitable_environment_block(self):
        category, cause = classify("requests.exceptions.ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=8002): Connection refused\n", [])
        self.assertEqual(category, 'DEMONSTRATED_LOCAL_HTTP_REFUSAL_CAUSE_UNKNOWN')
        self.assertIn('UNKNOWN', cause)
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
