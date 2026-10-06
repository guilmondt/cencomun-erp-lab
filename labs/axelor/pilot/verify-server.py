#!/usr/bin/env python3
"""Post-UI checks for the five-sale disposable acceptance dataset."""
from http_client import Client
from evidence import EvidenceRun
from snapshots import capture,digest,diff
from pathlib import Path
import os,json
from concurrent.futures import ThreadPoolExecutor
p=Path(os.environ['CCM_PILOT_RESULTS']);secrets=json.loads(Path(os.environ['CCM_PILOT_ACTORS_FILE']).read_text())
a=Client(password=os.environ.get('CCM_PILOT_ADMIN_PASSWORD','admin'))
def actor(role):return Client('pilot-'+role,secrets[role])
models=['com.cencomun.core.db.CcmPilotSale','com.cencomun.core.db.CcmPilotSession','com.axelor.apps.sale.db.SaleOrder','com.axelor.apps.account.db.Invoice','com.axelor.apps.stock.db.StockMove','com.axelor.apps.account.db.PaymentVoucher','com.axelor.apps.account.db.Move','com.axelor.apps.account.db.Reconcile']
def counts():return {m:a.request('/ws/rest/'+m+'/search',{'limit':1})['total'] for m in models}
def act(c,name,context,model='com.cencomun.core.db.CcmPilotSale'):
 result=c.action(name,context,model)
 proof.data.setdefault('action_responses',[]).append({'action':name,'model':model,'context':context,'result':result});proof.save()
 return result
def denied(result,reason):
 proof.check('explicit denial: '+reason,reason in json.dumps(result),result,reason)
 return result
with EvidenceRun(p/'server-replays.json') as proof:
 initial=capture(a);proof.data['snapshot_before']=initial;proof.save()
 try:
  before=counts();out={'before':before,'replays':[]};proof.data['operations']=out;c=actor('supervisor')
  for id,action in [(1,'collect'),(1,'deliver'),(2,'settle'),(3,'settle'),(5,'cancel')]:
   r=act(c,'ccm-pilot-'+action,{'id':id,'reason':'re-entry'});assert r['status']==0,r;out['replays'].append(r)
  def repeat(_):return act(actor('supervisor'),'ccm-pilot-settle',{'id':3})
  with ThreadPoolExecutor(max_workers=2) as pool:
   for r in pool.map(repeat,range(2)):assert r['status']==0;out['replays'].append(r)
  session_model='com.cencomun.core.db.CcmPilotSession'
  r=act(c,'ccm-pilot-close',{'cashCountedInput':'164','cashDifferenceReason':'Faltante ficticio de 1 USD en recuento'},session_model);assert r['status']==0,r;out['same_close']=r
  out['changed_close']=denied(act(c,'ccm-pilot-close',{'cashCountedInput':'163','cashDifferenceReason':'Changed'},session_model),'Confirmed cash close immutable')
  out['late_refund']=denied(act(c,'ccm-pilot-cancel',{'id':4,'reason':'late refund'}),'Cash session confirmed and immutable')
  s=a.request('/ws/rest/'+session_model+'/1')['data'][0]
  out['generic_admin_close_write']=denied(a.request('/ws/rest/'+session_model,{'data':{'id':1,'version':s['version'],'counted':'163'}}),'Use the authenticated Cencomun workflow service')
  for role in ('operator','supervisor'):
   x=actor(role);tests={}
   for name in ['action-sale-order-method-confirm-cancel','com.axelor.meta.web.MetaController:restoreAll','ccm-pilot-deliver,com.axelor.meta.web.MetaController:restoreAll','ccm-pilot-prepare']:
    tests[name]=denied(act(x,name,{'id':4}),'Pilot action denied')
   sale=a.request('/ws/rest/com.cencomun.core.db.CcmPilotSale/4')['data'][0]
   tests['generic_sale_write']=denied(x.request('/ws/rest/com.cencomun.core.db.CcmPilotSale',{'data':{'id':4,'version':sale['version'],'state':'SETTLED'}}),'Use the authenticated Cencomun workflow service')
   product=a.request('/ws/rest/com.axelor.apps.base.db.Product/1')['data'][0]
   tests['native_product_negative_cost']=denied(x.request('/ws/rest/com.axelor.apps.base.db.Product',{'data':{'id':1,'version':product['version'],'costPrice':'-1'}}),'not authorized')
   if role=='operator':
    for name in ['cancel','settle']:
     tests[name]=denied(act(x,'ccm-pilot-'+name,{'id':4,'reason':'denied'}),'Pilot role denied')
    tests['close']=denied(act(x,'ccm-pilot-close',{'cashCountedInput':'164'},session_model),'Pilot role denied')
   out[role]=tests
  probe=a.action('ccm-core-cycle-negative-cost',{'case_id':'PILOT'})
  assert probe['status']==0,probe
  cost_proof=next(x['values']['core_result'] for x in probe['data'] if 'values' in x)
  assert cost_proof['valid_control']['diagnostic_rollback_only'] is True
  assert cost_proof['invalid_attempt']['diagnostic_rollback_only'] is False
  assert 'Pilot negative cost forbidden' in cost_proof['invalid_attempt']['error']
  out['native_cost_control']=cost_proof
  out['after']=counts();proof.check('same record counts',out['before']==out['after'],out['after'],out['before'])
  
 finally:
  final=capture(a);proof.data['snapshot_after']=final;proof.data['snapshot_hashes']={'before':digest(initial),'after':digest(final)};proof.data['snapshot_diff']=diff(initial,final);proof.save()
  proof.check('economic fields unchanged',initial==final,proof.data['snapshot_diff'],{})
print('Negative controls and replays: complete economic snapshots unchanged PASS')
