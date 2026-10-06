"""Native tax concurrency, semantic audit and supported runtime configuration."""
import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from run import REFERENCE, NativeClient, exception_status, publish_complete_evidence, assert_native_economics, assert_native_configuration
from order_cases import OrderCases, effects
from api_cases import ApiCases, BOUNDARY,assert_native_permission_denial

RUNTIME_CHECKS={
 'TAX02-04-IDEM-CONCURRENT': {'TAX-CONC-S','TAX-CONC-W'},
 'IDEM-TAX-NATIVE-EFFECT-COUNTS': {'two-native-tax-ledgers','create-lost-bank-counts'},
 'AUDIT01-03-NATIVE': {'semantic-native-records','authorized-manager-read','immutable-manager-edit','immutable-admin-delete'},
 'SUPPORTED-CONFIGURATION': {'native-models-repositories','native-actors-scope','versioned-native-configuration'},
}


def assert_tax_step(step,oracle):
    assert step['independent_authenticated_sessions']==2
    for operation in ('physical','settlement'):
        responses=step[operation]['responses'];assert len(responses)==2 and all(r['http_status']==200 for r in responses),responses
        assert sorted(r['response']['replayed'] for r in responses)==[False,True]
        values=[{k:v for k,v in r['response'].items() if k not in ('replayed','_meta')} for r in responses]
        assert values[0]==values[1],operation+': complete native replay differs'
        assert len(step[operation]['before']['events'])+1==len(step[operation]['after']['events'])
    assert step['conflict']['http_status']==409
    assert effects(step['conflict']['before'])==effects(step['conflict']['after'])
    final=step['settlement']['after'];assert final['order']['state']=='SETTLED'
    assert_native_economics(final['native_export'],oracle)
    assert len(final['native_export']['deliveries'])==len(final['native_export']['invoices'])==1
    assert len(final['native_export']['invoices'][0]['payments'])==2
    assert len(final['native_export']['moves'])==4 and all(m['status']==3 for m in final['native_export']['moves'])
    assert sum(e['kind']=='cashea.approved' for e in final['events'])==1


def assert_audit_semantics(native):
    rows=native['audit'];assert rows,'Actual durable native audit records required'
    kinds={r['kind'] for r in rows};assert {'order.created','order.transition','cash.confirmed','purchase.approved','purchase.revised','rate.authorized','bank.reconciled','order.denied','finance.denied','rate.denied'}<=kinds,kinds
    chains={};checked=[]
    for r in rows:
        assert r['id']>0 and r['actor_id']>0 and r['actor'] and r['object_id'] and r['occurred_at'] not in ('null','None','')
        assert r['reason'].strip() and r['correlation'],r
        before,after=json.loads(r['beforeState']),json.loads(r['afterState'])
        assert isinstance(before,dict) and before and isinstance(after,dict) and after,r['kind']+': empty semantic snapshot'
        kind=r['kind']
        if r['rejected']:
            assert before==after,r['kind']+': rejection must preserve domain snapshot'
            continue
        if kind=='order.created':
            assert before=={'exists':False} and after['state']=='NEW'
            assert after['creator']==r['actor'] and after['native_id']>0
            chains[r['object_id']]=after
        elif kind=='order.transition':
            assert before==chains[r['object_id']],'Native order audit chain does not connect'
            target=after['state'];paths={'NEW':['REVIEWED','REJECTED','CANCELLED'],'REVIEWED':['APPROVED','REJECTED','CANCELLED'],
                'APPROVED':['PREPARING','CANCELLED'] if after['channel']=='WEB' else ['FULFILLED','CANCELLED'],
                'PREPARING':['SHIPPED','CANCELLED'],'FULFILLED':['SETTLED'],'SHIPPED':['SETTLED']}
            assert target in paths[before['state']]
            if target=='APPROVED':assert after['saleOrder_id']>0 and after['saleOrder_status']==3
            if target in ('FULFILLED','SHIPPED','SETTLED'):assert after['delivery_id']>0 and after['invoice_id']>0
            chains[r['object_id']]=after
        elif kind=='purchase.approved':
            assert before['state']=='PENDING' and after['state']=='APPROVED'
            assert before['native_purchase_id']==after['native_purchase_id']>0 and Decimal(before['usd_base'])==Decimal(after['usd_base'])>0
            assert after['approved_by']==after['native_validated_by']==r['actor'] and after['approved_at']
        elif kind=='purchase.revised':
            assert before['state']=='APPROVED' and after['state']=='DRAFT'
            assert after['decision_revision']==before['decision_revision']+1
            assert Decimal(before['usd_base'])==200 and Decimal(after['usd_base'])==Decimal('200.01')
            assert after['approved_by'] is None and after['approved_at'] is None
        elif kind=='cash.confirmed':
            assert before['state']=='PREPARED' and after['state']=='CONFIRMED' and after['confirmed_by']==r['actor'] and after['confirmed_at']
            for field in ('sourceSnapshot','expectedAmounts','observedAmounts','differences'):assert before[field]==after[field]
            assert r['reason']==(after['note'] or 'Synthetic closing matches native ledger')
        elif kind=='rate.authorized':
            assert before['rate']=='ABSENT' and after['native_conversion_id']>0 and after['authorization_id']>0
            assert before['date']==after['date'] and Decimal(after['rate'])>0
        elif kind=='bank.reconciled':
            assert not before['reconciled'] and after['reconciled'] and Decimal(before['amountRemainToReconcile'])>0
            assert before['native_transaction_id']==after['native_transaction_id']>0
            assert Decimal(after['amountRemainToReconcile'])==0 and after['statement_book_line_id']==after['book_line_id']>0
            assert after['reconciliation']['validated_by']==r['actor']
        checked.append(r['id'])
    return checked


def assert_runtime_group(evidence,fixtures):
    assert evidence['reference']==REFERENCE and evidence['revision']==2
    case=evidence['case'];steps=evidence['steps'];assert {s['name'] for s in steps}==RUNTIME_CHECKS[case] and len(steps)==len(RUNTIME_CHECKS[case])
    for step in steps:assert step.get('executed') is True and step['status']=='PASS' and step['read_boundary']==BOUNDARY,step['name']
    indexed={s['name']:s for s in steps}
    if case=='TAX02-04-IDEM-CONCURRENT':
        oracle=json.loads((fixtures/'oracle.json').read_bytes())
        for id,source in [('TAX-CONC-S','TAX01-S'),('TAX-CONC-W','TAX01-W')]:assert_tax_step(indexed[id],oracle[source])
    elif case=='IDEM-TAX-NATIVE-EFFECT-COUNTS':
        oracle=json.loads((fixtures/'oracle.json').read_bytes())
        for id,source in [('TAX-CONC-S','TAX01-S'),('TAX-CONC-W','TAX01-W')]:
            r=indexed['two-native-tax-ledgers']['records'][id];assert r['replay_response']['replayed'] is True
            assert effects(r['before'])==effects(r['after']);assert_native_economics(r['after']['native_export'],oracle[source])
            n=r['after']['native_export'];assert len(n['deliveries'])==len(n['invoices'])==1 and len(n['invoices'][0]['payments'])==2
            assert sum(e['kind']=='cashea.approved' for e in r['after']['events'])==1
        counts=indexed['create-lost-bank-counts'];assert all(len(counts['native']['order_counts'][id])==1 for id in ('IDEM-CREATE','IDEM-LOST'))
        rows=[r for r in counts['bank']['bank_rows'] if r['reference'].startswith('BENCH-B')]
        assert len(rows)==len({r['native_transaction_id'] for r in rows})==len({r['key'] for r in rows})==1000
    elif case=='AUDIT01-03-NATIVE':
        step=indexed['semantic-native-records'];assert step['checked_ids']==assert_audit_semantics(step['native'])
        read=indexed['authorized-manager-read'];assert read['http_status']==200 and read['response']['status']==0,'Manager audit read control must succeed'
        row=read['response']['data'][0];assert row['id']==read['native_audit_id']>0 and row['company']['id']==step['native']['company_id'],'Native audit read control must retain its ID and company'
        for name in ('immutable-manager-edit','immutable-admin-delete'):
            r=indexed[name];assert_native_permission_denial(r);assert r['before']==r['after'],name+': immutable native audit changed'
    elif case=='SUPPORTED-CONFIGURATION':
        native=indexed['native-models-repositories']['native'];assert native['core_lab_enabled'] is True
        assert len(native['models'])==11 and all(m['orm_entity'] is True and m['class'].startswith('com.cencomun.core.db.') for m in native['models'])
        assert all('WorkflowRepository' in m['repository'] for m in native['models'] if m['class'].rsplit('.',1)[-1] in ('CcmOrder','CcmOrderLine','CcmPurchase','CcmCashClose','CcmBankImport','CcmBankRow','CcmAudit','CcmRequestKey','CcmOutboxEvent'))
        actors=indexed['native-actors-scope']['native']['actors'];assert len(actors)==9
        for actor in actors:
            assert actor['id']>0 and actor['roles'] and actor['companies']==[actor['active_company']]
            assert actor['active_company']==('OTHER-LAB' if actor['code']=='ccm-other' else 'CCM-LAB-001')
        assert_native_configuration(indexed['versioned-native-configuration']['native']['fixture_configuration'])
    return True


def review_runtime_group(row,evidence,fixtures):
    if row['case'] not in RUNTIME_CHECKS:return
    if not evidence or evidence.get('status')!='PASS':
        if evidence:row.update(status=evidence['status'],complete=False,reason=evidence.get('error','Actual native observation failed'))
        return
    try:assert_runtime_group(evidence,fixtures)
    except (AssertionError,KeyError,TypeError,ValueError) as error:row.update(status='FAIL',complete=False,reason='Native observation proof rejected: '+str(error))
    else:row.update(status='PASS',complete=True,observed_revision=2,evidence=row['case']+'.json',reason='Executed native concurrency/audit/configuration reads checked')


class RuntimeCases(ApiCases):
    def group(self,case,operation):
        start=time.perf_counter();e={'case':case,'reference':REFERENCE,'revision':2,'complete':False,'steps':[]};self.current=e
        try:operation(e);assert_runtime_group(e,self.fixtures);e.update(status='PASS',complete=True)
        except Exception as error:e.update(status=exception_status(error),error=str(error)[:3000],error_type=type(error).__name__)
        e['seconds']=round(time.perf_counter()-start,3);self.results.append(e);(self.output/(case+'.json')).write_text(json.dumps(e,indent=2)+'\n')
        self.rows[case].update(status=e['status'],complete=e['complete'],observed_revision=2,evidence=case+'.json',reason=e.get('error','Native observation execution'))
        review_runtime_group(self.rows[case],e,self.fixtures);publish_complete_evidence(e)
    def audit_snapshot(self):return self.admin.action('ccm-core-audit-inspect','AUDIT')
    def tax(self,e):
        errors=[]
        for id,source in [('TAX-CONC-S','TAX01-S'),('TAX-CONC-W','TAX01-W')]:
            def cycle(step,id=id,source=source):
                self.orders.create(source,id);self.orders.advance(id,'REVIEWED');self.orders.advance(id,'APPROVED')
                template=self.orders.templates[source];physical='SHIPPED' if template['channel']=='WEB' else 'FULFILLED'
                if physical=='SHIPPED':self.orders.advance(id,'PREPARING')
                step.update(fixed_fixture=source,independent_authenticated_sessions=2)
                for op,target,role in [('physical',physical,'operator'),('settlement','SETTLED','simulator')]:
                    body={'company_id':'CCM-LAB-001','id':id,'state':target,'guide':template['guide'],'request_key':id+'-'+target,'reason':'Synthetic concurrent '+target}
                    record={'request':body,'actor':'ccm-'+role,'before':self.snapshot(id)};step[op]=record
                    clients=[NativeClient(self.base),NativeClient(self.base)]
                    for c in clients:c.login('ccm-'+role,'CoreLab-'+role+'-2026!')
                    with ThreadPoolExecutor(2) as pool:record['responses']=list(pool.map(lambda c:self.native_call(role,'/ws/ccm/lab/orders/transition',body,c),clients))
                    record['after']=self.snapshot(id)
                    assert all(r['http_status']==200 for r in record['responses']),record['responses']
                    if op=='physical':
                        conflict_body={**body,'request_key':id+'-different-physical'}
                        step['conflict']={'request':conflict_body,'before':self.snapshot(id),**self.native_call(role,'/ws/ccm/lab/orders/transition',conflict_body)};step['conflict']['after']=self.snapshot(id)
                assert_tax_step(step,json.loads((self.fixtures/'oracle.json').read_bytes())[source])
            try:self.step(e,id,cycle)
            except Exception as error:errors.append(id+': '+str(error))
        assert not errors,'; '.join(errors)
    def counts(self,e):
        def ledgers(step):
            step['records']={}
            for id in ('TAX-CONC-S','TAX-CONC-W'):
                body={'company_id':'CCM-LAB-001','id':id,'state':'SETTLED','guide':self.orders.templates['TAX01-S' if id.endswith('S') else 'TAX01-W']['guide'],'request_key':id+'-SETTLED','reason':'Synthetic concurrent SETTLED'}
                r={'request':body,'before':self.snapshot(id)};step['records'][id]=r;r.update(self.native_call('simulator','/ws/ccm/lab/orders/transition',body));r['replay_response']=r['response'];r['after']=self.snapshot(id);assert r['http_status']==200,r
        self.step(e,'two-native-tax-ledgers',ledgers)
        self.step(e,'create-lost-bank-counts',lambda step:step.update(native=self.audit_snapshot(),bank=self.finance.snapshot('BANK-CONCURRENT')))
    def audits(self,e):
        def semantic(step):step['native']=self.audit_snapshot();step['checked_ids']=assert_audit_semantics(step['native'])
        self.step(e,'semantic-native-records',semantic)
        id=self.audit_snapshot()['audit'][0]['id'];path='/ws/rest/com.cencomun.core.db.CcmAudit'
        self.step(e,'authorized-manager-read',lambda step:step.update(native_audit_id=id,**self.native_call('manager',path+'/'+str(id))))
        for name,role,url,body in [('immutable-manager-edit','manager',path,{'data':{'id':id,'reason':'Attempt overwrite'}}),('immutable-admin-delete','admin',path+'/remove',{'records':[{'id':id}]})]:
            def operation(step,role=role,url=url,body=body):
                step.update(actor=role,request=body,before=self.audit_snapshot())
                step.update(self.native_call(role,url,body,self.admin if role=='admin' else None));step['after']=self.audit_snapshot()
                assert_native_permission_denial(step);assert step['before']==step['after'],step['name']+': immutable native audit changed'
            self.step(e,name,operation)
    def configuration(self,e):
        self.step(e,'native-models-repositories',lambda step:step.update(native=self.audit_snapshot()))
        self.step(e,'native-actors-scope',lambda step:step.update(native=self.audit_snapshot()))
        self.step(e,'versioned-native-configuration',lambda step:step.update(native=self.admin.action('ccm-core-native-inspect','CO00')))


def run_tax_cases(admin,base,fixtures,output,rows):
    runner=RuntimeCases(admin,base,fixtures,output,rows);runner.group('TAX02-04-IDEM-CONCURRENT',runner.tax);return runner.results


def run_audit_cases(admin,base,fixtures,output,rows):
    runner=RuntimeCases(admin,base,fixtures,output,rows)
    for case,operation in [('IDEM-TAX-NATIVE-EFFECT-COUNTS',runner.counts),('AUDIT01-03-NATIVE',runner.audits),('SUPPORTED-CONFIGURATION',runner.configuration)]:runner.group(case,operation)
    return runner.results
