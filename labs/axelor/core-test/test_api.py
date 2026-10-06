import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from adapter import ROUTES, route, normalize
from api_cases import API_CHECKS, ApiCases, assert_api_group, review_api_group, functional, BOUNDARY,native_permission_denied,assert_native_permission_denial,assert_permission_denial,native_crud_request,adapter_transport,assert_mcp_pair
from mcp import TOOLS, dispatch,adapter_arguments,call
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
    def test_native_http403_also_requires_the_specific_permission_cause(self):
        for response in ({},{'message':'Generic routing failure'},{'error':'Not Found'}):
            self.assertFalse(native_permission_denied({'http_status':403,'response':response}))
        self.assertTrue(native_permission_denied({'http_status':403,'response':{'message':'You are not authorized to remove this resource.'}}))
    def test_complete_mcp_result_still_compares_request_rate_value_and_type(self):
        first={'native_purchase_id':8,'request_rate':'0','replay':False}
        replay={**first,'request_rate':0,'replay':True}
        self.assertNotEqual(functional(first),functional(replay))
        self.assertEqual(functional(first),functional({**replay,'request_rate':'0'}))
    def test_mcp_order_replay_keeps_customer_and_the_complete_business_payload(self):
        args={'id':'MCP-CO','customer_id':'C001','company_id':'CCM-LAB-001','lines':[{'product_id':'P001','qty':'2','unit_price':'50.00'}],
              'currency':'USD','tax_rate':'0','financed_amount':'75.00','shipping_expense':'0.00','guide':None,'idempotency_key':'MCP-CO'}
        before=copy.deepcopy(args);method,path,body,key=adapter_arguments('createCasheaOrder',args)
        self.assertEqual(('POST','/cashea/orders','MCP-CO'),(method,path,key))
        self.assertEqual({k:v for k,v in args.items() if k!='idempotency_key'},body)
        self.assertEqual('C001',body['customer_id']);self.assertEqual(before,args)
    def test_get_route_consumes_only_its_actual_placeholder(self):
        method,path,body,key=adapter_arguments('getCustomerBalance',{'customer_id':'C002','company_id':'CCM-LAB-001'})
        self.assertEqual(('GET','/customers/C002/balance',{'company_id':'CCM-LAB-001'},None),(method,path,body,key))
        _,path,body,_=adapter_arguments('getInventory',{'product_id':'P001','company_id':'CCM-LAB-001','warehouse':'WH-LAB-001'})
        self.assertEqual('/inventory/P001',path);self.assertEqual({'company_id':'CCM-LAB-001','warehouse':'WH-LAB-001'},body)
    def test_native_remove_all_retains_the_real_id_and_current_version(self):
        suffix,body=native_crud_request('remove',257,0)
        self.assertEqual('/removeAll',suffix);self.assertEqual({'records':[{'id':257,'version':0}]},body)
        self.assertEqual(('/257',None),native_crud_request('read',257))
        with self.assertRaisesRegex(ValueError,'Unknown native CRUD'):native_crud_request('unknown',257)
    def test_missing_native_route_never_counts_as_authorization_denial(self):
        record={'name':'incorrect-remove-route','http_status':404,'response':{'status':-1,'data':{'title':"Erreur d'accès",'message':'Vous n’êtes pas autorisé(e) à supprimer cette ressource.'}},
                'read_boundary':BOUNDARY,'before':{'id':257},'after':{'id':257}}
        self.assertFalse(native_permission_denied(record))
        with self.assertRaisesRegex(AssertionError,'explicit native authorization rejection'):assert_native_permission_denial(record)
    def test_actual_mcp_http_request_keeps_post_body_and_header(self):
        for name,args in [('createCasheaOrder',{'id':'MCP-CO','customer_id':'C001','company_id':'CCM-LAB-001','financed_amount':'75.00','idempotency_key':'MCP-CO'}),
                          ('createPurchaseDraft',{'id':'MCP-PO','company_id':'CCM-LAB-001','amount':'199.99','idempotency_key':'MCP-PO'})]:
            response=io.BytesIO(b'{"native_id":7,"replay":false}');response.status=201
            with self.subTest(tool=name),patch.dict('os.environ',{'CCM_MCP_COOKIE':'unit-session','CCM_ADAPTER_URL':'http://unit.invalid'}),patch('mcp.urllib.request.build_opener') as build:
                build.return_value.open.return_value=response;call(name,args)
                request=build.return_value.open.call_args.args[0]
                expected=adapter_transport(name,args)
                self.assertEqual(expected['method'],request.method)
                self.assertEqual('http://unit.invalid'+expected['path'],request.full_url)
                self.assertEqual(expected['body'],json.loads(request.data))
                self.assertEqual(expected['idempotency_key'],request.get_header('Idempotency-key'))
    def test_pair_rejects_missing_customer_conflict_or_changed_result_in_both_directions(self):
        args={'id':'MCP-CO','customer_id':'C001','company_id':'CCM-LAB-001','financed_amount':'75.00','idempotency_key':'MCP-CO'}
        first={'http_status':201,'response':{'native_id':7,'customer_id':'C001','request_rate':'0','replay':False}}
        replay={'http_status':200,'response':{**first['response'],'replay':True}}
        for direction in ('MCP_then_API','API_then_MCP'):
            record={'tool':'createCasheaOrder','direction':direction,'request':args,'mcp_adapter_request':adapter_transport('createCasheaOrder',args),
                    'api_request':adapter_transport('createCasheaOrder',args),'after_first':{'id':7},'after_replay':{'id':7},
                    'mcp':first if direction=='MCP_then_API' else replay,'api':replay if direction=='MCP_then_API' else first}
            assert_mcp_pair(record)
            for kind in ('payload','conflict','result'):
                changed=copy.deepcopy(record)
                if kind=='payload':changed['api_request']['body'].pop('customer_id')
                elif kind=='conflict':changed['api' if direction=='MCP_then_API' else 'mcp']['http_status']=409
                else:changed['api']['response']['request_rate']=0
                with self.subTest(direction=direction,kind=kind),self.assertRaises(AssertionError):assert_mcp_pair(changed)
                self.assertEqual(args,changed['request']);self.assertIn('mcp',changed);self.assertIn('api',changed)
                self.assertIn('after_first',changed);self.assertIn('after_replay',changed)
