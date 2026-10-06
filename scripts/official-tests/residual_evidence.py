"""Reconcile the 56 original failures without altering full native counters."""
import collections
import hashlib
import json
import re
from run import OUT, PRIVATE, active_runners


def statuses(data):
    result = {c['id']: c['status'] for c in data['cases']}
    result.update({c['id']: c['status'] for c in data.get('failure_headers', [])})
    return result


def attempts_after(full):
    rows = []
    for path in OUT.glob('frappe-*-attempt-*.json'):
        data = json.loads(path.read_text())
        if (data.get('cases') and not data.get('ci_parallel') and
                (data.get('module') or data.get('sequence')) and
                data['recorded_utc'] > full['recorded_utc']):
            rows.append((data['recorded_utc'], path, data))
    return sorted(rows)


def latest(rows, identifiers):
    result = {}
    for _, path, data in rows:
        for identifier, status in statuses(data).items():
            if identifier in identifiers:
                result[identifier] = {'status': status, 'result': path.name,
                                     'scope': data['scope'], 'site': data['site']}
    return result


def original_blocks(full):
    raw = re.sub(r'\x1b\[[0-9;]*m', '',
                 (PRIVATE / 'frappe-ci-attempt-1.log').read_text())
    assert hashlib.sha256((PRIVATE / 'frappe-ci-attempt-1.log').read_bytes()).hexdigest() == full['log_sha256']
    result = {}
    for case in full['failure_headers']:
        method = case['id'].rsplit('.', 1)[1]
        matches = re.finditer(r'^\s*' + case['status'] + r'\s+' + method +
                             r'\s+\(([^)]+)\)', raw, re.M)
        match = next(m for m in matches if m[1] in (case['id'], case['id'].rsplit('.', 1)[0]))
        end = re.search(r'^={30,}\s*$', raw[match.end():], re.M)
        block = raw[match.end():match.end()+end.start()] if end else raw[match.end():]
        result[case['id']] = {'native_trace_frames': re.findall(r'^  File .+$', block, re.M),
            'private_trace_block_sha256': hashlib.sha256(block.encode()).hexdigest(),
            'original_errno30_present': '[Errno 30]' in block,
            'original_readonly_message_present': 'Read-only file system' in block,
            'original_responses_refusal': 'Connection refused by Responses' in block}
    return result


def main():
    assert not active_runners()
    full = json.loads((OUT / 'frappe-ci-attempt-1.json').read_text())
    originals = full['failure_headers']; assert len(originals) == 56
    ids = {c['id'] for c in originals}; assert len(ids) == 56
    preserved = json.loads((PRIVATE / 'pre-residual-evidence-hashes.json').read_text())
    attempts = attempts_after(full)
    prior = latest([r for r in attempts if str(r[1]) in preserved], ids)
    assert collections.Counter(r['status'] for r in prior.values()) == {'PASS': 36, 'FAIL': 1}
    assert len(ids-prior.keys()) == 19
    current = latest(attempts, ids)
    offline = {r['id'] for r in json.loads((OUT / 'frappe-final-failure-diagnostics-v2.json').read_text())['cases']
               if r['classification'] == 'DEMONSTRATED_OFFLINE_TRANSPORT_REJECTION' and r['id'] not in prior}
    assert len(offline) == 4
    traces = original_blocks(full)
    rows = []
    for case in originals:
        identifier = case['id']; later = current.get(identifier)
        evidence = [later['result']] if later else []
        next_step = 'Stop: bounded PASS covers only its recorded methods/site/process. Full FAIL remains.'
        if identifier in offline:
            classification = 'DEMONSTRATED_OFFLINE_LIMIT_RETAINED'
            next_step = 'Keep original ERROR; no new external DNS/SMTP/HTTP or network permission changes authorized.'
            evidence += ['frappe-final-failure-diagnostics-v2.json']
        elif '.test_auth_via_api_key_secret' in identifier:
            classification = 'UNKNOWN_API_KEY_CIPHER_KEY_HISTORY'
            evidence += ['residual-api-key-read-only.json']
            next_step = 'Existing secret cannot be decrypted with retained keys. Review already-retained key/cache identity chronology; otherwise a separate disposable-site diagnostic needs approval. Never regenerate this key.'
        elif '.TestBackups.' in identifier:
            classification = 'DEMONSTRATED_READONLY_HOME_IN_NEW_ATTEMPT'
            evidence += ['frappe-test_commands-selected-attempt-1-observations.json']
            next_step = 'New per-command trace proves errno30 under HOME. Original trace lacks errno30. Stop; no HOME remapping or writes.'
        elif '.test_existing_db_username' in identifier:
            classification = 'DEMONSTRATED_NATIVE_EXISTING_USER_PASSWORD_CONTRACT'
            evidence += ['residual-existing-db-user-read-only.json']
            next_step = 'Keep FAIL; native CREATE USER IF NOT EXISTS leaves the preexisting passwordless account unchanged. Changing installer/account/access is outside scope.'
        elif '.test_set_password' in identifier:
            classification = 'DEMONSTRATED_NATIVE_PASSWORD_RESTORE_OPTION_PARSING'
            evidence += ['residual-retained-password-read-only.json']
            next_step = 'Keep FAIL; native restore command interpreted retained password prefix as an option. No rerun/reset. Native command argument handling would require a separate upstream/version decision.'
        elif '.test_no_unnecessary_migrates' in identifier:
            classification = 'DEMONSTRATED_NATIVE_SCHEMA_INDEX_CONTRACT'
            evidence += ['residual-schema-contract-read-only.json', 'residual-schema-subcase.json']
            next_step = 'Original generated-column subcase repeats two ALTERs vs zero; secondary writeln AttributeError is native result-stream handling. No random resampling to seek PASS or upstream/assertion change.'
        elif '.test_connect_fails_with_wrong_credentials_by_env' in identifier:
            classification = 'DEMONSTRATED_SOCKET_PREPARATION_AND_TCP_ACCESS_LIMIT'
            evidence += ['residual-db-transport-before.json', 'residual-db-transport-after.json', 'frappe-test_db-selected-attempt-2.json']
            next_step = 'Socket masks host-negative assertion. TCP needs DB host access: native 1130, only localhost grant. TCP attempt has zero tests/no method result; original socket restored. No grant/auth changes authorized.'
        elif '.test_memory_usage' in identifier:
            classification = 'RESOLVED_OWN_EAGER_HTTP_GUARD_IMPORT'
            evidence += ['frappe-test_rq_job-selected-attempt-1.json', 'residual-worker-memory-v2.json']
        elif '.test_rq_pool_idle_cpu_usage' in identifier:
            classification = 'BOUNDED_PASS_WITHOUT_FRAME_PROFILING'
            next_step += ' Historical CPU 46 vs 10; exact historical contribution of startup/profile load not measured.'
        elif '.TestActivityLog.' in identifier:
            classification = 'BOUNDED_PASS_CLEAN_NATIVE_AUTH_PREPARATION'
            evidence += ['residual-retained-password-read-only.json']
        elif '.TestEmailAccount.' in identifier:
            classification = 'BOUNDED_PASS_CLEAN_NATIVE_FIXTURES_HISTORICAL_STATE_UNKNOWN'
            next_step += ' Historical inbound list/reference/notification state was not captured; no causal claim about which earlier module changed it.'
        elif '.TestEmailIntegrationTest.' in identifier:
            classification = 'BOUNDED_PASS_CORRECTED_GUARD_NATIVE_PREPARATION'
            evidence += ['frappe-test_email-selected-attempt-1.json']
        else:
            classification = 'PREVIOUS_BOUNDED_PASS_RETAINED'
        rows.append({**case, 'original_native_result': 'frappe-ci-attempt-1.json',
            'prior_bounded_status': prior.get(identifier, {}).get('status', 'UNRUN'),
            'latest_bounded_status': later['status'] if later else 'UNRUN',
            'latest_bounded_scope': later['scope'] if later else 'No later official method execution',
            'classification': classification, 'evidence': evidence,
            'stop_condition_or_next_step': next_step, **traces[identifier]})
    auth = json.loads((OUT / 'auth-bounded-results.json').read_text())
    additional = [r for r in auth['remaining_16_by_id'] if '.TestClient.' in r['id']]
    assert len(additional) == 2 and all(r['latest_bounded_status']=='ERROR' for r in additional)
    assert not ids.intersection(r['id'] for r in additional)
    for r in additional:
        r.update(evidence=['auth-bounded-results.json','frappe-test_client-attempt-2.json'],
                 reexecuted_in_residual_task=False,
                 stop_condition='Native Workflow request/cache_control contract demonstrated; no further pursuit.')
    new_attempts = []
    for p in sorted(OUT.glob('frappe-*-attempt-*.json')):
        d = json.loads(p.read_text())
        if d.get('site') == 'ccm-upstream-frappe-residual.test':
            assert hashlib.sha256((PRIVATE/(p.stem+'.log')).read_bytes()).hexdigest()==d['log_sha256']
            selected_ids = {i for category in json.loads((OUT/'frappe-discovery-final.json').read_text())['categories']
                            for i in category['test_ids'] if i.startswith(d['module']+'.') and i.rsplit('.',1)[1] in d['selected_tests']}
            missing = sorted(selected_ids-statuses(d).keys())
            new_attempts.append({'result':p.name,'status':d['status'],'actual_tests_run':d['actual_tests_run'],
                'counts':d['counts'],'selected_tests':d['selected_tests'],'scope':d['scope'],
                'ids_without_result':missing,'native_runner_started':not bool(d.get('startup_error')),
                'bootstrap_only_or_startup_failed_not_pass':not bool(d['actual_tests_run'])})
    erp = json.loads((OUT/'erpnext-ci-attempt-2.json').read_text())
    assert len(erp['failure_headers']) == 4
    erp_rows = [{**r, 'original_native_result':'erpnext-ci-attempt-2.json',
                 'classification':'DEMONSTRATED_NATIVE_JOURNAL_FALLBACK_AND_OFFLINE_RATE_LIMIT'
                  if '.test_05_revaluation_journal_reversal' in r['id'] else 'DEMONSTRATED_OFFLINE_MISSING_ELIGIBLE_NATIVE_RATE',
                 'reexecuted_in_residual_task':False} for r in erp['failure_headers']]
    data = {'scope':'56 original failure IDs plus two additional Client IDs; no full suite rerun/recalculation',
        'starting_commit':'678c5ef0d90f628bece3fea0adce2ab5ad541ee9',
        'initial_reconciliation':{'PASS':36,'FAIL':1,'UNRUN':19},
        'full_frappe':{'status':full['status'],'actual_tests_run':full['actual_tests_run'],'counts':full['counts'],'SKIP':50},
        'full_erpnext':{'status':erp['status'],'actual_tests_run':erp['actual_tests_run'],'counts':erp['counts']},
        'original_56_by_id':rows,'additional_client_by_id':additional,
        'latest_bounded_id_counts':dict(collections.Counter(r['latest_bounded_status'] for r in rows)),
        'counts_never_added_to_full':True,'UNRUN_definition':'No later official execution of this method; original FAIL/ERROR remains. Read-only/subcase diagnosis is not a method PASS.',
        'new_selected_attempts':new_attempts,'new_native_executions':sum(r['actual_tests_run'] for r in new_attempts),
        'four_offline_ids_retained':sorted(offline),'erpnext_fx_by_id':erp_rows,
        'criterion_13':{'status':'BLOCKED','PATCH_UNRUN':6},'previous_core_scope':{'mandatory_groups':34,'PASS':34,'rerun':False}}
    assert data['latest_bounded_id_counts'] == {'PASS':45,'FAIL':4,'UNRUN':7}
    assert data['new_native_executions'] == 15
    with (OUT/'residual-final-matrix.json').open('x') as stream:
        stream.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'original_ids':len(rows),'additional_client_ids':len(additional),
                      'latest_bounded_counts':data['latest_bounded_id_counts'],
                      'new_native_executions':data['new_native_executions']}))


if __name__=='__main__': main()
