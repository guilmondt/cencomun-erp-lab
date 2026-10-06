import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from order_cases import GROUP_CHECKS, effects, assert_denied_step, review_order_group
from run import REFERENCE, verify_bundle
from extract_log_evidence import extract

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'

class OrderEvidenceRegression(unittest.TestCase):
    def row(self,case): return next(dict(r,status='PASS',complete=True,observed_revision=2) for r in verify_bundle(FIXTURES)['requirements'] if r['case']==case)
    def test_admin_economic_success_is_not_a_complete_order_group(self):
        for case in ('CO00-NATIVE','TAX01-W-NATIVE'):
            row=self.row(case)
            review_order_group(row,{'case':case,'reference':REFERENCE,'status':'PASS','complete':True,'revision':2,
                                    'steps':[],'native_export':{'administrator_gate':'PASS'}},FIXTURES)
            self.assertEqual(row['status'],'FAIL');self.assertFalse(row['complete'])
    def test_missing_revision_two_subcase_cannot_be_hidden_by_pass(self):
        case='STATE-DELIVERY-WITHOUT-ACCEPTANCE';row=self.row(case)
        steps=[{'name':name,'status':'PASS','executed':True,'read_boundary':'separate-http-after-business-commit-or-rollback'}
               for name in sorted(GROUP_CHECKS[case])[:-1]]
        review_order_group(row,{'case':case,'reference':REFERENCE,'status':'PASS','complete':True,'revision':2,'steps':steps},FIXTURES)
        self.assertEqual(row['status'],'FAIL')
    def test_denial_requires_real_error_actor_audit_and_unchanged_effects(self):
        before={'order':{'state':'APPROVED'},'native_export':{'stock':[5,5,5]},'keys':[],'events':[],'audit':[]}
        after=copy.deepcopy(before);after['audit']=[{'id':1,'actor':'ccm-mcp','actor_id':7,'created_on':'2026-10-06T10:00:00Z',
              'rejected':True,'reason':'Role denied','correlation':'key1','beforeState':'{"state":"APPROVED"}','afterState':'{"state":"APPROVED"}'}]
        step={'request':{'request_key':'key1'},'http_status':403,'expected_http_status':403,'actor':'ccm-mcp','response':{'error':'Role denied'},
              'before':before,'after':after,'read_boundary':'separate-http-after-business-commit-or-rollback'}
        assert_denied_step(step)
        for kind in ('stock','event','key','audit','actor','response','uncommitted'):
            bad=copy.deepcopy(step)
            if kind=='stock':bad['after']['native_export']['stock']=[3,4,5]
            if kind=='event':bad['after']['events']=[{'id':1}]
            if kind=='key':bad['after']['keys']=[{'id':1}]
            if kind=='audit':bad['after']['audit']=[]
            if kind=='actor':bad['after']['audit'][0]['actor']='admin'
            if kind=='response':bad['response']={}
            if kind=='uncommitted':bad['read_boundary']='same-transaction'
            with self.subTest(kind=kind),self.assertRaises(AssertionError):assert_denied_step(bad)
    def test_economic_snapshot_excludes_only_rejection_audit(self):
        self.assertEqual(effects({'native_export':{'stock':5},'audit':[]}),{'native_export':{'stock':5}})
    def test_complete_fragments_require_exact_count_unique_indices_and_hash(self):
        case='STATE-WEB-NO-GUIDE'
        item={'case':case,'reference':REFERENCE,'revision':2,'status':'FAIL','complete':False,'steps':[], 'error':'actual failed assertion'}
        raw=json.dumps(item).encode();encoded=base64.b64encode(raw).decode();parts=[encoded[:80],encoded[80:]]
        notices=[{'complete_evidence_case':case,'reference':REFERENCE,'content_sha256':hashlib.sha256(raw).hexdigest(),
                  'fragment_index':i,'fragment_count':2,'base64_fragment':part} for i,part in enumerate(parts)]
        for kind in ('valid','missing','duplicate','altered-hash'):
            selected=copy.deepcopy(notices)
            if kind=='missing':selected=selected[:1]
            if kind=='duplicate':selected[1]['fragment_index']=0
            if kind=='altered-hash':selected[1]['content_sha256']='0'*64
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp);log=path/'log';log.write_text('\n'.join('##[notice]'+json.dumps(r) for r in selected))
                result=extract(log,path/'result','123','a'*40,FIXTURES)
                row=next(r for r in result['groups'] if r['case']==case)
                self.assertEqual(row['status'],'FAIL' if kind=='valid' else 'UNRUN')
    def test_native_blocked_cancel_does_not_become_pass(self):
        case='STATE-CANCEL-BEFORE-HANDOVER';row=self.row(case)
        review_order_group(row,{'case':case,'reference':REFERENCE,'revision':2,'status':'BLOCKED','complete':False,
                               'error':'Pinned native service rejects confirmed orders','steps':[]},FIXTURES)
        self.assertEqual(row['status'],'BLOCKED');self.assertFalse(row['complete'])
