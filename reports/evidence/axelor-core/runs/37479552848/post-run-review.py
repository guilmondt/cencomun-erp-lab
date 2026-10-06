"""Review complete CI24 files with its frozen code; write a small derived receipt."""
import sys,json,hashlib,copy,subprocess
from pathlib import Path
from collections import Counter
repo=Path(__file__).resolve().parents[5];root=Path(__file__).resolve().parent;frozen=Path(sys.argv[1]).resolve();sys.path.insert(0,str(frozen))
from evidence_index import load_index
from repeat import assert_repeat_contents
from run import criteria_for,review_native_fx,review_native_fixture
from order_cases import GROUP_CHECKS,review_order_group
from finance_cases import FINANCE_CHECKS,review_finance_group
from api_cases import API_CHECKS,review_api_group,native_permission_denied,functional,assert_mcp_pair,native_admin_immutable_denied
from audit_cases import RUNTIME_CHECKS,review_runtime_group
from recovery_cases import RECOVERY_CHECKS,review_recovery_group
fixtures=repo/'fixtures/ccm-core-v1';index=json.loads((root/'isolated-repeat.json').read_bytes());payload,loaded=load_index(index,root)
receipt=json.loads((root/'evidence-source.json').read_bytes());sha=receipt['lab_commit'];assert sha==(frozen/'lab-commit').read_text().strip()
result={'run_id':receipt['run_id'],'lab_commit':sha,'reference':payload['reference'],'loaded_original_files':loaded,'phases':{}}
for phase in ['primary','repeat']:
 original=payload[phase];assert original['build_evidence']['lab_commit']==sha,'Build attestation must belong to actual executed SHA';rows=copy.deepcopy(original['coverage']['groups']);checks={}
 roles={e['role']:e for e in index['phases'][phase]['files'] if e.get('role')}
 for row in rows:
  evidence=original['groups'][row['case']]
  for family,review in [(GROUP_CHECKS,review_order_group),(FINANCE_CHECKS,review_finance_group),(API_CHECKS,review_api_group),(RUNTIME_CHECKS,review_runtime_group),(RECOVERY_CHECKS,review_recovery_group)]:
   if row['case'] in family:review(row,evidence,fixtures)
  if row['case']=='FX01-03-MONEY01-03':review_native_fx(row,evidence,json.loads((fixtures/'fx.json').read_bytes()))
  if row['case']=='FIXTURE-HASH-NATIVE-EXPORT':review_native_fixture(row,evidence,fixtures)
  row['evidence']=roles['group:'+row['case']]['path']
 statuses={r['case']:r['status'] for r in rows}
 def case(name):return original['groups'][name]
 def group(name,detail):return {'derived_status':statuses[name],'complete_original':roles['group:'+name],**detail}
 tax=case('TAX02-04-IDEM-CONCURRENT');tax_detail=[]
 for step in tax['steps']:
  item={'case':step['name'],'step_status':step['status']}
  for action in ['physical','settlement']:
   if action in step:
    a=step[action];item[action]={'http_statuses':[r['http_status'] for r in a.get('responses',[])],
      'replayed':[r.get('response',{}).get('replayed') for r in a.get('responses',[])],
      'durable_order':a.get('after',{}).get('order'),'keys_after':len(a.get('after',{}).get('keys',[])),
      'events_after':len(a.get('after',{}).get('events',[]))}
  tax_detail.append(item)
 checks['tax_concurrency']=group('TAX02-04-IDEM-CONCURRENT',{'actual_sessions_and_durable_reads':tax_detail})
 bank=original['benchmark'];checks['benchmark']={'observed_status':bank['status'],'original':roles['benchmark'],
   'samples_including_warmup':len(bank['rows']),'loaded_counts':bank.get('loaded',{}).get('counts'),'operations':bank['operations'],'error':bank.get('error')}
 perm=case('PERM-API-NATIVE');permission_steps={}
 for step in perm['steps']:
  if step['name'] not in ['private-crud','native-critical-crud','native-official-actions']:continue
  attempts=step.get('attempts',[]);permission_steps[step['name']]={'actual_attempts':len(attempts),'step_status':step['status'],
    'explicit_native_authorization_causes':sum(native_permission_denied(a) for a in attempts),
    'native_http_protocol_counts':dict(Counter(str(a.get('http_status'))+'/'+str(a.get('response',{}).get('status')) for a in attempts)),
    'actual_remove_paths':[{'actor':a['actor'],'path':a['path'],'request':a['request'],'causal_rejection':native_permission_denied(a)} for a in attempts if a.get('operation')=='remove']}
 checks['private_permissions']=group('PERM-API-NATIVE',{'steps':permission_steps,'adapter_403_contract_unchanged':True})
 audits=case('AUDIT01-03-NATIVE');checks['audit']=group('AUDIT01-03-NATIVE',{'steps':[{k:s.get(k) for k in ['name','status','http_status','error']} for s in audits['steps']]})
 admin_attempt=next((step for step in audits.get('steps',[]) if step.get('name')=='immutable-admin-delete'),None)
 if admin_attempt:
  diagnostic=admin_attempt.get('response',{}).get('data',{})
  checks['audit']['administrator_immutable']={'exact_scoped_cause_accepted':native_admin_immutable_denied(admin_attempt),'actor':admin_attempt.get('actor'),'path':admin_attempt.get('path'),'request':admin_attempt.get('request'),'http_status':admin_attempt.get('http_status'),'native_status':admin_attempt.get('response',{}).get('status'),'causeClass':diagnostic.get('causeClass'),'causeString':diagnostic.get('causeString'),'message':diagnostic.get('message'),'stack_sha256':hashlib.sha256(diagnostic.get('causeStack','').encode()).hexdigest(),'public_java_frames':len(diagnostic.get('causeStack','').splitlines())-1,'full_snapshots_identical':admin_attempt.get('before')==admin_attempt.get('after')}
 events=case('IDEM04-EVENTS-RECOVERY');event_steps={step['name']:step for step in events.get('steps',[])};event_summary={}
 for name,step in event_steps.items():
  response=step.get('native_response',{});consumer=step.get('consumer',{});receipts=consumer.get('receipts',[]);effects=consumer.get('effects',[])
  event_summary[name]={'step_status':step.get('status'),'native_http_status':step.get('native_http_status'),'delivered':response.get('delivered'),'failed':response.get('failed'),'native_attempts':len(response.get('attempts',[])),'actual_503_without_transport_error':sum(a.get('http_status')==503 and not a.get('error') for a in response.get('attempts',[])),'delivery_statuses':dict(Counter(str(a.get('http_status')) for a in response.get('attempts',[]))),'transport_errors':[{'event_id':a.get('event_id'),'error':a.get('error')} for a in response.get('attempts',[]) if a.get('error')],'consumer_receipts':len(receipts),'consumer_effects':len(effects),'consumer_delivery_counts':dict(Counter(str(a.get('deliveries')) for a in receipts)),'effect_application_counts':dict(Counter(str(a.get('applications')) for a in effects)),'native_pending':sum(not a.get('delivered') for a in step.get('native_after',[])),'native_attempt_counts':dict(Counter(str(a.get('attempts')) for a in step.get('native_after',[]))),'pid_before':step.get('pid_before'),'pid_after':step.get('pid_after'),'restart_snapshots_identical':step.get('before')==step.get('after') if name=='consumer-restart' else None}
 checks['event_recovery']=group('IDEM04-EVENTS-RECOVERY',{'steps':event_summary,'consumer_processes':events.get('consumer_processes',[]),'complete_four_steps_executed':set(event_steps)==RECOVERY_CHECKS['IDEM04-EVENTS-RECOVERY'],'error':events.get('error')})
 if statuses['IDEM04-EVENTS-RECOVERY']=='PASS':
  assert event_summary['consumer-503']['actual_503_without_transport_error']==42,'Both phases must demonstrate42actual503 responses'
  for name in ['first-delivery','durable-event-replay']:
   assert event_summary[name]['delivered']==event_summary[name]['consumer_receipts']==event_summary[name]['consumer_effects']==42,'Both phases require42deliveries,receipts,effects'
   assert event_summary[name]['failed']==0 and not event_summary[name]['transport_errors'],'No mapped/hidden transport exception allowed'
  assert event_summary['consumer-restart']['pid_before']!=event_summary['consumer-restart']['pid_after'] and event_summary['consumer-restart']['restart_snapshots_identical']
  assert event_summary['durable-event-replay']['consumer_delivery_counts']=={'2':42} and event_summary['durable-event-replay']['effect_application_counts']=={'1':42} and event_summary['durable-event-replay']['native_attempt_counts']=={'3':42}
 cash=case('CASH00-06-NATIVE');checks['cash']=group('CASH00-06-NATIVE',{'steps':[{k:s.get(k) for k in ['name','status','error']} for s in cash['steps']]})
 mcp=case('MCP01-06-STDIO');pairs=[]
 for step in mcp['steps']:
  for p in step.get('pairs',[]):
   a=p.get('api',{}).get('response',{});b=p.get('mcp',{}).get('response',{})
   try:assert_mcp_pair(p);proof={'assertions':'PASS'}
   except Exception as error:proof={'assertions':'FAIL','error':type(error).__name__+': '+str(error)}
   pairs.append({'tool':p['tool'],'direction':p['direction'],'api_request':p.get('api_request'),'mcp_adapter_request':p.get('mcp_adapter_request'),
     'api_http_status':p.get('api',{}).get('http_status'),'mcp_http_status':p.get('mcp',{}).get('http_status'),
     'api_request_rate':a.get('request_rate'),'api_request_rate_type':type(a.get('request_rate')).__name__,
     'mcp_request_rate':b.get('request_rate'),'mcp_request_rate_type':type(b.get('request_rate')).__name__,
     'complete_business_result_equal':functional(a)==functional(b),**proof})
 checks['mcp_complete_parity']=group('MCP01-06-STDIO',{'complete_pairs':pairs,'omitted_business_fields':[]})
 known={}
 for name in ['VAL01-04','STATE-CANCEL-BEFORE-HANDOVER']:
  e=case(name);detail={'error':e.get('error'),'steps':[]}
  for s in e['steps']:
   if name=='VAL01-04' and s['name']!='negative-native-cost':continue
   d={k:s.get(k) for k in ['name','status','http_status','expected_state','reason','assertion_error'] if k in s}
   if 'response' in s:d['native_response']={k:s['response'].get(k) for k in ['error_type','error']}
   if 'native_result' in s:
    d['native_probes']={p:{k:v.get(k) for k in ['input_cost','qty','reloaded_status','reloaded_lines','stage','diagnostic_rollback_only','error_type','error']} for p,v in s['native_result'].items() if p in ['valid_control','invalid_attempt']}
   detail['steps'].append(d)
  known[name]=group(name,detail)
 criteria=criteria_for(rows,original['build_evidence'],bank,index,fixtures,root)
 result['phases'][phase]={'groups':rows,'counts':dict(Counter(r['status'] for r in rows)),
   'criteria':criteria,'criteria_counts':dict(Counter(c['status'] for c in criteria)),
   'corrections':checks,'functional_findings':known,'build_evidence':original['build_evidence'],
   'administrator_gates':original['gates'],'smoke':original['smoke']}
try:assert_repeat_contents(payload,fixtures);result['repetition']={'derived_status':'PASS','complete':True,**loaded}
except Exception as error:result['repetition']={'derived_status':'FAIL','complete':False,'error':type(error).__name__+': '+str(error),**loaded}
# No case trees duplicated: receipt contains only derived rows and targeted fields.
out=root/'corrections-verification.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'run_id':receipt['run_id'],'phases':{p:{'groups':v['counts'],'criteria':v['criteria_counts']} for p,v in result['phases'].items()},'repeat':result['repetition']}))
