"""Complete grouped native order acceptance; expected fixture values remain assertion-only."""
import copy
import json
import re
import time
import urllib.error
from collections import Counter
from decimal import Decimal
from pathlib import Path
from run import NativeClient, REFERENCE, RANK, assert_native_economics, exception_status

ECONOMIC = ['CO00-NATIVE', 'CO01-NATIVE', 'TAX01-S-NATIVE', 'TAX01-W-NATIVE']
FLOW_CHECKS = {'create', 'create-replay', 'create-payload-conflict', 'create-functional-conflict',
               'reader-create-denied', 'foreign-create-denied', 'new-settled-denied', 'review',
               'operator-approval-denied', 'mcp-approval-denied', 'approve', 'approve-replay',
               'simulator-delivery-denied', 'mcp-delivery-denied', 'delivery-rollback', 'delivery',
               'delivery-replay', 'delivery-conflict', 'cancel-after-delivery-denied',
               'operator-settlement-denied', 'mcp-settlement-denied', 'settlement-rollback',
               'settle', 'settle-replay', 'settle-conflict', 'native-reader-order', 'native-order-crud-denied'}
GROUP_CHECKS = {
    **{case: FLOW_CHECKS | ({'prepare'} if case in ('CO01-NATIVE', 'TAX01-W-NATIVE') else set()) for case in ECONOMIC},
    'STATE01-04': {'STATE-STORE-REJECTED', 'STATE-STORE-CANCELLED', 'STATE-WEB-REJECTED', 'STATE-WEB-CANCELLED'},
    'STATE-UNKNOWN-ATOMIC': {'STATE-UNKNOWN-STORE', 'STATE-UNKNOWN-WEB'},
    'STATE-DELIVERY-WITHOUT-ACCEPTANCE': {'STORE-NEW', 'STORE-REVIEWED', 'WEB-NEW', 'WEB-REVIEWED', 'WEB-APPROVED'},
    'STATE-WEB-NO-GUIDE': {'WEB-PREPARING-NO-GUIDE'},
    'STATE-CANCEL-BEFORE-HANDOVER': {'STORE-APPROVED', 'WEB-APPROVED', 'WEB-PREPARING'},
    'INV01-03-INSUFFICIENT': {'native-stock-insufficient'},
    'VAL01-04': {'quantity-zero', 'quantity-fraction', 'quantity-negative', 'price-zero', 'price-negative', 'price-precision', 'disabled-product', 'negative-native-cost'},
}


def effects(snapshot):
    """Audit of a rejected request is durable but is not an economic side effect."""
    return {k: v for k, v in snapshot.items() if k != 'audit'}


def capture_probe(evidence, step, request, read, invoke, validate, result_key,
                  before_key='before', after_key='after'):
    """Attach the attempted probe and durable reads before checking its result."""
    if not any(existing is step for existing in evidence['steps']):
        evidence['steps'].append(step)
    step.update(status='UNRUN', executed=True, probe_request=request, probe_actor='admin')
    step[before_key] = read()
    try:
        step[result_key] = invoke()
    except Exception as error:
        step['probe_exception'] = {'type': type(error).__name__, 'error': str(error)}
        step['status'] = exception_status(error)
        raise
    finally:
        step[after_key] = read()
        step['read_boundary'] = step[after_key]['read_boundary']
    try:
        validate(step[result_key])
        assert effects(step[before_key]) == effects(step[after_key]), step['name']+': probe left domain effects after rollback'
    except Exception as error:
        step.update(status='FAIL', assertion_error=str(error))
        raise
    step['status'] = 'PASS'
    return step


def assert_initial(native, approved=False):
    assert {r['code']: Decimal(r['current_qty']) for r in native['stock']} == {'P001': Decimal(5), 'P002': Decimal(5), 'P003': Decimal(5)}
    assert sum(Decimal(r['current_qty']) * Decimal(r['avg_price']) for r in native['stock']) == Decimal(500)
    assert not native['deliveries'] and not native['invoices'] and not native['moves'], 'Premature native economic effects'
    assert len(native['sale_order_ids']) == int(approved), 'Wrong native confirmation boundary'


def assert_denied_step(step):
    name = step.get('name', 'denied-request')
    assert step['http_status'] == step['expected_http_status'], (
        f"{name}: expected HTTP {step['expected_http_status']}, observed {step['http_status']}; "
        f"native response={step['response']}")
    assert step['read_boundary'] == 'separate-http-after-business-commit-or-rollback', name+': independent rollback read missing'
    assert effects(step['before']) == effects(step['after']), 'Rejected request retained economic, key or event effects'
    old = {a['id'] for a in step['before']['audit']}
    new = [a for a in step['after']['audit'] if a['id'] not in old]
    assert len(new) == 1 and new[0]['rejected'] is True, 'Denied request must create exactly one semantic rejection'
    assert new[0]['actor'] == step['actor'] and new[0]['actor_id'] > 0 and new[0]['created_on'] not in ('null', '', 'None'), name+': denial actor/time invalid'
    assert new[0]['reason'] and new[0]['correlation'] == step['request']['request_key'] and json.loads(new[0]['beforeState']) == json.loads(new[0]['afterState']), name+': denial reason/correlation or semantic rollback invalid'
    assert step['response'].get('error'), 'Actual denial response required'


def assert_native_enum_probe(probe):
    control, invalid = probe['valid_control'], probe['invalid_attempt']
    assert control['raw_value'] == 'REVIEWED' and control['persisted_state'] == 'REVIEWED'
    assert control['persisted_native_id'] == control['model_id'] > 0
    assert control['stage'] == 'native-enum-persisted-and-reloaded' and control['diagnostic_rollback_only'] is True
    assert control['native_mapper'] == invalid['native_mapper'] == 'com.axelor.db.mapper.Mapper.set'
    assert control['enum_type'] == invalid['enum_type'] == 'com.cencomun.core.db.CcmOrderState'
    assert invalid['raw_value'] == 'UNKNOWN-LAB' and invalid['stage'] == 'native-enum-conversion'
    assert invalid['diagnostic_rollback_only'] is False and invalid['error_type'] == 'java.lang.IllegalArgumentException'
    assert 'UNKNOWN-LAB' in invalid['error'] and 'CcmOrderState' in invalid['error']
    assert any('com.axelor.db.ValueEnum.of' in frame for frame in invalid['native_stack']), 'Native enum validator causal frame required'
    assert any('com.axelor.db.mapper.' in frame for frame in invalid['native_stack'])
    assert 'persisted_state' not in invalid and 'persisted_native_id' not in invalid


def assert_native_cost_probe(probe):
    control, invalid = probe['valid_control'], probe['invalid_attempt']
    assert Decimal(control['input_cost']) == Decimal('30.00') and Decimal(invalid['input_cost']) == Decimal('-0.01')
    assert control['qty'] == invalid['qty'] == '1'
    assert control['stage'] == 'native-stock-realized-and-reloaded' and control['diagnostic_rollback_only'] is True
    assert control['planned_status'] == 2 and control['reloaded_status'] == 3
    assert len(control['reloaded_lines']) == 1
    line = control['reloaded_lines'][0]
    assert line['id'] > 0 and line['native_move_id'] == control['native_move_id'] > 0
    assert Decimal(line['qty']) == 1 and Decimal(line['unit_cost']) == 30
    assert all(control[k] == invalid[k] > 0 for k in ('company_id','warehouse_id','product_id'))
    assert invalid['diagnostic_rollback_only'] is False, 'ERP accepted negative native cost; cleanup rollback cannot count as validation'
    assert invalid['error_type'] in ('com.axelor.apps.base.AxelorException','jakarta.validation.ConstraintViolationException')
    assert invalid['stage'] in ('native-stock-line-create','native-stock-move-plan','native-stock-move-realize')
    assert re.search(r'(negative.*(?:cost|price)|(?:cost|price).*(?:negative|must be.*positive|non.?negative))', invalid['error'], re.I), 'Cost-specific native validation message required; fixture/configuration errors cannot PASS'
    assert any('com.axelor.apps.stock.' in frame for frame in invalid['native_stack']), 'Native stock validator causal frame required'
    assert invalid.get('reloaded_status') != 3


def assert_group(evidence, fixtures):
    case = evidence['case']
    assert evidence['reference'] == REFERENCE and evidence['revision'] >= (2 if case.startswith('STATE-') else 1)
    steps = evidence.get('steps', [])
    assert len({s['name'] for s in steps}) == len(steps), 'Duplicate executed subcase'
    assert {s['name'] for s in steps} == GROUP_CHECKS[case], 'Complete frozen subcase set required'
    for step in steps:
        assert step['status'] == 'PASS', step
        assert step.get('executed') is True and step.get('read_boundary') == 'separate-http-after-business-commit-or-rollback'
        if 'expected_http_status' in step:
            assert_denied_step(step)
    if case in ECONOMIC:
        indexed = {s['name']: s for s in steps}
        for name, state in [('create','NEW'),('review','REVIEWED'),('approve','APPROVED')]:
            snapshot = indexed[name]['snapshot']
            assert snapshot['order']['state'] == state
            assert_initial(snapshot['native_export'], approved=(state=='APPROVED'))
        handover = indexed['delivery']['snapshot']
        invoice = handover['native_export']['invoices'][0]
        assert len(handover['native_export']['deliveries']) == len(handover['native_export']['invoices']) == 1
        assert invoice['payments'] == [] and Decimal(invoice['amountPaid']) == 0
        assert Decimal(invoice['amountRemaining']) == Decimal(invoice['inTaxTotal'])
        assert len(handover['native_export']['moves']) == 2, 'Invoice and COGS must be committed before settlement'
        assert all(m['status'] == 3 for m in handover['native_export']['moves'])
        assert len(handover['events']) == 2
        for name in ('create-replay','approve-replay','delivery-replay','settle-replay'):
            assert indexed[name]['response']['replayed'] is True
        original = case.removesuffix('-NATIVE')
        assert_native_economics(evidence['native_export'], json.loads((fixtures / 'oracle.json').read_bytes())[original])
        final = evidence['final_snapshot']
        assert final['order']['state'] == 'SETTLED' and final['order']['creator'] == 'ccm-operator'
        assert final['order']['saleOrder_id'] == final['native_export']['sale_order_ids'][0]
        assert final['order']['delivery_id'] == final['native_export']['deliveries'][0]['id']
        assert final['order']['invoice_id'] == final['native_export']['invoices'][0]['id']
        assert [a['actor'] for a in final['audit'] if a['kind'] == 'order.transition' and not a['rejected']] == (
            ['ccm-simulator', 'ccm-simulator', 'ccm-operator', 'ccm-simulator'] if final['order']['channel'] == 'STORE'
            else ['ccm-simulator', 'ccm-simulator', 'ccm-operator', 'ccm-operator', 'ccm-simulator'])
        assert len(final['events']) == 3 and len({e['event_key'] for e in final['events']}) == 3
    elif case == 'STATE-UNKNOWN-ATOMIC':
        for step in steps:
            assert step['request']['state'] == 'UNKNOWN-LAB' and step['expected_http_status'] == 409
            assert_native_enum_probe(step['native_enum_probe'])
            assert effects(step['native_probe_before']) == effects(step['native_probe_after'])
            assert step['generic_valid_crud_denied'] and step['generic_unknown_crud_denied']
    elif case == 'STATE-DELIVERY-WITHOUT-ACCEPTANCE':
        for step in steps:
            channel, state = step['name'].split('-')
            assert step['before']['order']['state'] == state and step['before']['order']['channel'] == channel
            assert_initial(step['after']['native_export'], approved=state=='APPROVED')
    elif case == 'STATE-WEB-NO-GUIDE':
        step = steps[0]
        assert step['expected_http_status'] == 422 and step['before']['order']['state'] == 'PREPARING'
        assert not step['before']['order']['guide']; assert_initial(step['after']['native_export'],True)
    elif case == 'VAL01-04':
        cost = next(s for s in steps if s['name']=='negative-native-cost')
        assert_native_cost_probe(cost['native_result'])
        assert effects(cost['before']) == effects(cost['after'])
    return True


def review_order_group(row, evidence, fixtures):
    if row['case'] not in GROUP_CHECKS:
        return
    if evidence and row['case'] == 'STATE-CANCEL-BEFORE-HANDOVER':
        observed = [s for s in evidence.get('steps', []) if s.get('http_status') == 422
                    and s.get('response', {}).get('error_type') == 'com.axelor.apps.base.AxelorException'
                    and s.get('request', {}).get('state') == 'CANCELLED'
                    and any('SaleOrderWorkflowService' in f for f in s.get('response', {}).get('native_stack', []))]
        if observed:
            row.update(status='FAIL', complete=False, reason='Executed native service refuses required cancellation: observed functional contract failure, not environment blocker')
            return
    if evidence and evidence.get('status') == 'PASS':
        steps = evidence.get('steps', [])
        missing_controls = (row['case'] == 'STATE-UNKNOWN-ATOMIC' and any('native_enum_probe' not in s for s in steps))
        if row['case'] == 'VAL01-04':
            cost = next((s for s in steps if s.get('name') == 'negative-native-cost'), {})
            missing_controls = 'valid_control' not in cost.get('native_result', {})
        if missing_controls:
            row.update(status='UNRUN', complete=False, reason='Required native causal validator and valid control have not executed; generic CRUD/error-class evidence is insufficient')
            return
    if not evidence or evidence.get('status') != 'PASS':
        if evidence:
            row.update(status=evidence['status'], complete=False, reason=evidence.get('error', 'Executed grouped subcase failure'))
        return
    try:
        assert_group(evidence, fixtures)
    except (AssertionError, KeyError, TypeError, ValueError) as error:
        row.update(status='FAIL', complete=False, reason='Native group proof rejected: '+str(error))
    else:
        row.update(status='PASS', complete=True, observed_revision=evidence['revision'], evidence=row['case']+'.json',
                   reason='All grouped subcases executed and independently checked after commit/rollback')


class OrderCases:
    def __init__(self, admin, base, fixtures, output, rows):
        self.admin, self.base, self.fixtures, self.output, self.rows = admin, base, fixtures, output, rows
        self.templates = {r['id']: r for r in json.loads((fixtures / 'orders.json').read_bytes())}
        self.actors = {}
        self.results = []

    def actor(self, role):
        if role not in self.actors:
            c = NativeClient(self.base)
            c.login('ccm-'+role, 'CoreLab-'+role+'-2026!')
            self.actors[role] = c
        return self.actors[role]

    def snapshot(self, id):
        return self.admin.action('ccm-core-cycle-inspect', id)

    def fixture(self, id):
        self.admin.action('ccm-core-cycle-prepare', id)
        self.admin.action('ccm-core-cycle-seed', id)
        snapshot = self.snapshot(id)
        assert_initial(snapshot['native_export'])
        assert not snapshot['order'] and not snapshot['keys'] and not snapshot['events']
        return snapshot

    def payload(self, template, id, **changes):
        value = copy.deepcopy(self.templates[template])
        value.update(id=id, company_id='CCM-LAB-001', request_key=id+'-create')
        value.update(changes)
        return value

    def call(self, actor, path, body):
        c = self.actor(actor)
        try:
            response = c.request('/ws/ccm/lab/orders/'+path, body)
            return c.last_status, response
        except urllib.error.HTTPError as error:
            raw = error.read().decode(errors='replace')
            try:
                response = json.loads(raw)
            except ValueError:
                response = {'error': raw[:2200]}
            return error.code, response

    def create(self, template, id, **changes):
        self.fixture(id)
        body = self.payload(template, id, **changes)
        status, result = self.call('operator', 'create', body)
        assert status == 201 and result['state'] == 'NEW' and result['replayed'] is False, (status, result)
        snap = self.snapshot(id)
        assert_initial(snap['native_export'])
        return body, snap

    def advance(self, id, target, guide=None, **extra):
        body = {'company_id':'CCM-LAB-001','id':id,'state':target,'request_key':id+'-'+target,
                'reason':'Synthetic LAB transition to '+target}
        if guide is not None:
            body['guide'] = guide
        body.update(extra)
        role = 'operator' if target in ('PREPARING','FULFILLED','SHIPPED') else 'simulator'
        status, result = self.call(role, 'transition', body)
        assert status == 200 and result['state'] == target and result['replayed'] is False, (status, result)
        return body, result, self.snapshot(id)

    def denied(self, name, id, actor, path, body, expected):
        before = self.snapshot(id)
        status, response = self.call(actor, path, body)
        after = self.snapshot(id)
        step = {'name':name,'executed':True,'actor':'ccm-'+actor,'request':body,'http_status':status,
                'expected_http_status':expected,'response':response,'before':before,'after':after,
                'read_boundary':after['read_boundary']}
        self.last_attempt = step
        # Preserve the actual HTTP/native result before assertions can abort the group.
        try:
            assert_denied_step(step)
        except (AssertionError, KeyError, TypeError, ValueError) as error:
            step.update(status='FAIL', assertion_error=str(error))
            if getattr(self, 'active_evidence', None) is not None:
                self.active_evidence['steps'].append(step)
            raise
        step['status'] = 'PASS'
        return step

    def run_group(self, case, operation):
        start = time.perf_counter()
        evidence = {'case':case,'reference':REFERENCE,'revision':2 if case.startswith('STATE-') else 1,
                    'steps':[], 'complete':False}
        self.last_attempt = None
        self.active_evidence = evidence
        try:
            operation(evidence)
            assert_group(evidence,self.fixtures)
            evidence.update(status='PASS',complete=True)
        except NativeCancellationFailure as error:
            evidence.update(status=error.evidence['status'],complete=False,error=str(error))
        except Exception as error:
            evidence.update(status=exception_status(error),error=str(error)[:2500],error_type=type(error).__name__)
            if self.last_attempt is not None:
                evidence['last_attempt'] = self.last_attempt
        evidence['seconds'] = round(time.perf_counter()-start,3)
        (self.output/(case+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
        row=self.rows[case]
        row.update(status=evidence['status'],complete=evidence['complete'],observed_revision=evidence['revision'],
                   evidence=case+'.json',reason=evidence.get('error','All native grouped checks executed'))
        review_order_group(row,evidence,self.fixtures)
        from run import publish_complete_evidence
        publish_complete_evidence(evidence)
        self.results.append(evidence)

    @staticmethod
    def passed(name, **data):
        return {'name':name,'status':'PASS','executed':True,'read_boundary':'separate-http-after-business-commit-or-rollback',**data}

    def economic(self, evidence):
        original = evidence['case'].removesuffix('-NATIVE'); id='CYCLE-'+original
        payload,new=self.create(original,id)
        steps=evidence['steps']; steps.append(self.passed('create',snapshot=new))
        status,replay=self.call('operator','create',payload)
        assert status==200 and replay['native_id']==new['order']['native_id'] and replay['replayed'] is True
        assert effects(self.snapshot(id))==effects(new)
        steps.append(self.passed('create-replay',response=replay,snapshot=self.snapshot(id)))
        changed={**payload,'shipping_expense':'0.01'}
        steps.append(self.denied('create-payload-conflict',id,'operator','create',changed,409))
        steps.append(self.denied('create-functional-conflict',id,'operator','create',{**payload,'request_key':id+'-second'},409))
        steps.append(self.denied('reader-create-denied',id,'reader','create',payload,403))
        steps.append(self.denied('foreign-create-denied',id,'other','create',payload,403))
        settled={'company_id':'CCM-LAB-001','id':id,'state':'SETTLED','request_key':id+'-jump','reason':'Synthetic forbidden jump'}
        steps.append(self.denied('new-settled-denied',id,'simulator','transition',settled,409))
        body,result,snap=self.advance(id,'REVIEWED'); assert_initial(snap['native_export'])
        steps.append(self.passed('review',response=result,snapshot=snap))
        approval={**body,'state':'APPROVED','request_key':id+'-APPROVED','reason':'Synthetic LAB acceptance'}
        for role in ('operator','mcp'):
            steps.append(self.denied(role+'-approval-denied',id,role,'transition',approval,403))
        status,result=self.call('simulator','transition',approval); assert status==200 and result['saleOrder_status']==3
        snap=self.snapshot(id); assert_initial(snap['native_export'],True); assert len(snap['events'])==1
        steps.append(self.passed('approve',response=result,snapshot=snap))
        status,result=self.call('simulator','transition',approval); assert status==200 and result['replayed'] is True
        assert effects(snap)==effects(self.snapshot(id)); steps.append(self.passed('approve-replay',response=result,snapshot=snap))
        if payload['channel']=='WEB':
            body,result,snap=self.advance(id,'PREPARING'); assert_initial(snap['native_export'],True)
            steps.append(self.passed('prepare',response=result,snapshot=snap))
        physical='SHIPPED' if payload['channel']=='WEB' else 'FULFILLED'
        body={'company_id':'CCM-LAB-001','id':id,'state':physical,'request_key':id+'-'+physical,
              'reason':'Synthetic physical handover','guide':payload['guide']}
        for role in ('simulator','mcp'):
            steps.append(self.denied(role+'-delivery-denied',id,role,'transition',body,403))
        steps.append(self.denied('delivery-rollback',id,'operator','transition',
                                 {**body,'request_key':id+'-delivery-fault','lab_fail_after_delivery':True},503))
        status,result=self.call('operator','transition',body); assert status==200 and result['state']==physical
        snap=self.snapshot(id); assert len(snap['native_export']['deliveries'])==len(snap['native_export']['invoices'])==1
        assert {x['code']:Decimal(x['current_qty']) for x in snap['native_export']['stock']}=={'P001':Decimal(3),'P002':Decimal(4),'P003':Decimal(5)}
        steps.append(self.passed('delivery',response=result,snapshot=snap))
        status,result=self.call('operator','transition',body); assert status==200 and result['replayed'] is True
        assert effects(snap)==effects(self.snapshot(id)); steps.append(self.passed('delivery-replay',response=result,snapshot=snap))
        steps.append(self.denied('delivery-conflict',id,'operator','transition',{**body,'request_key':id+'-different-physical'},409))
        steps.append(self.denied('cancel-after-delivery-denied',id,'simulator','transition',
                                 {**body,'state':'CANCELLED','request_key':id+'-late-cancel'},409))
        settlement={**body,'state':'SETTLED','request_key':id+'-SETTLED','reason':'Synthetic settlement'}
        for role in ('operator','mcp'):
            steps.append(self.denied(role+'-settlement-denied',id,role,'transition',settlement,403))
        steps.append(self.denied('settlement-rollback',id,'simulator','transition',
                                 {**settlement,'request_key':id+'-settlement-fault','lab_fail_after_settlement':True},503))
        status,result=self.call('simulator','transition',settlement); assert status==200 and result['state']=='SETTLED'
        snap=self.snapshot(id); steps.append(self.passed('settle',response=result,snapshot=snap))
        status,result=self.call('simulator','transition',settlement); assert status==200 and result['replayed'] is True
        assert effects(snap)==effects(self.snapshot(id)); steps.append(self.passed('settle-replay',response=result,snapshot=snap))
        steps.append(self.denied('settle-conflict',id,'simulator','transition',{**settlement,'request_key':id+'-different-settlement'},409))
        found=self.actor('reader').request('/ws/rest/com.cencomun.core.db.CcmOrder/search',{
            'fields':['functionalId','state','company.code','saleOrder.id','invoice.id'],
            'data':{'criteria':[{'fieldName':'functionalId','operator':'=','value':id}]}})
        assert found['status']==0 and len(found['data'])==1 and found['data'][0]['id']==snap['order']['native_id'],found
        steps.append(self.passed('native-reader-order',response=found))
        before=self.snapshot(id)
        try:
            r=self.actor('operator').request('/ws/rest/com.cencomun.core.db.CcmOrder',{'data':{'id':snap['order']['native_id'],'state':'CANCELLED'}})
        except urllib.error.HTTPError as denied:
            assert denied.code==403; r={'http_status':denied.code,'error':denied.read().decode(errors='replace')[:1200]}
        else:
            assert r.get('status')!=0,'Generic order writes unexpectedly allowed'
        assert effects(before)==effects(self.snapshot(id))
        steps.append(self.passed('native-order-crud-denied',response=r))
        final=self.snapshot(id)
        evidence.update(native_export=final['native_export'],final_snapshot=final,
                        fixture_mapping={'functional_id':id,'fixed_fixture_id':original,'technical_alias_only':True})

    def state_exceptions(self,evidence):
        for channel in ('STORE','WEB'):
            for target in ('REJECTED','CANCELLED'):
                name='STATE-'+channel+'-'+target; id=name
                self.create('CO00' if channel=='STORE' else 'CO01',id)
                self.advance(id,'REVIEWED'); body,result,snap=self.advance(id,target)
                assert result['state']==target and not snap['events']; assert_initial(snap['native_export'])
                status,replay=self.call('simulator','transition',body)
                assert status==200 and replay['replayed'] is True and effects(snap)==effects(self.snapshot(id))
                evidence['steps'].append(self.passed(name,request=body,response=result,snapshot=snap,replay=replay))

    def unknown(self,evidence):
        for channel in ('STORE','WEB'):
            name='STATE-UNKNOWN-'+channel; id=name
            self.create('CO00' if channel=='STORE' else 'CO01',id)
            body={'company_id':'CCM-LAB-001','id':id,'state':'UNKNOWN-LAB','request_key':id+'-unknown','reason':'Synthetic unknown state'}
            step=self.denied(name,id,'simulator','transition',body,409)
            evidence['steps'].append(step)
            step['status']='UNRUN'  # This compound subcase includes native enum proof, still pending.
            # Generic CRUD rejects both valid and invalid states. It proves the guard, never enum causality.
            before=self.snapshot(id); crud={};step['generic_crud_attempts']=crud
            for state in ('REVIEWED','UNKNOWN-LAB'):
                try:
                    native=self.admin.request('/ws/rest/com.cencomun.core.db.CcmOrder',{'data':{
                        'id':before['order']['native_id'],'state':state}})
                except urllib.error.HTTPError as error:
                    native={'http_status':error.code,'error':error.read().decode(errors='replace')[:1800]}
                    crud[state]={'request':{'data':{'id':before['order']['native_id'],'state':state}},'response':native,'before':before,'after':self.snapshot(id)}
                    assert error.code in (400,403,409,422,500), f'{name}: generic CRUD unexpected HTTP {error.code}: {native}'
                else:
                    crud[state]={'request':{'data':{'id':before['order']['native_id'],'state':state}},'response':native,'before':before,'after':self.snapshot(id)}
                    assert native.get('status')!=0, f'{name}: generic CRUD write unexpectedly accepted: {native}'
                assert effects(before)==effects(crud[state]['after']), name+': generic CRUD retained domain effects'
            step.update(generic_valid_crud_denied=crud['REVIEWED'],generic_unknown_crud_denied=crud['UNKNOWN-LAB'])
            capture_probe(evidence,step,{'action':'ccm-core-cycle-enum-probe','case_id':id,
                          'control_input':'REVIEWED','invalid_input':'UNKNOWN-LAB'},
                          lambda:self.snapshot(id),lambda:self.admin.action('ccm-core-cycle-enum-probe',id),
                          assert_native_enum_probe,'native_enum_probe','native_probe_before','native_probe_after')

    def without_acceptance(self,evidence):
        for channel,states in [('STORE',['NEW','REVIEWED']),('WEB',['NEW','REVIEWED','APPROVED'])]:
            for current in states:
                name=channel+'-'+current; id='NO-ACCEPT-'+name
                self.create('CO00' if channel=='STORE' else 'CO01',id)
                for target in ['REVIEWED','APPROVED'][:0 if current=='NEW' else 1 if current=='REVIEWED' else 2]: self.advance(id,target)
                body={'company_id':'CCM-LAB-001','id':id,'state':'FULFILLED' if channel=='STORE' else 'SHIPPED',
                      'request_key':id+'-physical','reason':'Synthetic premature handover','guide':'GUIDE-LAB-001'}
                evidence['steps'].append(self.denied(name,id,'operator','transition',body,409))

    def no_guide(self,evidence):
        id='NO-GUIDE-WEB'; self.create('CO01',id,guide=None)
        for target in ('REVIEWED','APPROVED','PREPARING'):self.advance(id,target)
        body={'company_id':'CCM-LAB-001','id':id,'state':'SHIPPED','request_key':id+'-physical','reason':'Synthetic missing guide'}
        evidence['steps'].append(self.denied('WEB-PREPARING-NO-GUIDE',id,'operator','transition',body,422))

    def cancellation(self,evidence):
        failures=[]
        for channel,current in [('STORE','APPROVED'),('WEB','APPROVED'),('WEB','PREPARING')]:
            name=channel+'-'+current; id='CANCEL-'+name
            try:
                self.create('CO00' if channel=='STORE' else 'CO01',id)
                for target in ('REVIEWED','APPROVED'):self.advance(id,target)
                if current=='PREPARING':self.advance(id,'PREPARING')
                before=self.snapshot(id)
                body={'company_id':'CCM-LAB-001','id':id,'state':'CANCELLED','request_key':id+'-cancel',
                      'reason':'Synthetic cancellation from '+current+' before handover'}
                status,response=self.call('simulator','transition',body);after=self.snapshot(id)
                step={'name':name,'executed':True,'actor':'ccm-simulator','request':body,'http_status':status,
                      'response':response,'before':before,'after':after,'read_boundary':after['read_boundary']}
                if status==422 and response.get('error_type')=='com.axelor.apps.base.AxelorException' and any('SaleOrderWorkflowService' in f for f in response.get('native_stack',[])):
                    assert effects(before)==effects(after);assert_initial(after['native_export'],True)
                    step.update(status='FAIL',expected_state='CANCELLED',functional_failure=True,reason='Pinned native service rejects required cancellation of confirmed SaleOrder; expected result unchanged')
                    failures.append(step)
                else:
                    assert status==200 and after['order']['state']=='CANCELLED' and after['order']['saleOrder_status']==5,(status,response)
                    assert_initial(after['native_export'],True)
                    assert after['events']==before['events'];step['status']='PASS'
                evidence['steps'].append(step)
            except Exception as error:
                step={'name':name,'status':exception_status(error),'error':str(error)[:2200],'executed':True}
                evidence['steps'].append(step);failures.append(step)
        if failures:
            status=max((s['status'] for s in failures),key=RANK.get)
            # Preserve actual technical blocker and independent executions; never approve expected cancellation.
            evidence.update(status=status,complete=False,error='Observed functional failure of required confirmed native cancellation; three actual attempts preserved')
            raise NativeCancellationFailure(evidence)

    def insufficient(self,evidence):
        id='INV-INSUFFICIENT';payload=copy.deepcopy(self.templates['CO00']);payload['lines']=[{'product_id':'P001','qty':'6','unit_price':'50.00'}]
        self.create('CO00',id,lines=payload['lines'])
        for state in ('REVIEWED','APPROVED'):self.advance(id,state)
        step=self.denied('native-stock-insufficient',id,'operator','transition',{
            'company_id':'CCM-LAB-001','id':id,'state':'FULFILLED','request_key':id+'-physical','reason':'Synthetic insufficient stock'},422)
        assert step['response']['error_type']=='com.axelor.apps.base.AxelorException'
        assert_initial(step['after']['native_export'],True);evidence['steps'].append(step)

    def validations(self,evidence):
        for name,field,value in [('quantity-zero','qty','0'),('quantity-fraction','qty','0.5'),('quantity-negative','qty','-1'),
                                 ('price-zero','unit_price','0'),('price-negative','unit_price','-1'),('price-precision','unit_price','0.005'),
                                 ('disabled-product','product_id','P003')]:
            id='VAL-'+name.upper();self.fixture(id);body=self.payload('CO00',id);body['lines'][0][field]=value
            evidence['steps'].append(self.denied(name,id,'operator','create',body,422))
        id='VAL-NEGATIVE-NATIVE-COST';self.fixture(id)
        capture_probe(evidence,{'name':'negative-native-cost'},
                      {'action':'ccm-core-cycle-negative-cost','case_id':id,'control_input':'30.00','invalid_input':'-0.01'},
                      lambda:self.snapshot(id),lambda:self.admin.action('ccm-core-cycle-negative-cost',id),
                      assert_native_cost_probe,'native_result')


class NativeCancellationFailure(Exception):
    def __init__(self,evidence): self.evidence=evidence;super().__init__(evidence['error'])


def run_order_cases(admin,base,fixtures,output,rows):
    runner=OrderCases(admin,base,fixtures,output,rows)
    try:
        admin.action('ccm-core-cycle-actors','CYCLE')
    except Exception as error:
        for case in GROUP_CHECKS:
            evidence={'case':case,'reference':REFERENCE,'revision':2 if case.startswith('STATE-') else 1,
                      'status':exception_status(error),'complete':False,'steps':[],'error':'Native actor fixture: '+str(error)[:2000],'seconds':0}
            (output/(case+'.json')).write_text(json.dumps(evidence,indent=2)+'\n')
            rows[case].update(status=evidence['status'],complete=False,observed_revision=evidence['revision'],evidence=case+'.json',reason=evidence['error'])
            from run import publish_complete_evidence
            publish_complete_evidence(evidence);runner.results.append(evidence)
        return runner.results
    for case in ECONOMIC:runner.run_group(case,runner.economic)
    for case,operation in [('VAL01-04',runner.validations),('STATE01-04',runner.state_exceptions),
        ('INV01-03-INSUFFICIENT',runner.insufficient),('STATE-UNKNOWN-ATOMIC',runner.unknown),
        ('STATE-DELIVERY-WITHOUT-ACCEPTANCE',runner.without_acceptance),('STATE-WEB-NO-GUIDE',runner.no_guide),
        ('STATE-CANCEL-BEFORE-HANDOVER',runner.cancellation)]:runner.run_group(case,operation)
    return runner.results
