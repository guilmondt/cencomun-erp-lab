import unittest
from pathlib import Path
from finance_cases import FINANCE_CHECKS, assert_finance_group, review_finance_group, attach_check
from run import REFERENCE, verify_bundle

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'


class FinanceEvidenceRegression(unittest.TestCase):
    def test_claimed_finance_pass_without_complete_executions_is_rejected(self):
        for case in FINANCE_CHECKS:
            with self.subTest(case=case):
                row=next(dict(r,status='PASS',complete=True,observed_revision=2) for r in verify_bundle(FIXTURES)['requirements'] if r['case']==case)
                evidence={'case':case,'reference':REFERENCE,'revision':2,'status':'PASS','complete':True,'steps':[]}
                review_finance_group(row,evidence,FIXTURES);self.assertEqual(row['status'],'FAIL');self.assertFalse(row['complete'])
    def test_failed_finance_attempt_retains_actual_response_and_reads(self):
        evidence={'steps':[]};step={'name':'native-approval'}
        def check(step):
            step.update(request={'id':'PO02'},response={'error':'Native configuration failure'},http_status=422,before={'state':'PENDING'},after={'state':'PENDING'})
            raise AssertionError('expected HTTP200; actual native error')
        with self.assertRaisesRegex(AssertionError,'expected HTTP200'):
            attach_check(evidence,step,check)
        self.assertIs(evidence['steps'][0],step);self.assertEqual(step['status'],'FAIL')
        self.assertEqual(step['http_status'],422);self.assertEqual(step['before'],step['after'])
        self.assertIn('response',step);self.assertIn('request',step)
    def test_native_label_without_execution_or_commit_reads_cannot_pass(self):
        for case,names in FINANCE_CHECKS.items():
            evidence={'case':case,'reference':REFERENCE,'revision':2,'status':'PASS','steps':[{'name':n,'status':'PASS','executed':False} for n in names]}
            with self.subTest(case=case),self.assertRaises(AssertionError):assert_finance_group(evidence,FIXTURES)
