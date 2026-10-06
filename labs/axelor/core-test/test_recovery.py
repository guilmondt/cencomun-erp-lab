import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from audit_cases import RUNTIME_CHECKS, review_runtime_group, assert_runtime_group, assert_audit_semantics
from recovery_cases import RECOVERY_CHECKS, review_recovery_group, assert_recovery_group
from consumer import initialize, apply, snapshot
from run import REFERENCE, verify_bundle, NativeActionError
from api_cases import ApiCases, BOUNDARY

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'


class RecoveryEvidenceRegression(unittest.TestCase):
    def test_durable_consumer_replay_keeps_one_effect_under_concurrency(self):
        payload={'schema_version':1,'event_id':'cashea.approved:CO00:1','object_id':'CO00','company_id':'CCM-LAB-001','actor':'ccm-simulator','occurred_at':'2026-10-01T10:00:00-04:00','correlation_id':'CO00-approved','type':'cashea.approved','data':{'id':'CO00','state':'APPROVED'}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'consumer.sqlite';initialize(path)
            with ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:apply(path,payload),range(2)))
            before=snapshot(path);initialize(path);after=snapshot(path)
            self.assertEqual(before,after);self.assertEqual(after['receipts'][0]['deliveries'],2);self.assertEqual(after['effects'][0]['applications'],1)
            with self.assertRaisesRegex(ValueError,'payload conflict'):apply(path,{**payload,'data':{'id':'CO00','state':'SETTLED'}})
            self.assertEqual(snapshot(path),after)
    def test_incomplete_envelope_does_not_enter_consumer(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'consumer.sqlite';initialize(path)
            with self.assertRaises(AssertionError):apply(path,{'event_id':'invented-only'})
            self.assertEqual(snapshot(path),{'receipts':[],'effects':[]})
    def test_saved_restart_instructions_or_labels_are_not_executed_recovery(self):
        for cases,review in [(RECOVERY_CHECKS,review_recovery_group),(RUNTIME_CHECKS,review_runtime_group)]:
            for case in cases:
                row=next(dict(r,status='PASS',complete=True,observed_revision=2) for r in verify_bundle(FIXTURES)['requirements'] if r['case']==case)
                evidence={'case':case,'reference':REFERENCE,'revision':2,'status':'PASS','complete':True,'steps':[],'restart_script':'run later'}
                review(row,evidence,FIXTURES);self.assertEqual(row['status'],'FAIL');self.assertFalse(row['complete'])
    def test_native_action_failure_retains_complete_response_before_assertion(self):
        runner=object.__new__(ApiCases);e={'steps':[]};response={'status':-1,'data':{'causeStack':'actual native error\n'*2000}}
        def failing(step):step['request']={'action':'native-probe'};raise NativeActionError({'action':'native-probe','case_id':'X','response':response})
        with self.assertRaises(NativeActionError):runner.step(e,'native-probe',failing)
        self.assertEqual(e['steps'][0]['native_action_failure']['response'],response)
        self.assertEqual(e['steps'][0]['status'],'FAIL')
    def test_empty_semantic_snapshots_do_not_establish_audit_coverage(self):
        with self.assertRaises(AssertionError):assert_audit_semantics({'audit':[]})
