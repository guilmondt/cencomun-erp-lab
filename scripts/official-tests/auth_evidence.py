"""Derived auth evidence with assertions; preserves all native attempts."""
import collections
import datetime
import hashlib
import json
import re
from run import OUT, PRIVATE, active_runners, observed_native_ids, parse_parallel_results

BASES = [
    'frappe-test_frappe_client-selected-attempt-1',
    'frappe-test_client-selected-attempt-1',
    'frappe-test_oauth20-selected-attempt-1',
    'frappe-sequence-test_oauth20-attempt-1',
    'frappe-sequence-test_oauth20-attempt-2',
    'frappe-test_perf-attempt-1',
    'frappe-test_client-attempt-1',
    'frappe-test_client-attempt-2',
]


def events(base):
    return [json.loads(line) for line in (PRIVATE/(base+'-observations.jsonl')).read_text().splitlines()]


def statuses(result):
    data = {case['id']: case['status'] for case in result['cases']}
    data.update({case['id']: case['status'] for case in result.get('failure_headers', [])})
    return data


def write(name, data):
    with (OUT/(name+'.json')).open('x') as stream:
        stream.write(json.dumps(data, indent=2)+'\n')
    print(name)


def main():
    assert not active_runners()
    summaries = []
    parsed = {}
    for base in BASES:
        original = json.loads((OUT/(base+'.json')).read_text())
        raw = (PRIVATE/(base+'.log')).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == original['log_sha256']
        ids = observed_native_ids(PRIVATE/(base+'-observations.jsonl'))
        result = parse_parallel_results(raw.decode(), 'frappe', ids) if original['sequence'] else original
        parsed[base] = result
        assert not any(e['kind']=='observation_error' for e in events(base))
        expected = ({i for i in ids if i.rsplit('.',1)[1] in original['selected_tests']}
                    if ids and original['selected_tests'] else ids)
        discovery_source = 'Actual native loader in this attempt'
        if expected is None:
            reference = json.loads((OUT/'frappe-discovery-final.json').read_text())
            expected = {i for category in reference['categories'] for i in category['test_ids']
                        if i.startswith(original['module']+'.')}
            discovery_source = 'Retained pinned native discovery, filtered to module; no new discovery for unprofiled benchmark'
        missing = sorted(expected-set(statuses(result)))
        assert not missing
        summaries.append({'native_result':base+'.json','site':original['site'],
            'scope':original['scope'],'native_count':result['actual_tests_run'],
            'counts':result['counts'],'loader_distinct_ids':len(ids) if ids else None,
            'discovery_source':discovery_source,'expected_selected_ids':len(expected),
            'loaded_but_unselected_ids':sorted(ids-expected) if ids else [],
            'ids_without_result':missing,'cases_by_id':[
                {'id':identifier,'status':status} for identifier,status in sorted(statuses(result).items())],
            'counts_added_to_full_CI':False})
    previous = json.loads((OUT/'frappe-sequence-test_perf-attempt-1.json').read_text())
    remaining = previous['failure_headers']
    assert len(remaining)==16
    latest_client = statuses(parsed['frappe-test_client-attempt-2'])
    corrected = statuses(parsed['frappe-sequence-test_oauth20-attempt-2'])
    perf = statuses(parsed['frappe-test_perf-attempt-1'])
    rows = []
    for case in remaining:
        identifier = case['id']
        if '.test_client.' in identifier:
            current = latest_client[identifier]; reason='DEMONSTRATED_NATIVE_WORKFLOW_REQUEST_CONTRACT'
        elif '.test_perf.' in identifier:
            current = perf[identifier]; reason='RESOLVED_NEW_SITE_NATIVE_CREDENTIAL_PRECEDENCE'
        else:
            current = corrected[identifier]
            reason = ('RESOLVED_SECONDARY_LOGIN_LOCK_FAILURE' if '.test_oauth20.' in identifier
                      else 'RESOLVED_NEW_SITE_NATIVE_CREDENTIAL_PRECEDENCE')
        rows.append({'id':identifier,'retained_sequence_status':case['status'],
                     'latest_bounded_status':current,'classification':reason})
    assert collections.Counter(r['latest_bounded_status'] for r in rows)=={'PASS':14,'ERROR':2}
    mismatch = events('frappe-sequence-test_oauth20-attempt-1')
    oauth_error = next(e for e in mismatch if e['kind']=='native_http_exception' and
                      e['route']=='/api/method/login')
    assert oauth_error['exception']=='SecurityException'
    locked = [e for e in mismatch if e['kind']=='native_auth_tracker' and
              e['tracker_kind']=='loopback_ip' and e['allowed'] is False]
    assert locked and all(e['failed_count']>e['max_failed_logins'] for e in locked)
    oauth_state = next(e for e in mismatch if e['kind']=='native_oauth_assertion_state' and e['line']==390)
    assert oauth_state['response_parameter_names']==[] and not oauth_state['access_token_present']
    correct_events = events('frappe-sequence-test_oauth20-attempt-2')
    success = next(e for e in correct_events if e['kind']=='native_oauth_assertion_state' and e['line']==390)
    assert success['access_token_present']
    client_events = events('frappe-test_client-attempt-2')
    client = []
    for failure in [e for e in client_events if e['kind']=='native_cache_html' and e['stage']=='exception']:
        assert not failure['request_is_none'] and failure['cache_control_is_none']
        assert failure['exception_attribute']=='no_cache' and failure['caller'][0]['line']==537
        assignment = [e for e in client_events if e['kind']=='request_context_transition' and
                      e['operation']=='__setattr___return' and e['pid']==failure['pid'] and e['epoch']<=failure['epoch']][-1]
        assert assignment['caller'][0]['file'].endswith('frappe/tests/test_client.py')
        client.append({'failure':failure,'last_native_request_assignment':assignment})
    assert len(client)==2
    prep = events('auth-sequence-preparation')
    write('auth-preparation-observations', {'scope':'Preparation only; zero official tests',
        'private_stream_sha256':hashlib.sha256((PRIVATE/'auth-sequence-preparation-observations.jsonl').read_bytes()).hexdigest(),
        'events':prep,'native_installation_not_password_reset':True})
    measurements = re.findall(r'Completed 1000 in ([\d.]+) @ ([\d.]+) requests per seconds',
                              (PRIVATE/'frappe-test_perf-attempt-1.log').read_text())
    assert len(measurements)==1 and float(measurements[0][1])>=126
    write('auth-bounded-results', {'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'starting_commit':'baad8f9f45373005b72e7c4609ad57ca35dfe34d',
        'scope':'16 retained nine-module failures, not a complete suite or Core rerun',
        'attempts':summaries,'remaining_16_by_id':rows,'latest_16_counts':{'PASS':14,'ERROR':2},
        'client_exact_failure_and_assignment':client,
        'oauth_failure':{'native_login_exception':oauth_error,'native_lock_states':locked,
                        'assertion':oauth_state,
                        'redirects':[e for e in mismatch if e['kind']=='native_http_reply' and e.get('status')==302]},
        'oauth_corrected_assertion':success,
        'historical_login_500_exception_not_captured_in_old_stream':True,
        'causality_demonstrated_in_new_bounded_reproduction_not_retroactive_telemetry':True,
        'performance':{'native_requests':1000,'native_seconds':measurements[0][0],
                       'native_rps':measurements[0][1],'unchanged_native_minimum_rps':126,
                       'frame_profiling_disabled_for_measurement':True},
        'additional_outcomes':[
            {'id':'frappe.tests.test_client.TestClient.test_client_get','earlier':'ERROR',
             'latest':'PASS','cause':'Missing retained wkhtmltopdf on invocation PATH; PATH corrected only.'},
            {'id':'frappe.tests.test_frappe_client.TestFrappeClient.test_auth_via_api_key_secret',
             'latest':'FAIL','classification':'UNKNOWN',
             'facts':'First positive API request returned 401 instead of 200. Read-only post-run probe finds stored API secret not decryptable with retained site key.',
             'unknown':'Exact initial key/config/cache mutation order was not captured. No key repair, credential regeneration or repetition to force PASS.'}],
        'full_official_results_unchanged':'FAIL','criterion_13':{'status':'BLOCKED','PATCH_UNRUN':6}})


if __name__=='__main__': main()
