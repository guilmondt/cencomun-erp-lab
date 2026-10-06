#!/usr/bin/env python3
"""Review a second execution restored into a fresh owned CI database, same pins."""
import json,sys
from pathlib import Path
from run import REFERENCE,criteria_for,publish_complete_evidence,verified_build_status
from benchmark import assert_benchmark

def assert_repeat(e,fixtures):
    assert e['reference']==REFERENCE and e['status']=='PASS'
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
    e={'case':'ISOLATED-FRESH-REPLAY','reference':REFERENCE,'revision':2,'status':'UNRUN','complete':False,'restore':json.loads((results/'isolated-restore.json').read_text())}
    for phase,directory,smoke in [('primary','core-test','smoke-restart.json'),('repeat','core-test-repeat','smoke-repeat-restart.json')]:
        root=results/directory;coverage=json.loads((root/'coverage.json').read_text())
        e[phase]={'coverage':coverage,'build_evidence':json.loads((root/'build-evidence.json').read_text()),'benchmark':json.loads((root/'benchmark.json').read_text()),'smoke':json.loads((results/smoke).read_text()),'gates':{name:json.loads((root/(name+'-gate.json')).read_text()) for name in ('CO00','TAX01-W')},'groups':{row['case']:json.loads((root/(row['case']+'.json')).read_text()) for row in coverage['groups'] if (root/(row['case']+'.json')).exists()}}
    try:e['status']='PASS';assert_repeat(e,fixtures);e['complete']=True
    except Exception as error:e.update(status='FAIL',error=type(error).__name__+': '+str(error))
    root=results/'core-test';(root/'isolated-repeat.json').write_text(json.dumps(e,indent=2)+'\n');publish_complete_evidence(e)
    coverage=e['primary']['coverage'];coverage['criteria']=criteria_for(coverage['groups'],e['primary']['build_evidence'],e['primary']['benchmark'],e,fixtures)
    coverage['isolated_repeat_status']=e['status'];coverage['benchmark_status']=e['primary']['benchmark']['status'];(root/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

if __name__=='__main__':review(*map(Path,sys.argv[1:]))
