"""Six-route, stdio and server permission acceptance using actual native sessions.

Every attempt is attached before assertions. Session cookies stay in memory and
ephemeral child environments; none are persisted in evidence or command lines.
"""
import base64
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from run import REFERENCE, NativeClient, exception_status, publish_complete_evidence
from order_cases import OrderCases, effects, assert_denied_step
from finance_cases import FinanceCases
from mcp import TOOLS

BOUNDARY='separate-http-after-business-commit-or-rollback'
API_CHECKS={
 'API01-06-SIX-ROUTES': {'search','inventory','balance','cash','purchase','order','order-replay','order-conflict'},
 'IDEM01-02-CREATE-CONCURRENT': {'two-native-sessions','reader-replay-denied','different-key-conflict'},
 'PERM-API-NATIVE': {'read-matrix','create-matrix','native-extra-write-denials','private-crud','native-critical-crud','native-official-actions','reader-order'},
 'MCP01-06-STDIO': {'initialize','tools','six-complete-results','reverse-write-replays'},
 'MCP-FORBIDDEN-CRITICAL-ACTIONS': {'eligible-fixtures','eight-forbidden-tools','eight-native-denials'},
 'MCP-DENIALS-NATIVE-EFFECTS-AUDIT': {'eight-committed-denial-audits'},
}


def functional(value):return {k:v for k,v in value.items() if k not in ('_meta','replay')}


def assert_permission_denial(record, audited=True):
    assert record['http_status']==403, record['name']+': permission rejection requires HTTP403; '+str(record['response'])
    assert record['read_boundary']==BOUNDARY
    assert effects(record['before'])==effects(record['after']), record['name']+': denied operation left domain effects'
    if audited:assert_denied_step(record)


def assert_api_group(evidence, fixtures):
    case=evidence['case'];assert evidence['reference']==REFERENCE and evidence['revision']==2
    assert {s['name'] for s in evidence['steps']}==API_CHECKS[case]
    assert len(evidence['steps'])==len(API_CHECKS[case])
    for step in evidence['steps']:
        assert step.get('executed') is True and step.get('status')=='PASS', 'Unexecuted/failed API step: '+step['name']
        assert step.get('read_boundary')==BOUNDARY
    indexed={s['name']:s for s in evidence['steps']}
    if case=='API01-06-SIX-ROUTES':
        assert [r['id'] for r in indexed['search']['response']['items']]==['P001']
        inv=indexed['inventory']['response'];assert inv['on_hand']==inv['available']=='5' and inv['reserved']=='0'
        assert Decimal(inv['value'])==150 and inv['native_stock_line_id']>0
        assert indexed['balance']['response']['balances']=={'USD':'0.00'}
        assert indexed['cash']['response']['state']=='CONFIRMED'
        assert indexed['purchase']['http_status']==201 and indexed['purchase']['response']['state']=='Draft'
        assert indexed['purchase']['after']['purchase']['native_status']==1
        first=indexed['order'];replay=indexed['order-replay']
        assert first['http_status']==201 and first['response']['status']=='NEW' and not first['response']['replay']
        assert replay['http_status']==200 and replay['response']['replay'] is True
        assert functional(first['response'])==functional(replay['response'])
        assert effects(first['after'])==effects(replay['after'])
        assert indexed['order-conflict']['http_status']==409
        error=indexed['order-conflict']['response'];assert error['code']=='409' and error['message'] and error['correlation_id']
        assert not set(error)&{'native_stack','error_type'}
        assert effects(indexed['order-conflict']['before'])==effects(indexed['order-conflict']['after'])
    elif case=='IDEM01-02-CREATE-CONCURRENT':
        step=indexed['two-native-sessions'];a,b=step['responses'];assert sorted(r['http_status'] for r in (a,b))==[200,201]
        assert sorted(r['response']['replay'] for r in (a,b))==[False,True]
        assert functional(a['response'])==functional(b['response'])
        assert step['independent_authenticated_sessions']==2 and len(step['after']['keys'])==1
        assert len([a for a in step['after']['audit'] if not a['rejected']])==1
        assert not step['after']['events'] and step['after']['order']['state']=='NEW'
        assert_permission_denial(indexed['reader-replay-denied'])
        assert indexed['different-key-conflict']['http_status']==409
    elif case=='PERM-API-NATIVE':
        assert len(indexed['read-matrix']['attempts'])==7*4+3
        for r in indexed['read-matrix']['attempts']:
            assert r['http_status']==r['expected_http_status'],r
        for name in ('create-matrix','native-extra-write-denials'):
            for r in indexed[name]['attempts']:assert_permission_denial(r)
        private=indexed['private-crud']['attempts']
        assert len(private)==3*3*3, 'Three private models, three identities, three CRUD operations required'
        for r in private:
            assert r['http_status']==403, 'Private CRUD must deny with native authorization: '+str(r)
            assert effects(r['before'])==effects(r['after'])
        for name in ('native-critical-crud','native-official-actions'):
            assert indexed[name]['attempts']
            for r in indexed[name]['attempts']:
                assert r['permission_denied'] is True and effects(r['before'])==effects(r['after']),r
        assert indexed['reader-order']['response']['status']==0
        assert indexed['reader-order']['response']['data'][0]['id']==indexed['reader-order']['native_order_id']>0
    elif case=='MCP01-06-STDIO':
        assert indexed['initialize']['response']['result']['protocolVersion']=='2025-03-26'
        assert set(indexed['tools']['names'])==set(TOOLS)
        pairs=indexed['six-complete-results']['pairs'];assert {r['tool'] for r in pairs}==set(TOOLS) and len(pairs)==6
        reverse=indexed['reverse-write-replays']['pairs'];assert {r['tool'] for r in reverse}=={'createPurchaseDraft','createCasheaOrder'}
        for r in pairs+reverse:
            assert functional(r['api']['response'])==functional(r['mcp']['response']), 'Complete business result parity required'
            if r['tool'].startswith('create'):
                first,second=(r['mcp'],r['api']) if r['direction']=='MCP_then_API' else (r['api'],r['mcp'])
                assert first['http_status']==201 and first['response']['replay'] is False
                assert second['http_status']==200 and second['response']['replay'] is True
                assert first['response']['native_id']>0
                assert effects(r['after_first'])==effects(r['after_replay'])
            else:assert r['api']['http_status']==r['mcp']['http_status']==200
    elif case=='MCP-FORBIDDEN-CRITICAL-ACTIONS':
        baseline=indexed['eligible-fixtures']['baseline'];assert len(baseline)==8
        tools=indexed['eight-forbidden-tools']['attempts'];native=indexed['eight-native-denials']['attempts']
        assert len(tools)==len(native)==8 and {r['name'] for r in tools}=={r['name'] for r in native}
        for r in tools:assert r['response']['error']['code']==-32602
        for r in native:assert_permission_denial(r)
        assert baseline['approvePurchase']['purchase']['native_status']==2
        for key,state in [('deliverOrder','APPROVED'),('dispatchOrder','PREPARING'),('settleOrder','FULFILLED'),('settleWebOrder','SHIPPED')]:
            assert baseline[key]['order']['state']==state,key+': denial requires an eligible native object'
        assert baseline['confirmClosing']['cash_close']['state']=='PREPARED'
        assert baseline['authorizeRate']['date']=='2026-10-04' and baseline['authorizeRate']['rate']=='ABSENT'
        bank=baseline['reconcileBank'];assert bank['reference']=='MCP-DENY-BANK' and not bank['reconciled']
        assert Decimal(bank['amountRemainToReconcile'])==40
    elif case=='MCP-DENIALS-NATIVE-EFFECTS-AUDIT':
        records=indexed['eight-committed-denial-audits']['attempts'];assert len(records)==8
        for r in records:assert_permission_denial(r)
    return True


def review_api_group(row,evidence,fixtures):
    if row['case'] not in API_CHECKS:return
    if not evidence or evidence.get('status')!='PASS':
        if evidence:row.update(status=evidence['status'],complete=False,reason=evidence.get('error','Actual API failure'))
        return
    try:assert_api_group(evidence,fixtures)
    except (AssertionError,KeyError,TypeError,ValueError) as error:row.update(status='FAIL',complete=False,reason='API proof rejected: '+str(error))
    else:row.update(status='PASS',complete=True,observed_revision=2,evidence=row['case']+'.json',reason='Executed native identities, six routes/stdio and committed effects reviewed')


class MCPProcess:
    def __init__(self,url,client):
        env=dict(os.environ,CCM_ADAPTER_URL=url,CCM_MCP_COOKIE='; '.join(c.name+'='+c.value for c in client.cookies),
                 CCM_MCP_CSRF=next((c.value for c in client.cookies if c.name=='CSRF-TOKEN'),''))
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('mcp.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
        self.serial=0
    def rpc(self,method,params=None):
        self.serial+=1;request={'jsonrpc':'2.0','id':self.serial,'method':method,'params':params or {}}
        self.process.stdin.write(json.dumps(request)+'\n');self.process.stdin.flush()
        response=json.loads(self.process.stdout.readline());assert response['id']==self.serial,'MCP response correlation differs';return response
    def tool(self,name,args):
        response=self.rpc('tools/call',{'name':name,'arguments':args})
        if 'error' in response:return response
        body=json.loads(response['result']['content'][0]['text'])
        return {'http_status':body['status'],'response':body['result'],'mcp_response':response}
    def stop(self):
        self.process.terminate()
        try:self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait()


class ApiCases:
    def __init__(self,admin,base,fixtures,output,rows):
        self.admin,self.base,self.fixtures,self.output,self.rows=admin,base,fixtures,output,rows
        self.orders=OrderCases(admin,base,fixtures,output,rows);self.finance=FinanceCases(admin,base,fixtures,output,rows)
        self.results=[];self.denials=[];self.adapter=None;self.setup_error=None
    def actor(self,role):return self.orders.actor(role)
    def snapshot(self,id,kind='order'):
        if kind=='order':return self.orders.snapshot(id)
        value=self.finance.snapshot(id)
        # Retain actual identities for this object and a canonical digest/count of
        # all bank rows, rather than duplicating a thousand unrelated rows in
        # every role denial. Finance/concurrency acceptance exports full rows.
        bank_rows=sorted(value['bank_rows'],key=lambda row:row['native_transaction_id'])
        value['native_bank_rows_summary']={'count':len(bank_rows),'canonical_sha256':hashlib.sha256(json.dumps(bank_rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        value['bank_rows']=[row for row in bank_rows if row['reference'].startswith(id)]
        if kind=='rate':value['native_fx']=self.admin.action('ccm-core-fx-inspect','FX')
        return value
    def native_call(self,role,path,payload=None,client=None):
        c=client or self.actor(role)
        try:result=c.request(path,payload);return {'http_status':c.last_status,'response':result}
        except urllib.error.HTTPError as error:
            raw=error.read().decode(errors='replace')
            try:result=json.loads(raw)
            except ValueError:result={'error':raw[:2200]}
            return {'http_status':error.code,'response':result}
    def api(self,role,path,payload=None,key=None,client=None):
        headers={'Content-Type':'application/json'}
        if role is not None:
            c=client or self.actor(role);headers['Cookie']='; '.join(c.name+'='+c.value for c in c.cookies)
            headers['X-CSRF-Token']=next((c.value for c in c.cookies if c.name=='CSRF-TOKEN'),'')
        if key:headers['Idempotency-Key']=key
        raw=None if payload is None else json.dumps(payload).encode()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(urllib.request.Request(self.url+path,raw,headers),timeout=600) as response:return {'http_status':response.status,'response':json.load(response)}
        except urllib.error.HTTPError as error:return {'http_status':error.code,'response':json.load(error)}
    def query(self,path,**args):return path+'?'+urllib.parse.urlencode({'company_id':'CCM-LAB-001',**args})
    def step(self,evidence,name,operation):
        step={'name':name,'executed':True,'status':'UNRUN','read_boundary':BOUNDARY};evidence['steps'].append(step)
        try:operation(step);step['status']='PASS'
        except Exception as error:
            step.update(status=exception_status(error),error=str(error))
            if hasattr(error,'native_failure'):step['native_action_failure']=error.native_failure
            if isinstance(error,urllib.error.HTTPError):
                raw=error.read().decode(errors='replace');step['http_status']=error.code
                try:step['response']=json.loads(raw)
                except ValueError:step['response']={'error':raw[:3000]}
            raise
        return step
    def attempted(self,evidence,name,id,kind,role,path,payload,expected,key=None,native=False):
        def operation(step):
            step.update(actor='ccm-'+role if role else 'anonymous',request=payload,before=self.snapshot(id,kind),expected_http_status=expected)
            result=self.native_call(role,path,payload) if native else self.api(role,path,payload,key)
            step.update(result);step['after']=self.snapshot(id,kind)
            assert result['http_status']==expected,f'{name}: expected HTTP{expected}, observed {result}'
        return self.step(evidence,name,operation)
    def denial(self,evidence,name,id,kind,role,path,payload,native=True):
        record={'name':name,'actor':'ccm-'+role,'request':payload,'expected_http_status':403,'before':self.snapshot(id,kind),'read_boundary':BOUNDARY}
        evidence.setdefault('attempts',[]).append(record)
        record.update(self.native_call(role,path,payload) if native else self.api(role,path,payload,payload.get('request_key')))
        record['after']=self.snapshot(id,kind)
        try:assert_permission_denial(record);record.update(status='PASS',executed=True)
        except Exception as error:record.update(status='FAIL',executed=True,error=str(error))
        return record
    def group(self,case,operation):
        evidence={'case':case,'reference':REFERENCE,'revision':2,'complete':False,'steps':[]};self.current=evidence;start=time.perf_counter()
        try:
            if self.setup_error:raise RuntimeError('API transport fixture failed: '+self.setup_error)
            operation(evidence);assert_api_group(evidence,self.fixtures);evidence.update(status='PASS',complete=True)
        except Exception as error:evidence.update(status=exception_status(error),error=str(error)[:3000],error_type=type(error).__name__)
        evidence['seconds']=round(time.perf_counter()-start,3);self.results.append(evidence)
        (self.output/(case+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
        self.rows[case].update(status=evidence['status'],complete=evidence['complete'],observed_revision=2,evidence=case+'.json',reason=evidence.get('error','Native API runtime'))
        review_api_group(self.rows[case],evidence,self.fixtures);publish_complete_evidence(evidence)
    def start(self):
        self.adapter=subprocess.Popen([sys.executable,str(Path(__file__).with_name('adapter.py')),'--erp-base',self.base],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        info=json.loads(self.adapter.stdout.readline());self.url='http://127.0.0.1:'+str(info['listening_port'])
        assert info['routes']==6
        self.orders.fixture('API-BASE');self.warehouse='WH-LAB-001-API-BASE'
        self.admin.action('ccm-core-finance-prepare','PURCHASE')
    def six(self,e):
        reads=[('search',self.query('/products/search',q='P001')),('inventory',self.query('/inventory/P001',warehouse=self.warehouse)),('balance',self.query('/customers/C002/balance')),('cash',self.query('/cash/status',id='CS001'))]
        for name,path in reads:
            def read(step,path=path):step.update(path=path,actor='ccm-reader',**self.api('reader',path));assert step['http_status']==200,step
            self.step(e,name,read)
        po=self.finance.body('API-PO','API-PO',amount='199.99',currency='USD');po.pop('request_key');po.pop('reason')
        self.attempted(e,'purchase','API-PO','finance','operator','/purchases/drafts',po,201,'API-PO')
        order=self.orders.payload('CO00','API-CO',warehouse=self.warehouse);order.pop('request_key')
        self.attempted(e,'order','API-CO','order','operator','/cashea/orders',order,201,'API-CO')
        self.attempted(e,'order-replay','API-CO','order','operator','/cashea/orders',order,200,'API-CO')
        self.attempted(e,'order-conflict','API-CO','order','operator','/cashea/orders',{**order,'financed_amount':'74.00'},409,'API-CO')
    def concurrent(self,e):
        body=self.orders.payload('CO00','IDEM-CREATE',warehouse=self.warehouse);body.pop('request_key')
        def run(step):
            step.update(request=body,before=self.snapshot('IDEM-CREATE'),independent_authenticated_sessions=2)
            clients=[NativeClient(self.base),NativeClient(self.base)]
            for c in clients:c.login('ccm-operator','CoreLab-operator-2026!')
            with ThreadPoolExecutor(2) as pool:step['responses']=list(pool.map(lambda c:self.api('operator','/cashea/orders',body,'IDEM-CREATE',c),clients))
            step['after']=self.snapshot('IDEM-CREATE')
            assert sorted(x['http_status'] for x in step['responses'])==[200,201],step['responses']
        self.step(e,'two-native-sessions',run)
        payload={**body,'request_key':'IDEM-CREATE'}
        record=self.denial(e,'reader-replay-denied','IDEM-CREATE','order','reader','/ws/ccm/lab/orders/create',payload)
        e['steps'].append(record)
        self.attempted(e,'different-key-conflict','IDEM-CREATE','order','operator','/cashea/orders',body,409,'IDEM-CREATE-DIFFERENT')
    def permissions(self,e):
        def reads(step):
            step['attempts']=[]
            for role in ('reader','operator','buyer','manager','director','simulator','mcp'):
                for path in [self.query('/products/search',q='P001'),self.query('/inventory/P001',warehouse=self.warehouse),self.query('/customers/C002/balance'),self.query('/cash/status',id='CS001')]:
                    r={'actor':'ccm-'+role,'path':path,'expected_http_status':200,**self.api(role,path)};step['attempts'].append(r)
                    assert r['http_status']==200,r
            for role,path,status in [(None,self.query('/products/search',q='P001'),401),('other',self.query('/products/search',q='P001'),403),('reader','/products/search?company_id=OTHER-LAB&q=P001',403)]:
                r={'actor':role,'path':path,'expected_http_status':status,**self.api(role,path)};step['attempts'].append(r);assert r['http_status']==status,r
        self.step(e,'read-matrix',reads)
        def creators(step):
            step['attempts']=[]
            for role in ('reader','buyer','manager','director','simulator','other'):
                for kind,path,id in [('finance','/ws/ccm/lab/finance/purchase/create','DENY-PO-'+role.upper()),('order','/ws/ccm/lab/orders/create','DENY-ORDER-'+role.upper())]:
                    body=self.finance.body(id,'create',amount='200.00',currency='USD') if kind=='finance' else self.orders.payload('CO00',id)
                    step['attempts'].append(self.denial(e,'native-create-'+id,id,kind,role,path,body))
        self.step(e,'create-matrix',creators)
        def writes(step):
            step['attempts']=[]
            for role in ('reader','mcp','other'):
                for op,id,body in [('cash/prepare','DENY-CS-'+role.upper(),self.finance.body('DENY-CS-'+role.upper(),'prepare',observed={'USD':'100.00','VES':'4000.00','POS':'50.00','TRANSFER':'30.00'})),
                    ('bank/import','DENY-BANK-'+role.upper(),self.finance.body('DENY-BANK-'+role.upper(),'import',account='BANK-USD-001',csv_base64=base64.b64encode(b'account,date,reference,currency,amount,description\r\nBANK-USD-001,2026-10-01,DENIED,USD,40.00,Synthetic\r\n').decode())),
                    ('purchase/request','API-PO',self.finance.body('API-PO','deny-request-'+role)),('purchase/revise','API-PO',self.finance.body('API-PO','deny-revise-'+role,amount='200.01',currency='USD'))]:
                    step['attempts'].append(self.denial(e,op+'-'+role,id,'finance',role,'/ws/ccm/lab/finance/'+op,body))
        self.step(e,'native-extra-write-denials',writes)
        def private(step):
            step['attempts']=[]
            snapshots=self.snapshot('API-CO');ids={'CcmAudit':snapshots['audit'][0]['id'],'CcmRequestKey':snapshots['keys'][0]['id']}
            event_snapshot=self.snapshot('CYCLE-CO00');assert event_snapshot['events'],'An actual event is required for private outbox CRUD'
            ids['CcmOutboxEvent']=event_snapshot['events'][0]['id']
            for role in ('reader','mcp','other'):
                for model,id in ids.items():
                    for operation,path,payload in [('read','/'+str(id),None),('write','',{'data':{'id':id}}),('remove','/remove',{'records':[{'id':id}]})]:
                        before={'order':self.snapshot('API-CO'),'event_order':self.snapshot('CYCLE-CO00')}
                        r={'name':role+'-'+model+'-'+operation,'actor':'ccm-'+role,'request':payload,'before':before,'read_boundary':BOUNDARY}
                        step['attempts'].append(r);r.update(self.native_call(role,'/ws/rest/com.cencomun.core.db.'+model+path,payload))
                        r['after']={'order':self.snapshot('API-CO'),'event_order':self.snapshot('CYCLE-CO00')}
                        assert r['http_status']==403 and r['before']==r['after'],r
        self.step(e,'private-crud',private)
        po=self.snapshot('API-PO','finance')['purchase'];native_purchase=po['native_purchase_id']
        def critical(step):
            step['attempts']=[]
            for role in ('reader','mcp','other'):
                for model,id in [('com.axelor.apps.purchase.db.PurchaseOrder',native_purchase),('com.cencomun.core.db.CcmPurchase',po['native_id']),('com.cencomun.core.db.CcmOrder',self.snapshot('API-CO')['order']['native_id'])]:
                    r={'name':role+'-'+model,'actor':'ccm-'+role,'request':{'data':{'id':id,'statusSelect':3}},'before':self.snapshot('API-PO','finance'),'read_boundary':BOUNDARY};step['attempts'].append(r)
                    r.update(self.native_call(role,'/ws/rest/'+model,r['request']));r['after']=self.snapshot('API-PO','finance')
                    r['permission_denied']=r['http_status']==403
                    assert r['permission_denied'] and effects(r['before'])==effects(r['after']),r
        self.step(e,'native-critical-crud',critical)
        def official(step):
            step['attempts']=[]
            for role in ('reader','mcp','other'):
                body={'action':'action-purchase-order-method-requested','model':'com.axelor.apps.purchase.db.PurchaseOrder','data':{'context':{'id':native_purchase,'_model':'com.axelor.apps.purchase.db.PurchaseOrder'}}}
                r={'name':role+'-native-request','actor':'ccm-'+role,'request':body,'before':self.snapshot('API-PO','finance'),'read_boundary':BOUNDARY};step['attempts'].append(r)
                r.update(self.native_call(role,'/ws/action',body));r['after']=self.snapshot('API-PO','finance')
                r['permission_denied']=r['http_status']==403 or (r['response'].get('status')!=0 and any(word in json.dumps(r['response']).lower() for word in ('permission','denied','forbidden','authorization')))
                assert r['permission_denied'] and effects(r['before'])==effects(r['after']),r
        self.step(e,'native-official-actions',official)
        def order(step):
            id=self.snapshot('API-CO')['order']['native_id'];step.update(native_order_id=id,**self.native_call('reader','/ws/rest/com.cencomun.core.db.CcmOrder/'+str(id)))
            assert step['http_status']==200 and step['response']['status']==0,step
        self.step(e,'reader-order',order)
    def mcp(self,e):
        process=MCPProcess(self.url,self.actor('mcp'))
        try:
            self.step(e,'initialize',lambda step:step.update(response=process.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'ccm-core-test','version':'1.0'}})))
            def tools(step):step['response']=process.rpc('tools/list');step['names']=[t['name'] for t in step['response']['result']['tools']];assert set(step['names'])==set(TOOLS)
            self.step(e,'tools',tools)
            args=[('searchProducts',{'q':'P001'}),('getInventory',{'product_id':'P001','warehouse':self.warehouse}),('getCustomerBalance',{'customer_id':'C002'}),('getCashStatus',{'id':'CS001'}),('createPurchaseDraft',{'id':'MCP-PO','amount':'199.99','idempotency_key':'MCP-PO'}),('createCasheaOrder',{**self.orders.payload('CO00','MCP-CO',warehouse=self.warehouse),'idempotency_key':'MCP-CO'})]
            for _,arg in args:arg.pop('request_key',None);arg['company_id']='CCM-LAB-001'
            def pairs(step):
                step['pairs']=[]
                for name,arg in args:
                    method,path=TOOLS[name];api_arg={k:v for k,v in arg.items() if k not in ('product_id','customer_id','idempotency_key')}
                    path=path.replace('{product_id}','P001').replace('{customer_id}','C002');kind='finance' if name=='createPurchaseDraft' else 'order'
                    r={'tool':name,'direction':'MCP_then_API','request':arg};step['pairs'].append(r)
                    r['mcp']=process.tool(name,arg)
                    if method=='POST':r['after_first']=self.snapshot(arg['id'],kind);r['api']=self.api('mcp',path,api_arg,arg['idempotency_key']);r['after_replay']=self.snapshot(arg['id'],kind)
                    else:r['api']=self.api('mcp',path+'?'+urllib.parse.urlencode(api_arg))
                    assert r['mcp'].get('http_status') in (200,201),r
                    assert functional(r['api']['response'])==functional(r['mcp']['response']),r
            self.step(e,'six-complete-results',pairs)
            def reverse(step):
                step['pairs']=[]
                for name,arg in args[-2:]:
                    arg={**arg,'id':arg['id']+'-API-FIRST'};arg['idempotency_key']=arg['id'];_,path=TOOLS[name]
                    kind='finance' if name=='createPurchaseDraft' else 'order';body={k:v for k,v in arg.items() if k!='idempotency_key'}
                    r={'tool':name,'direction':'API_then_MCP','request':arg};step['pairs'].append(r)
                    r['api']=self.api('mcp',path,body,arg['id']);r['after_first']=self.snapshot(arg['id'],kind)
                    r['mcp']=process.tool(name,arg);r['after_replay']=self.snapshot(arg['id'],kind)
                    assert r['api']['http_status']==201 and r['mcp'].get('http_status')==200,r
            self.step(e,'reverse-write-replays',reverse)
        finally:process.stop()
    def forbidden(self,e):
        cases=[];baseline={};e['fixture_attempts']=[]
        def eligible(step):
            step['baseline']=baseline
            body=self.finance.body('MCP-PO','request');r=self.native_call('operator','/ws/ccm/lab/finance/purchase/request',body);e['fixture_attempts'].append({'request':body,**r});assert r['http_status']==200,r
            baseline['approvePurchase']=self.snapshot('MCP-PO','finance');cases.append(('approvePurchase','MCP-PO','finance','/ws/ccm/lab/finance/purchase/approve',self.finance.body('MCP-PO','mcp-deny-approve')))
            targets=[('deliverOrder','MCP-DENY-DELIVER-S','CO00',['REVIEWED','APPROVED'],'FULFILLED'),('dispatchOrder','MCP-DENY-DELIVER-W','CO01',['REVIEWED','APPROVED','PREPARING'],'SHIPPED'),('settleOrder','MCP-DENY-SETTLE-S','CO00',['REVIEWED','APPROVED','FULFILLED'],'SETTLED'),('settleWebOrder','MCP-DENY-SETTLE-W','CO01',['REVIEWED','APPROVED','PREPARING','SHIPPED'],'SETTLED')]
            for tool,id,template,states,target in targets:
                self.orders.create(template,id)
                for state in states:self.orders.advance(id,state,guide=self.orders.templates[template]['guide'])
                baseline[tool]=self.snapshot(id);cases.append((tool,id,'order','/ws/ccm/lab/orders/transition',{'company_id':'CCM-LAB-001','id':id,'state':target,'guide':self.orders.templates[template]['guide'],'request_key':id+'-mcp-deny','reason':'Synthetic permission check'}))
            body=self.finance.body('MCP-DENY-CS','prepare',observed={'USD':'100.00','VES':'4000.00','POS':'50.00','TRANSFER':'30.00'});r=self.native_call('operator','/ws/ccm/lab/finance/cash/prepare',body);e['fixture_attempts'].append({'request':body,**r});assert r['http_status']==200,r
            baseline['confirmClosing']=self.snapshot('MCP-DENY-CS','finance');cases.append(('confirmClosing','MCP-DENY-CS','finance','/ws/ccm/lab/finance/cash/confirm',self.finance.body('MCP-DENY-CS','mcp-deny-confirm',note='Synthetic permission check')))
            fx=self.admin.action('ccm-core-fx-inspect','FX');assert not any(r['from_date']=='2026-10-04' for r in fx['rates'])
            baseline['authorizeRate']={'date':'2026-10-04','rate':'ABSENT','native_fx':fx};cases.append(('authorizeRate','MCP-DENY-RATE','rate','/ws/ccm/lab/currency/authorize',self.finance.body('MCP-DENY-RATE','mcp-deny-rate',date='2026-10-04',rate='42.000000',reason='Synthetic permission check')))
            csv='account,date,reference,currency,amount,description\r\nBANK-USD-001,2026-10-01,MCP-DENY-BANK,USD,40.00,Synthetic permission check\r\n'
            body=self.finance.body('MCP-DENY-BANK','import',account='BANK-USD-001',csv_base64=base64.b64encode(csv.encode()).decode());r=self.native_call('operator','/ws/ccm/lab/finance/bank/import',body);e['fixture_attempts'].append({'request':body,**r});assert r['http_status']==200,r
            row=next(row for row in self.snapshot('MCP-DENY-BANK','finance')['bank_rows'] if row['reference']=='MCP-DENY-BANK');baseline['reconcileBank']=row
            book=self.admin.action('ccm-core-bank-book-inspect','BANK-BOOK-FIXTURE')
            # Candidate must be the fixed native AMB-BOOK-B book line, not an arbitrary eligible amount.
            voucher=next(v for v in book['vouchers'] if v['reference']=='AMB-BOOK-B')
            candidate=next(line['id'] for line in voucher['move']['lines'] if line['account']=='CCM-BANK')
            assert candidate in row['candidates'],'Fixed AMB-BOOK-B must be a native eligible unallocated candidate';e['native_bank_book']=book
            cases.append(('reconcileBank','MCP-DENY-BANK','finance','/ws/ccm/lab/finance/bank/reconcile',self.finance.body('MCP-DENY-BANK','mcp-deny-reconcile',transaction_key=row['key'],candidate_id=candidate,reason='Synthetic permission check')))
        self.step(e,'eligible-fixtures',eligible)
        process=MCPProcess(self.url,self.actor('mcp'))
        try:
            def tools(step):
                step['attempts']=[]
                for name,_,_,_,body in cases:
                    r={'name':name,'request':body,'response':process.rpc('tools/call',{'name':name,'arguments':body})};step['attempts'].append(r);assert r['response']['error']['code']==-32602,r
            self.step(e,'eight-forbidden-tools',tools)
            def native(step):
                step['attempts']=[]
                for name,id,kind,path,body in cases:
                    r=self.denial(e,name,id,kind,'mcp',path,body);step['attempts'].append(r);self.denials.append(r)
            self.step(e,'eight-native-denials',native)
        finally:process.stop()
    def denial_audit(self,e):
        def check(step):
            step['attempts']=copy.deepcopy(self.denials)
            assert len(step['attempts'])==8,'Eight actual eligible-object denials have not completed'
            for record in step['attempts']:assert_permission_denial(record)
        self.step(e,'eight-committed-denial-audits',check)
    def run(self):
        try:
            try:self.start()
            except Exception as error:self.setup_error=str(error)
            for case,op in [('API01-06-SIX-ROUTES',self.six),('IDEM01-02-CREATE-CONCURRENT',self.concurrent),('PERM-API-NATIVE',self.permissions),('MCP01-06-STDIO',self.mcp),('MCP-FORBIDDEN-CRITICAL-ACTIONS',self.forbidden),('MCP-DENIALS-NATIVE-EFFECTS-AUDIT',self.denial_audit)]:self.group(case,op)
        finally:
            if self.adapter:self.adapter.terminate();self.adapter.wait(timeout=15)
        return self.results


def run_api_cases(admin,base,fixtures,output,rows):return ApiCases(admin,base,fixtures,output,rows).run()
