#!/usr/bin/env python3
"""Adds one clearly labeled foreign sentinel, without an operational store/ledger.
Run only after backing up the disposable acceptance DB; never production.
"""
from http_client import Client
from pathlib import Path
import json,os,urllib.error
if os.environ.get('CCM_PILOT_DISPOSABLE')!='1':raise SystemExit('Disposable fixture required')
p=Path(os.environ['CCM_PILOT_RESULTS']);actors=json.loads(Path(os.environ['CCM_PILOT_ACTORS_FILE']).read_text());a=Client(password=os.environ.get('CCM_PILOT_ADMIN_PASSWORD','admin'));out={}
def create(model,data,domain=None):
 if domain:
  old=a.request('/ws/rest/'+model+'/search',{'data':{'_domain':domain},'limit':1})
  if old.get('data'):return old['data'][0]
 r=a.request('/ws/rest/'+model,{'data':data});assert r['status']==0,r;return r['data'][0]
company=create('com.axelor.apps.base.db.Company',{'code':'ISOLATION-SENTINEL','name':'Negative-test sentinel; no operational store'},"self.code = 'ISOLATION-SENTINEL'")
create('com.axelor.apps.account.db.AccountConfig',{'company':{'id':company['id']}},'self.company.id = '+str(company['id']))
partner=create('com.axelor.apps.base.db.Partner',{'name':'Foreign fictitious sentinel','partnerSeq':'ISOLATION-SENTINEL','isCustomer':False,'companySet':[{'id':company['id']}]},"self.partnerSeq = 'ISOLATION-SENTINEL'")
product=create('com.axelor.apps.base.db.Product',{'code':'ISOLATION-SENTINEL','name':'Foreign product sentinel','salePrice':'11','costPrice':'5'},"self.code = 'ISOLATION-SENTINEL'")
profile=create('com.cencomun.core.db.CcmProductProfile',{'company':{'id':company['id']},'product':{'id':product['id']},'warrantyQuantity':1,'warrantyUnit':'YEAR','condition':'NEW','casheaEnabled':True,'casheaPrice':'11','supplierReference':'LAB-SENTINEL'},'self.company.id = '+str(company['id']))
out['sentinel']={'company':company['id'],'partner':partner['id'],'product':product['id'],'profile':profile['id']}
for iteration in range(3):
 for role in ('operator','supervisor'):
  c=Client('pilot-'+role,actors[role]);rows={}
  for key,model,record in [('partner','com.axelor.apps.base.db.Partner',partner),('product','com.axelor.apps.base.db.Product',product),('profile','com.cencomun.core.db.CcmProductProfile',profile)]:
   r=c.request('/ws/rest/'+model+'/search',{'data':{'_domain':'self.id = '+str(record['id'])},'limit':10});assert r['status']==0 and r.get('total',0)==0,r;rows[key+'_search']=r
   try:r=c.request('/ws/rest/'+model+'/'+str(record['id']))
   except urllib.error.HTTPError as e:r={'http':e.code}
   assert r.get('status',-1)!=0 or not r.get('data'),r;rows[key+'_direct_read']=r
  r=c.action('ccm-pilot-line',{'product':{'id':product['id']}},'com.cencomun.core.db.CcmPilotLine');assert 'Product outside pilot catalog' in json.dumps(r),r;rows['catalog_scope']=r
  out[str(iteration)+'-'+role]=rows
(p/'isolation.json').write_text(json.dumps(out,indent=2));print('Foreign sentinel search/direct read and catalog service denied for both profiles, three logins each PASS')
