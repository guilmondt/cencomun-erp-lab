import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from order_cases import GROUP_CHECKS, effects, assert_denied_step, review_order_group, assert_native_enum_probe, assert_native_cost_probe, OrderCases
from run import REFERENCE, verify_bundle
from extract_log_evidence import extract

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'

class OrderEvidenceRegression(unittest.TestCase):
    def test_failed_http_expectation_retains_complete_attempt_before_assertion(self):
        runner=object.__new__(OrderCases)
        runner.active_evidence={'steps':[]}
        snapshots=[{'order':{'state':'APPROVED'},'audit':[],'read_boundary':'separate-http-after-business-commit-or-rollback'}]*2
        runner.snapshot=lambda _:snapshots.pop(0)
        response={'error_type':'com.axelor.apps.base.AxelorException','error':'Observed native configuration error','native_stack':['com.axelor.apps.account.Native.validate']}
        runner.call=lambda *args:(422,response)
        request={'id':'CYCLE-CO00','request_key':'delivery-fault','lab_fail_after_delivery':True}
        with self.assertRaisesRegex(AssertionError,'expected HTTP 503, observed 422'):
            runner.denied('delivery-rollback','CYCLE-CO00','operator','transition',request,503)
        attempt=runner.active_evidence['steps'][0]
        self.assertEqual(attempt['status'],'FAIL');self.assertEqual(attempt['actor'],'ccm-operator')
        self.assertEqual(attempt['request'],request);self.assertEqual(attempt['response'],response)
        self.assertIn('before',attempt);self.assertIn('after',attempt);self.assertIs(runner.last_attempt,attempt)
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

    def test_generic_crud_failure_cannot_establish_native_enum_rejection(self):
        case='STATE-UNKNOWN-ATOMIC';row=self.row(case)
        steps=[{'name':name,'status':'PASS','executed':True,'unknown_native_state_rejected':True,
                'native_unknown_attempt':{'http_status':403,'error':'Use workflow service'}} for name in GROUP_CHECKS[case]]
        review_order_group(row,{'case':case,'reference':REFERENCE,'revision':2,'status':'PASS','complete':True,'steps':steps},FIXTURES)
        self.assertEqual(row['status'],'UNRUN');self.assertFalse(row['complete'])

    def test_native_enum_cause_requires_valid_persistence_control_and_valueenum_frame(self):
        control={'raw_value':'REVIEWED','persisted_state':'REVIEWED','persisted_native_id':1,'model_id':1,
                 'stage':'native-enum-persisted-and-reloaded','diagnostic_rollback_only':True,
                 'native_mapper':'com.axelor.db.mapper.Mapper.set','enum_type':'com.cencomun.core.db.CcmOrderState'}
        invalid={'raw_value':'UNKNOWN-LAB','stage':'native-enum-conversion','diagnostic_rollback_only':False,
                 'error_type':'java.lang.IllegalArgumentException','error':'com.cencomun.core.db.CcmOrderState UNKNOWN-LAB',
                 'native_mapper':'com.axelor.db.mapper.Mapper.set','enum_type':'com.cencomun.core.db.CcmOrderState',
                 'native_stack':['com.axelor.db.ValueEnum.of(ValueEnum.java:50)','com.axelor.db.mapper.Mapper.set(Mapper.java:250)']}
        proof={'valid_control':control,'invalid_attempt':invalid};assert_native_enum_probe(proof)
        for kind in ('generic403','missing_control','missing_cause','wrong_value','no_persisted_control'):
            bad=copy.deepcopy(proof)
            if kind=='generic403':bad['invalid_attempt'].update(error_type='com.cencomun.core.CoreFault',error='Use workflow')
            if kind=='missing_control':bad['valid_control']={}
            if kind=='missing_cause':bad['invalid_attempt']['native_stack']=['com.cencomun.core.GenericGuard.save']
            if kind=='wrong_value':bad['invalid_attempt']['raw_value']='REVIEWED'
            if kind=='no_persisted_control':bad['valid_control']['stage']='native-enum-conversion'
            with self.subTest(kind=kind),self.assertRaises((AssertionError,KeyError)):assert_native_enum_probe(bad)

    def test_any_axelor_exception_is_not_a_negative_cost_validator(self):
        control={'input_cost':'30.00','qty':'1','company_id':1,'warehouse_id':4,'product_id':1,
                 'stage':'native-stock-realized-and-reloaded','diagnostic_rollback_only':True,'planned_status':2,
                 'reloaded_status':3,'native_move_id':5,'reloaded_lines':[{'id':6,'native_move_id':5,'qty':'1','unit_cost':'30.00'}]}
        invalid={'input_cost':'-0.01','qty':'1','company_id':1,'warehouse_id':4,'product_id':1,
                 'stage':'native-stock-move-realize','diagnostic_rollback_only':False,
                 'error_type':'com.axelor.apps.base.AxelorException','error':'Unit cost must be non-negative',
                 'native_stack':['com.axelor.apps.stock.service.CostValidator.validate']}
        proof={'valid_control':control,'invalid_attempt':invalid};assert_native_cost_probe(proof)
        for kind in ('sequence','address','no_control','accepted_negative','other_validator','wrong_cost'):
            bad=copy.deepcopy(proof)
            if kind=='sequence':bad['invalid_attempt']['error']='Sequence not configured'
            if kind=='address':bad['invalid_attempt']['error']='Address template missing'
            if kind=='no_control':bad['valid_control']['reloaded_status']=1
            if kind=='accepted_negative':bad['invalid_attempt']['diagnostic_rollback_only']=True
            if kind=='other_validator':bad['invalid_attempt']['native_stack']=['com.axelor.apps.base.AddressBaseRepository.save']
            if kind=='wrong_cost':bad['invalid_attempt']['input_cost']='30.00'
            with self.subTest(kind=kind),self.assertRaises(AssertionError):assert_native_cost_probe(bad)

    def test_executed_native_cancel_contract_rejection_is_functional_failure(self):
        case='STATE-CANCEL-BEFORE-HANDOVER';row=self.row(case)
        evidence={'case':case,'reference':REFERENCE,'revision':2,'status':'BLOCKED','complete':False,'steps':[
            {'name':name,'http_status':422,'request':{'state':'CANCELLED'},'response':{
                'error_type':'com.axelor.apps.base.AxelorException','native_stack':['com.axelor.apps.sale.service.saleorder.status.SaleOrderWorkflowServiceImpl.cancelSaleOrder']}}
            for name in GROUP_CHECKS[case]]}
        review_order_group(row,evidence,FIXTURES);self.assertEqual(row['status'],'FAIL');self.assertFalse(row['complete'])
