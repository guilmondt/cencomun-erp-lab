from http_client import Client
from pathlib import Path
from decimal import Decimal as D
import json,os
p=Path(os.environ['CCM_PILOT_RESULTS']);c=Client(password=os.environ.get('CCM_PILOT_ADMIN_PASSWORD','admin'));out={}
def read(model,id):return c.request('/ws/rest/'+model+'/'+str(id))['data'][0]
def rows(model,domain):return c.request('/ws/rest/'+model+'/search',{'data':{'_domain':domain},'limit':100})['data']
sales=rows('com.cencomun.core.db.CcmPilotSale','self.company.id = 1');stock=rows('com.axelor.apps.stock.db.StockLocationLine',"self.stockLocation.name = 'WH-LAB-001-PILOT'")
for s in sales:
 r={'sale':s};out[str(s['id'])]=r
 for field,model in [('invoice','Invoice'),('settlement','Move'),('costMove','Move'),('initialVoucher','PaymentVoucher'),('refundVoucher','PaymentVoucher')]:
  if s[field]:r[field]=read('com.axelor.apps.account.db.'+model,s[field]['id'])
 if s['invoice']:
  assert D(r['invoice']['amountPaid'])+D(r['invoice']['amountRemaining'])==D(s['gross'])
  if s['state'] in ('SETTLED','PAID'):assert D(r['invoice']['amountRemaining'])==0
 for field in ['settlement','costMove']:
  if not s[field]:continue
  lines=rows('com.axelor.apps.account.db.MoveLine','self.move.id = '+str(s[field]['id']));r[field+'_lines']=lines
  assert sum(D(x['debit'])-D(x['credit']) for x in lines)==0
  totals={}
  for x in lines:
   code=x['account']['code'];totals[code]=totals.get(code,D(0))+D(x['debit'])-D(x['credit'])
  if field=='settlement':
   assert totals.get('CCM-BANK')==D(s['transfer']);assert totals.get('CCM-COMMISSION')==D(s['commission']);assert totals.get('CCM-SHIPPING',D(0))==D(s['shipping']);assert totals.get('CCM-AR')==-D(s['financed']);assert 'CCM-CASH' not in totals
 if s['state']=='CANCELLED':
  order=read('com.axelor.apps.sale.db.SaleOrder',s['saleOrder']['id']);r['order']=order;assert order['statusSelect']==5
  assert s['invoice'] is None and s['delivery'] is None and s['costMove'] is None
 if s['state']=='RESERVED':assert s['invoice'] is None and s['delivery'] is None
assert len(sales)==5, 'Repeated UI clicks must create exactly five sales'
assert {s['id']:s['state'] for s in sales}=={1:'PAID',2:'SETTLED',3:'SETTLED',4:'RESERVED',5:'CANCELLED'}
observed={x['product']['code']:D(x['currentQty']) for x in stock}
assert observed=={f'P{i:03d}':D(18 if i in (1,2) else 19 if i in (4,5) else 20) for i in range(1,11)},observed
assert D(out['3']['invoice']['exTaxTotal'])==D('81.81') and D(out['3']['invoice']['taxTotal'])==D('8.19')
assert D(out['3']['invoice']['inTaxTotal'])==90
lines=rows('com.cencomun.core.db.CcmPilotLine','self.sale.id = 3')
assert {(x['warrantyQuantity'],x['warrantyUnit']) for x in lines}=={(90,'DAY'),(1,'YEAR')}
assert D(out['3']['costMove_lines'][0]['debit'])+D(out['3']['costMove_lines'][1]['debit'])==45
out['stock']=stock
out['cash_session']=read('com.cencomun.core.db.CcmPilotSession',1)
session=out['cash_session']
assert session['state']=='CONFIRMED' and D(session['expected'])==165 and D(session['counted'])==164 and D(session['difference'])==-1,session
assert 'Faltante ficticio de 1 USD' in session['reason']
assert sum(D(x['amount']) for x in json.loads(session['sourceSnapshot'])['sources'])==165
out['tax_gap']=read('com.axelor.apps.account.db.AccountConfig',1)['allowedTaxGap'];assert D(out['tax_gap'])==0
(p/'native-linked-ledger.json').write_text(json.dumps(out,indent=2));print('Linked sales, payments, native balance, commission/shipping and zero tax tolerance PASS')
