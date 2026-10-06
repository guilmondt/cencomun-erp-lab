"""Grouped finance acceptance with complete raw attempts retained before assertions."""
import base64
import copy
import json
import time
import urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from run import REFERENCE, NativeClient, exception_status, publish_complete_evidence, assert_native_move_scope
from order_cases import effects, assert_denied_step

FINANCE_CHECKS = {
    'PO01-09-NATIVE': {'PO'+str(i).zfill(2) for i in range(1,10)},
    'PO07-09-REVISION-SELF': {'revision-native', 'reapprove-threshold', 'self-approval-denied', 'invalid-zero', 'invalid-negative'},
    'CASH00-06-NATIVE': {'native-source-fixture', 'native-source-replay', 'CS000', 'CS001'},
    'CASH04-06-HTTP-IMMUTABLE': {'confirmed-edit-denied', 'confirmed-new-key-denied', 'denied-replay', 'crud-immutable'},
    'BANK01-05-NATIVE': {'first-import','file-replay','alternate-file','manual-probable','manual-ambiguous','bank-role-denied','negative-native'},
    'BANK-CONCURRENT-1000': {'concurrent-imports','committed-unique-1000'},
}


def attach_check(evidence, step, check):
    """This helper never discards a failed attempted operation or its raw ERP proof."""
    evidence['steps'].append(step)
    step.update(executed=True, status='UNRUN')
    try:
        check(step)
    except Exception as error:
        step.update(status=exception_status(error), assertion_error=str(error))
        raise
    step['status']='PASS'
    return step


def assert_purchase(purchase, base, native_status, actor=None):
    assert Decimal(purchase['usd_base']) == Decimal(base), 'Native purchase request-day gross conversion differs'
    assert purchase['native_id'] > 0 and purchase['native_purchase_id'] > 0 and purchase['native_company_id'] > 0
    assert purchase['native_status'] == native_status, 'Official native purchase workflow status differs'
    assert purchase['lines'] and all(l['id'] > 0 and l['native_purchase_id']==purchase['native_purchase_id'] for l in purchase['lines'])
    if actor is not None:
        assert purchase['state']=='APPROVED' and purchase['approved_by']==purchase['native_validated_by']==actor
        assert purchase['approved_at'], 'Native purchase decision time missing'


def assert_cash_source(native, fixture):
    expected={channel:sum(map(Decimal,values)) for channel,values in fixture['source_movements'].items()}
    assert {k:Decimal(v) for k,v in native['expected'].items()}==expected, 'Cash snapshot is not computed from posted native source lines'
    sources={s['channel']:s['lines'] for s in native['sources']}
    assert set(sources)==set(expected) and sum(map(len,sources.values()))==8
    for channel,rows in sources.items():
        assert Counter(Decimal(r['native_currency_amount']) for r in rows)==Counter(map(Decimal,fixture['source_movements'][channel]))
        for row in rows:
            assert row['id']>0 and row['native_move_id']==row['move']['id']>0 and row['move']['status']==3
            assert row['currency']==('VES' if channel=='VES' else 'USD')
            assert_native_move_scope(row['move'],row['move']['company_id'])
            assert sum(Decimal(l['debit'])-Decimal(l['credit']) for l in row['move']['lines'])==0
    pending=native['pending_invoice']
    assert pending['id']>0 and pending['status']==3 and pending['move']['status']==3
    assert Decimal(pending['gross'])==Decimal(pending['remaining'])==Decimal(fixture['pending_invoice']['gross'])
    assert Decimal(pending['paid'])==0 and not pending['payments'], 'Pending invoice must not enter cash'


def assert_bank_link(row):
    assert row['native_transaction_id']>0 and row['native_statement_id']>0 and row['native_bank_company_id']>0
    if row['reconciled']:
        r=row['reconciliation'];assert r['id']>0 and r['status']==2 and r['company_id']==row['native_bank_company_id']
        assert r['validated_by'] and r['validated_at'] and Decimal(row['amountRemainToReconcile'])==0
        assert row['book_line_id']==row['statement_book_line_id']>0
        assert Decimal(row['native_bank_reconciled_amount'])==Decimal(row['debit'])+Decimal(row['credit'])
        assert len(r['lines'])==1 and r['lines'][0]['is_posted'] is True
        assert r['lines'][0]['statement_line_id']==row['native_transaction_id'] and r['lines'][0]['book_line_id']==row['book_line_id']


def assert_finance_group(evidence, fixtures):
    assert evidence['reference']==REFERENCE and evidence['revision']==2
    steps=evidence['steps'];assert {s['name'] for s in steps}==FINANCE_CHECKS[evidence['case']]
    assert len(steps)==len(FINANCE_CHECKS[evidence['case']])
    for step in steps:
        assert step['executed'] is True and step['status']=='PASS', 'Unexecuted or failed finance subcase'
        assert step['read_boundary']=='separate-http-after-business-commit-or-rollback'
        for attempt in step.get('denials',[]):assert_denied_step(attempt)
    case=evidence['case'];indexed={s['name']:s for s in steps}
    if case=='PO01-09-NATIVE':
        expected=json.loads((fixtures/'purchases.json').read_bytes())+json.loads((fixtures/'scenarios.json').read_bytes())['purchases_extra']
        for item in expected:
            step=indexed[item['id']];assert step['checks']==['create','replay','request','roles','approve','replay','denied-replay']
            actor='ccm-'+item.get('required_role',item.get('role')).lower()
            expected_roles=['ccm-operator','ccm-reader','ccm-mcp','ccm-other','ccm-mcp']
            if actor in ('ccm-manager','ccm-director'):expected_roles.append('ccm-buyer')
            if actor=='ccm-director':expected_roles.append('ccm-manager')
            assert Counter(a['actor'] for a in step['denials'])==Counter(expected_roles), 'Complete purchase role and denied-replay controls required'
            assert_purchase(step['after']['purchase'],item.get('expected_base',item['amount']),3,actor)
            assert step['create_http']==201 and step['replay_http']==200 and step['replay_response']['replayed'] is True
            assert step['request_after']['purchase']['native_status']==2
            assert step['after']['purchase']['native_purchase_id']==step['create_response']['native_purchase_id']
            assert len(step['after']['events'])==1
            if item['id']=='PO07':
                assert Decimal(step['after']['purchase']['native_gross'])==200 and Decimal(step['after']['purchase']['native_tax'])==15
            if item['id'] in ('PO08','PO09'):
                purchase=step['after']['purchase'];assert purchase['currency']=='VES' and Decimal(purchase['request_rate'])==40 and purchase['request_date']=='2026-10-01'
                assert Decimal(purchase['native_gross'])==Decimal(item['amount'])
    elif case=='PO07-09-REVISION-SELF':
        revised=indexed['revision-native']['after']['purchase']
        assert_purchase(revised,'200.01',1);assert revised['state']=='DRAFT' and revised['approved_by'] is None and revised['approved_at'] is None
        assert revised['decision_revision']==2
        final=indexed['reapprove-threshold']['after']['purchase'];assert_purchase(final,'200.01',3,'ccm-manager')
        assert final['decision_revision']==2
        denial=indexed['self-approval-denied']['denials'][0]
        assert denial['actor']==denial['before']['purchase']['creator']=='ccm-selfbuyer' and denial['expected_http_status']==403
        assert Counter(a['actor'] for a in indexed['reapprove-threshold']['denials'])==Counter(['ccm-buyer'])
    elif case=='CASH00-06-NATIVE':
        fixture=json.loads((fixtures/'cash.json').read_bytes());assert_cash_source(indexed['native-source-fixture']['after']['native_cash'],fixture)
        assert indexed['native-source-fixture']['after']['native_cash']==indexed['native-source-replay']['after']['native_cash'],'Committed native cash source replay changed complete line identities or values'
        for item in fixture['cases']:
            step=indexed[item['id']];close=step['after']['cash_close'];assert close['state']=='CONFIRMED' and close['confirmed_by']=='ccm-manager' and close['confirmed_at']
            for field,expected in [('observedAmounts',item['observed']),('differences',item['differences'])]:assert {k:Decimal(v) for k,v in close[field].items()}=={k:Decimal(v) for k,v in expected.items()}
            assert close['sourceSnapshot']==indexed['native-source-fixture']['after']['native_cash'] and len(step['after']['events'])==1
            assert step['confirm_replay']['replayed'] is True and step['checks']==['prepare','prepare-replay','roles','note','confirm','confirm-replay']
            assert Counter(a['actor'] for a in step['denials'])==Counter(['ccm-operator','ccm-mcp','ccm-reader','ccm-other']+(['ccm-manager'] if item['id']=='CS001' else [])), 'Complete cash role/note controls required'
            if item['id']=='CS001':assert close['note'] and any(a['expected_http_status']==422 for a in step['denials'])
    elif case=='CASH04-06-HTTP-IMMUTABLE':
        for step in steps:assert effects(step['before'])==effects(step['after']), 'Confirmed cash changed after attempted mutation'
    elif case=='BANK01-05-NATIVE':
        first=indexed['first-import']['response'];assert (first['rows'],first['created'],first['duplicates'])==(5,4,1)
        assert [r['classification'] for r in first['results']]==['EXACT','PROBABLE','AMBIGUOUS','DUPLICATE','UNMATCHED']
        assert [r.get('reconciled',False) for r in first['results']]==[True,False,False,False,False]
        assert indexed['file-replay']['response']['replayed'] is True
        assert effects(indexed['file-replay']['before'])==effects(indexed['file-replay']['after'])
        assert (indexed['alternate-file']['response']['created'],indexed['alternate-file']['response']['duplicates'])==(0,5)
        rows={r['reference']:r for r in indexed['manual-ambiguous']['after']['bank_rows']}
        for reference,book in [('EXACT-001','EXACT-001'),('PROB-BANK-001','PROB-BOOK-001'),('AMB-BANK-001','AMB-BOOK-A')]:
            assert_bank_link(rows[reference]);assert rows[reference]['reconciled'] is True and rows[reference]['native_book_reference']==book
        assert not rows['NO-MATCH-001']['reconciled']
        negative=next(r for r in indexed['negative-native']['after']['bank_rows'] if r['reference']=='NEGATIVE-001')
        assert Decimal(negative['debit'])==10 and Decimal(negative['credit'])==0 and not negative['reconciled']
    elif case=='BANK-CONCURRENT-1000':
        results=indexed['concurrent-imports']['responses'];assert [x['http_status'] for x in results]==[200,200]
        assert sorted(x['response']['replayed'] for x in results)==[False,True]
        assert all(x['response']['created']==1000 and x['response']['rows']==1000 for x in results)
        rows=[r for r in indexed['committed-unique-1000']['after']['bank_rows'] if r['reference'].startswith('BENCH-B')]
        assert len(rows)==len({r['key'] for r in rows})==len({r['native_transaction_id'] for r in rows})==1000
        assert all(not r['reconciled'] and Decimal(r['credit'])==1 and Decimal(r['debit'])==0 for r in rows)
    return True


def review_finance_group(row,evidence,fixtures):
    if row['case'] not in FINANCE_CHECKS:return
    if not evidence or evidence.get('status')!='PASS':
        if evidence:row.update(status=evidence['status'],complete=False,reason=evidence.get('error','Actual finance failure'))
        return
    try:assert_finance_group(evidence,fixtures)
    except (AssertionError,KeyError,TypeError,ValueError) as error:row.update(status='FAIL',complete=False,reason='Finance proof rejected: '+str(error))
    else:row.update(status='PASS',complete=True,observed_revision=2,evidence=row['case']+'.json',reason='All native finance subcases checked after commit/rollback')


class FinanceCases:
    def __init__(self,admin,base,fixtures,output,rows):
        self.admin,self.base,self.fixtures,self.output,self.rows=admin,base,fixtures,output,rows
        self.clients={};self.results=[];self.setups={}
    def actor(self,role):
        if role not in self.clients:
            c=NativeClient(self.base);c.login('ccm-'+role,'CoreLab-'+role+'-2026!');self.clients[role]=c
        return self.clients[role]
    def snapshot(self,id):return self.admin.action('ccm-core-finance-inspect',id)
    def body(self,id,key,**data):return {'company_id':'CCM-LAB-001','id':id,'request_key':id+'-'+key,'reason':'Synthetic LAB '+key,**data}
    def call(self,role,path,body,client=None):
        c=client or self.actor(role)
        try:return c.request('/ws/ccm/lab/finance/'+path,body),c.last_status
        except urllib.error.HTTPError as error:
            raw=error.read().decode(errors='replace')
            try:body=json.loads(raw)
            except ValueError:body={'error':raw[:2500]}
            return body,error.code
    def attempt(self,evidence,name,id,role,path,body,expected,checks=lambda _:None):
        step={'name':name,'actor':'ccm-'+role,'request':body,'before':self.snapshot(id),'read_boundary':'separate-http-after-business-commit-or-rollback'}
        evidence['steps'].append(step);step.update(executed=True,status='UNRUN')
        try:
            response,status=self.call(role,path,body);step.update(response=response,http_status=status,after=self.snapshot(id))
            assert status==expected,f'{name}: expected HTTP {expected}, observed {status}; native response={response}'
            checks(step);step['status']='PASS'
        except Exception as error:step.update(status=exception_status(error),assertion_error=str(error));raise
        return step
    def denied(self,id,role,path,body,expected):
        before=self.snapshot(id);response,status=self.call(role,path,body);after=self.snapshot(id)
        step={'name':path+'-denied-'+role,'actor':'ccm-'+role,'request':body,'response':response,'http_status':status,'expected_http_status':expected,'before':before,'after':after,'read_boundary':after['read_boundary']}
        self.current.setdefault('attempts',[]).append(step)
        assert_denied_step(step);step.update(status='PASS',executed=True);return step
    def group(self,case,operation):
        start=time.perf_counter();evidence={'case':case,'reference':REFERENCE,'revision':2,'complete':False,'steps':[]};self.current=evidence
        try:
            scope='PURCHASE' if case.startswith('PO') else 'CASH' if case.startswith('CASH') else 'BANK'
            if scope not in self.setups:
                try:self.setups[scope]={'response':self.admin.action('ccm-core-finance-prepare',scope)}
                except Exception as error:self.setups[scope]={'error':str(error),'error_type':type(error).__name__};raise
            evidence['fixture_preparation']=self.setups[scope]
            if 'error' in self.setups[scope]:raise RuntimeError('Previous '+scope+' fixture preparation failed: '+self.setups[scope]['error'])
            operation(evidence);assert_finance_group(evidence,self.fixtures);evidence.update(status='PASS',complete=True)
        except Exception as error:
            evidence.update(status=exception_status(error),error=str(error)[:2500],error_type=type(error).__name__)
            if hasattr(error,'native_failure'):evidence['native_action_failure']=error.native_failure
            if 'scope' in locals() and scope in self.setups:evidence['fixture_preparation']=self.setups[scope]
        evidence['seconds']=round(time.perf_counter()-start,3);self.results.append(evidence)
        (self.output/(case+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
        self.rows[case].update(status=evidence['status'],complete=evidence['complete'],observed_revision=2,evidence=case+'.json',reason=evidence.get('error','Native finance group executed'))
        review_finance_group(self.rows[case],evidence,self.fixtures);publish_complete_evidence(evidence)
    def purchases(self,evidence):
        inputs=json.loads((self.fixtures/'purchases.json').read_bytes())+json.loads((self.fixtures/'scenarios.json').read_bytes())['purchases_extra']
        for item in inputs:
            id=item['id'];role=item.get('required_role',item.get('role')).lower();body=self.body(id,'create',amount=item['amount'],currency=item.get('currency','USD'))
            if 'charges' in item:body['charges']=item['charges']
            step={'name':id,'request':body,'read_boundary':'separate-http-after-business-commit-or-rollback','denials':[]}
            def check(step):
                step['create_response'],step['create_http']=self.call('operator','purchase/create',body);step['create_after']=self.snapshot(id)
                assert step['create_http']==201,f'{id}: native create failed {step["create_response"]}'
                base=Decimal(item['amount'])+sum(map(Decimal,item.get('charges',[])))
                if item.get('currency','USD')=='VES':base=Decimal('200.00') if id=='PO08' else Decimal('200.01')
                assert_purchase(step['create_after']['purchase'],base,1)
                step['replay_response'],step['replay_http']=self.call('operator','purchase/create',body);step['replay_after']=self.snapshot(id)
                assert step['replay_http']==200 and effects(step['replay_after'])==effects(step['create_after']),id+': create replay changed effects'
                request=self.body(id,'request');step['request_response'],step['request_http']=self.call('operator','purchase/request',request);step['request_after']=self.snapshot(id)
                assert step['request_http']==200,f'{id}: native request failed {step["request_response"]}'
                approve=self.body(id,'approve')
                for denied_role in ['operator','reader','mcp','other']+(['buyer'] if role in ('manager','director') else [])+(['manager'] if role=='director' else []):step['denials'].append(self.denied(id,denied_role,'purchase/approve',approve,403))
                step['response'],step['http_status']=self.call(role,'purchase/approve',approve);step['after']=self.snapshot(id)
                assert step['http_status']==200,f'{id}: native approval failed {step["response"]}'
                replay,status=self.call(role,'purchase/approve',approve);step['approval_replay']=replay;step['approval_replay_after']=self.snapshot(id)
                assert status==200 and replay['replayed'] is True and effects(step['approval_replay_after'])==effects(step['after']),id+': approval replay changed effects'
                step['denials'].append(self.denied(id,'mcp','purchase/approve',approve,403));step['checks']=['create','replay','request','roles','approve','replay','denied-replay']
            attach_check(evidence,step,check)
    def revision(self,evidence):
        body=self.body('PO02','revise',amount='200.01',currency='USD')
        self.attempt(evidence,'revision-native','PO02','operator','purchase/revise',body,200)
        request=self.body('PO02','request-revision');response,status=self.call('operator','purchase/request',request)
        evidence['revision_request']={'request':request,'response':response,'http_status':status,'after':self.snapshot('PO02')};assert status==200,'Revised purchase could not request: '+str(response)
        denial=self.denied('PO02','buyer','purchase/approve',self.body('PO02','approve-revision'),403)
        step=self.attempt(evidence,'reapprove-threshold','PO02','manager','purchase/approve',self.body('PO02','approve-revision'),200);step['denials']=[denial]
        body=self.body('PO-SELF','create',amount='50.00',currency='USD');response,status=self.call('selfbuyer','purchase/create',body);evidence['self_create']={'request':body,'response':response,'http_status':status,'after':self.snapshot('PO-SELF')};assert status==201,'Selfbuyer native create failed: '+str(response)
        response,status=self.call('selfbuyer','purchase/request',self.body('PO-SELF','request'));evidence['self_request']={'response':response,'http_status':status};assert status==200,'Selfbuyer request failed: '+str(response)
        for name,id,role,path,body in [('self-approval-denied','PO-SELF','selfbuyer','purchase/approve',self.body('PO-SELF','approve')),
             ('invalid-zero','PO-ZERO','operator','purchase/create',self.body('PO-ZERO','create',amount='0.00')),
             ('invalid-negative','PO-NEGATIVE','operator','purchase/create',self.body('PO-NEGATIVE','create',amount='-1.00'))]:
            denial=self.denied(id,role,path,body,403 if name.startswith('self') else 422)
            attach_check(evidence,{'name':name,'denials':[denial],'read_boundary':denial['read_boundary'],'after':denial['after']},lambda _:None)
    def cash(self,evidence):
        response=self.admin.action('ccm-core-finance-cash-seed','CASH');after=self.snapshot('CASH')
        attach_check(evidence,{'name':'native-source-fixture','response':response,'after':after,'read_boundary':after['read_boundary']},lambda s:assert_cash_source(s['after']['native_cash'],json.loads((self.fixtures/'cash.json').read_bytes())))
        response=self.admin.action('ccm-core-finance-cash-seed','CASH');after=self.snapshot('CASH')
        attach_check(evidence,{'name':'native-source-replay','response':response,'after':after,'read_boundary':after['read_boundary']},lambda _:None)
        for item in json.loads((self.fixtures/'cash.json').read_bytes())['cases']:
            id=item['id'];body=self.body(id,'prepare',observed=item['observed'])
            step={'name':id,'request':body,'denials':[],'read_boundary':'separate-http-after-business-commit-or-rollback'}
            def check(step):
                step['prepare_response'],step['prepare_http']=self.call('operator','cash/prepare',body);step['prepared_after']=self.snapshot(id);assert step['prepare_http']==200,f'{id}: cash prepare failed {step["prepare_response"]}'
                response,status=self.call('operator','cash/prepare',body);step['prepare_replay']=response;assert status==200 and response['replayed'] is True,'Cash prepare replay failed'
                confirm=self.body(id,'confirm')
                for role in ('operator','mcp','reader','other'):step['denials'].append(self.denied(id,role,'cash/confirm',confirm,403))
                if id=='CS001':step['denials'].append(self.denied(id,'manager','cash/confirm',confirm,422));confirm['note']='Synthetic count discrepancy per frozen fixture'
                step['response'],step['http_status']=self.call('manager','cash/confirm',confirm);step['after']=self.snapshot(id);assert step['http_status']==200,f'{id}: native-backed cash confirm failed {step["response"]}'
                response,status=self.call('manager','cash/confirm',confirm);step['confirm_replay']=response;step['replay_after']=self.snapshot(id)
                assert status==200 and response['replayed'] is True and effects(step['after'])==effects(step['replay_after']),'Cash confirm replay changed effects'
                step['checks']=['prepare','prepare-replay','roles','note','confirm','confirm-replay']
            attach_check(evidence,step,check)
    def immutable(self,evidence):
        for name,role,path,body,status in [('confirmed-edit-denied','operator','cash/prepare',self.body('CS000','edit',observed={'USD':'1.00','VES':'0.00','POS':'0.00','TRANSFER':'0.00'}),409),
           ('confirmed-new-key-denied','manager','cash/confirm',self.body('CS000','second-confirm'),409),('denied-replay','mcp','cash/confirm',self.body('CS000','confirm'),403)]:
            denial=self.denied('CS000',role,path,body,status)
            attach_check(evidence,{'name':name,'before':denial['before'],'after':denial['after'],'denials':[denial],'read_boundary':denial['read_boundary']},lambda _:None)
        before=self.snapshot('CS000');step={'name':'crud-immutable','before':before,'request':{'data':{'id':before['cash_close']['native_id'],'observedAmounts':'{}'}},'read_boundary':before['read_boundary']}
        def check(step):
            try:step['response']=self.admin.request('/ws/rest/com.cencomun.core.db.CcmCashClose',step['request']);step['http_status']=self.admin.last_status
            except urllib.error.HTTPError as error:step['http_status']=error.code;step['response']={'error':error.read().decode(errors='replace')[:2200]}
            step['after']=self.snapshot('CS000');assert step['response'].get('status')!=0,'Generic cash mutation accepted';assert effects(before)==effects(step['after']),'Confirmed cash CRUD changed effects'
        attach_check(evidence,step,check)
    def bank_body(self,id,key,csv):return self.body(id,key,account='BANK-USD-001',csv_base64=base64.b64encode(csv).decode())
    def bank(self,evidence):
        csv=(self.fixtures/'bank.csv').read_bytes();body=self.bank_body('BANK-CORE','import',csv)
        first=self.attempt(evidence,'first-import','BANK-CORE','operator','bank/import',body,200)
        replay=self.attempt(evidence,'file-replay','BANK-CORE','operator','bank/import',body,200)
        changed=csv.replace(b'Cobro ficticio exacto',b'Different synthetic description')
        self.attempt(evidence,'alternate-file','BANK-CORE-ALT','operator','bank/import',self.bank_body('BANK-CORE-ALT','import',changed),200)
        for name,reference,book in [('manual-probable','PROB-BANK-001','PROB-BOOK-001'),('manual-ambiguous','AMB-BANK-001','AMB-BOOK-A')]:
            row=next(r for r in self.snapshot('BANK-CORE')['bank_rows'] if r['reference']==reference)
            book_export=self.admin.action('ccm-core-bank-book-inspect','BANKBOOK');voucher=next(v for v in book_export['vouchers'] if v['reference']==book)
            candidate=next(l['id'] for l in voucher['move']['lines'] if l['account']=='CCM-BANK')
            request=self.body('BANK-CORE',name,transaction_key=row['key'],candidate_id=candidate)
            self.attempt(evidence,name,'BANK-CORE','manager','bank/reconcile',request,200)
        row=next(r for r in self.snapshot('BANK-CORE')['bank_rows'] if r['reference']=='NO-MATCH-001');request=self.body('BANK-CORE','forbidden-reconcile',transaction_key=row['key'],candidate_id=1)
        denial=self.denied('BANK-CORE','mcp','bank/reconcile',request,403)
        attach_check(evidence,{'name':'bank-role-denied','before':denial['before'],'after':denial['after'],'denials':[denial],'read_boundary':denial['read_boundary']},lambda _:None)
        negative=b'account,date,reference,currency,amount,description\nBANK-USD-001,2026-10-01,NEGATIVE-001,USD,-10.00,Synthetic negative sign probe\n'
        self.attempt(evidence,'negative-native','BANK-NEGATIVE','operator','bank/import',self.bank_body('BANK-NEGATIVE','import',negative),200)
    def concurrent_bank(self,evidence):
        body=self.bank_body('BANK-1000','import',(self.fixtures/'benchmark-bank.csv').read_bytes());clients=[NativeClient(self.base),NativeClient(self.base)]
        for client in clients:client.login('ccm-operator','CoreLab-operator-2026!')
        step={'name':'concurrent-imports','request':body,'read_boundary':'separate-http-after-business-commit-or-rollback'}
        def check(step):
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses=list(pool.map(lambda c:self.call('operator','bank/import',body,c),clients))
            step['responses']=[{'response':r,'http_status':s} for r,s in responses];step['after']=self.snapshot('BANK-1000')
            assert all(s==200 for _,s in responses),'Concurrent bank import failed: '+str([(s,r.get('error')) for r,s in responses])
        attach_check(evidence,step,check)
        after=self.snapshot('BANK-1000');attach_check(evidence,{'name':'committed-unique-1000','after':after,'read_boundary':after['read_boundary']},lambda _:None)


def run_finance_cases(admin,base,fixtures,output,rows):
    runner=FinanceCases(admin,base,fixtures,output,rows)
    try:admin.action('ccm-core-cycle-actors','FINANCE')
    except Exception as error:
        for case in FINANCE_CHECKS:
            evidence={'case':case,'reference':REFERENCE,'revision':2,'status':exception_status(error),'complete':False,'steps':[],'error':'Native finance configuration: '+str(error),'seconds':0}
            runner.results.append(evidence);rows[case].update(status=evidence['status'],complete=False,observed_revision=2,evidence=case+'.json',reason=evidence['error']);(output/(case+'.json')).write_text(json.dumps(evidence,indent=2)+'\n');publish_complete_evidence(evidence)
        return runner.results
    for case,operation in [('PO01-09-NATIVE',runner.purchases),('PO07-09-REVISION-SELF',runner.revision),('CASH00-06-NATIVE',runner.cash),
                           ('CASH04-06-HTTP-IMMUTABLE',runner.immutable),('BANK01-05-NATIVE',runner.bank),('BANK-CONCURRENT-1000',runner.concurrent_bank)]:runner.group(case,operation)
    return runner.results
