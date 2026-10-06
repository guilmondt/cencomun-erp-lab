import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from adapter import ROUTES, route, normalize
from api_cases import API_CHECKS, ApiCases, assert_api_group, review_api_group, functional, BOUNDARY,native_permission_denied,assert_native_permission_denial,assert_permission_denial
from mcp import TOOLS, dispatch
from run import REFERENCE, verify_bundle

FIXTURES=Path(__file__).resolve().parents[3]/'fixtures/ccm-core-v1'


class ApiEvidenceRegression(unittest.TestCase):
    def test_six_routes_and_stdio_tools_do_not_include_financial_writes(self):
        self.assertEqual(len(ROUTES)+2,6);self.assertEqual(len(TOOLS),6)
        for method,path in [('POST','/bank/import'),('POST','/cash/prepare'),('POST','/purchases/approve')]:
            self.assertIsNone(route(method,path))
        for name in ('approvePurchase','deliverOrder','dispatchOrder','settleOrder','settleWebOrder','confirmClosing','authorizeRate','reconcileBank'):
            with self.subTest(name=name),self.assertRaises(KeyError):dispatch({'id':1,'method':'tools/call','params':{'name':name,'arguments':{}}})
    def test_replay_normalization_keeps_all_native_identity_and_business_values(self):
        value={'id':'MCP-PO','native_id':4,'native_purchase_id':7,'state':'DRAFT','usd_base':'199.99','replayed':False}
        first=normalize('/purchases/drafts',value);second=normalize('/purchases/drafts',{**value,'replayed':True})
        self.assertEqual(functional(first),functional(second));self.assertFalse(first['replay']);self.assertTrue(second['replay'])
        self.assertEqual(first['native_purchase_id'],7)
        self.assertNotEqual(functional(first),functional({**second,'native_purchase_id':8}))
    def test_failed_api_attempt_keeps_actor_request_native_response_and_fresh_reads(self):
        runner=object.__new__(ApiCases);runner.snapshot=lambda *args:{'order':{'state':'NEW'},'audit':[],'read_boundary':BOUNDARY}
        runner.native_call=lambda *args:{'http_status':422,'response':{'error':'Specific native failure'}}
        evidence={'steps':[]};body={'id':'API-CO','request_key':'key'}
        with self.assertRaisesRegex(AssertionError,'expected HTTP403'):
            runner.attempted(evidence,'denial','API-CO','order','mcp','/native',body,403,native=True)
        step=evidence['steps'][0];self.assertEqual(step['status'],'FAIL');self.assertEqual(step['request'],body)
        self.assertEqual(step['actor'],'ccm-mcp');self.assertEqual(step['http_status'],422)
        self.assertIn('before',step);self.assertIn('after',step);self.assertIn('response',step)
    def test_labels_or_missing_executed_runtime_cannot_approve_api_mcp_security(self):
        for case,names in API_CHECKS.items():
            row=next(dict(r,status='PASS',complete=True,observed_revision=2) for r in verify_bundle(FIXTURES)['requirements'] if r['case']==case)
            evidence={'case':case,'reference':REFERENCE,'revision':2,'status':'PASS','complete':True,'steps':[]}
            review_api_group(row,evidence,FIXTURES);self.assertEqual(row['status'],'FAIL');self.assertFalse(row['complete'])
            evidence['steps']=[{'name':name,'executed':False,'status':'PASS','read_boundary':BOUNDARY} for name in names]
            with self.subTest(case=case),self.assertRaises(AssertionError):assert_api_group(evidence,FIXTURES)
    def test_mcp_parity_rejects_changed_native_fk_even_with_equal_marker(self):
        self.assertNotEqual(functional({'native_invoice_id':3,'equal':True}),functional({'native_invoice_id':4,'equal':True}))
    def test_native_rpc_denial_requires_the_explicit_pinned_permission_cause(self):
        for message in ('You are not authorized to read this resource.','Vous n’êtes pas autorisé(e) à modifier cette ressource.'):
            title='Access error' if message.startswith('You') else "Erreur d'accès"
            record={'name':'private-denial','http_status':200,'response':{'status':-1,'data':{'title':title,'message':message}},'read_boundary':BOUNDARY,'before':{'private_id':7},'after':{'private_id':7}}
            self.assertTrue(native_permission_denied(record));assert_native_permission_denial(record)
            with self.assertRaisesRegex(AssertionError,'HTTP403'):assert_permission_denial(record,audited=False)
            changed=copy.deepcopy(record);changed['after']['private_id']=8
            with self.assertRaisesRegex(AssertionError,'durable effects'):assert_native_permission_denial(changed)
    def test_generic_native_errors_or_private_data_cannot_approve_a_denial(self):
        for data in ({'title':"Erreur d'accès",'message':'No result found for query'},
                     {'message':'Pinned API signature mismatch'},
                     {'title':"Erreur d'accès",'message':'Vous n’êtes pas autorisé(e) à lire cette ressource.','id':7},
                     [{'id':7,'reason':'Private native audit'}]):
            self.assertFalse(native_permission_denied({'http_status':200,'response':{'status':-1,'data':data}}))
    def test_complete_mcp_result_still_compares_request_rate_value_and_type(self):
        first={'native_purchase_id':8,'request_rate':'0','replay':False}
        replay={**first,'request_rate':0,'replay':True}
        self.assertNotEqual(functional(first),functional(replay))
        self.assertEqual(functional(first),functional({**replay,'request_rate':'0'}))
