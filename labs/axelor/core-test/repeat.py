#!/usr/bin/env python3
"""Review a second execution restored into a fresh owned CI database, same pins."""
import json,os,sys
from pathlib import Path
from run import REFERENCE,criteria_for,publish_complete_evidence,verified_build_status
from benchmark import assert_benchmark
from evidence_index import FORMAT,build_index,load_index,file_notices

def assert_repeat(e,fixtures,evidence_root=None):
    if e.get('format')==FORMAT:
        payload,_=load_index(e,evidence_root)
        return assert_repeat_contents(payload,fixtures)
    assert e['status']=='PASS'
    return assert_repeat_contents(e,fixtures)

def assert_repeat_contents(e,fixtures):
    # The verdict is derived below, not trusted from an index's PASS label.
    # These are the unchanged business assertions used for the legacy capsule.
    assert e['reference']==REFERENCE
    restore=e['restore'];assert restore['source_database']=='ccm_axelor_ci' and restore['target_database']=='ccm_axelor_replay'
    assert restore['restore_exit_code']==0 and len(restore['backup_sha256'])==64
    first,second=e['primary'],e['repeat'];assert first['build_evidence']==second['build_evidence']
    assert verified_build_status(first['build_evidence'])=='PASS'
    assert len(first['coverage']['groups'])==len(second['coverage']['groups'])==34
    def signature(v):return [(r['case'],r['status'],r.get('complete',False)) for r in v['coverage']['groups']]
    assert signature(first)==signature(second),'Fresh restored execution has a different full-group result'
    assert all(r['status'] in ('PASS','FAIL') for r in first['coverage']['groups']),'Repeat cannot complete while groups are BLOCKED/UNRUN'
    from order_cases import GROUP_CHECKS,assert_group
    from finance_cases import FINANCE_CHECKS,assert_finance_group
    from api_cases import API_CHECKS,assert_api_group
    from audit_cases import RUNTIME_CHECKS,assert_runtime_group
    from recovery_cases import RECOVERY_CHECKS,assert_recovery_group
    for result in (first,second):
        assert result['smoke']['status']=='passed' and result['smoke']['authenticated'] is True
        for row in result['coverage']['groups']:
            evidence=result['groups'][row['case']];assert evidence['status']==row['status']
            if row['status']=='FAIL':assert evidence.get('error') or evidence.get('review_reason'),row['case']+': preserve observed failure'
            if row['status']=='PASS':
                for cases,validator in [(GROUP_CHECKS,assert_group),(FINANCE_CHECKS,assert_finance_group),(API_CHECKS,assert_api_group),(RUNTIME_CHECKS,assert_runtime_group),(RECOVERY_CHECKS,assert_recovery_group)]:
                    if row['case'] in cases:validator(evidence,fixtures)
        assert_benchmark(result['benchmark'],fixtures)
        for name in ('CO00','TAX01-W'):assert result['gates'][name]['status']=='PASS'
    assert first['benchmark']['loaded']['counts']==second['benchmark']['loaded']['counts']
    return True

def review(results,fixtures):
    e={'case':'ISOLATED-FRESH-REPLAY','reference':REFERENCE,'revision':2,'status':'UNRUN','complete':False}
    e.update(build_index(results,{'primary':(results/'core-test',results/'smoke-restart.json'),
        'repeat':(results/'core-test-repeat',results/'smoke-repeat-restart.json')},results/'isolated-restore.json'))
    payload,receipt=load_index(e,results);e['file_verification']=receipt
    try:assert_repeat_contents(payload,fixtures);e.update(status='PASS',complete=True)
    except Exception as error:e.update(status='FAIL',error=type(error).__name__+': '+str(error))
    root=results/'core-test';(root/'isolated-repeat.json').write_text(json.dumps(e,indent=2)+'\n')
    # CI already streams each phase immediately after its finalization, so a
    # later startup failure cannot erase primary proofs. Only restore is new.
    transport=e if os.environ.get('CCM_INDEXED_EVIDENCE')!='1' else {'reference':REFERENCE,'phases':{},'restore':e['restore']}
    for notice in file_notices(transport,results):print('::notice title=Complete indexed evidence file::'+json.dumps(notice),flush=True)
    publish_complete_evidence(e)
    coverage=payload['primary']['coverage'];coverage['criteria']=criteria_for(coverage['groups'],payload['primary']['build_evidence'],payload['primary']['benchmark'],e,fixtures,results)
    coverage['isolated_repeat_status']=e['status'];coverage['benchmark_status']=payload['primary']['benchmark']['status'];(root/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

if __name__=='__main__':review(*map(Path,sys.argv[1:]))
