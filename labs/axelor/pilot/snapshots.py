"""Committed native/economic fields; no passwords or volatile UI metadata."""
import hashlib,json
FIELDS={
 'com.cencomun.core.db.CcmPilotSession':'company businessDate state expected counted difference reason sourceSnapshot confirmedBy confirmedAt',
 'com.cencomun.core.db.CcmPilotSale':'company session reference payloadHash payload state kind channel customer gross initial financed shipping commission transfer saleOrder delivery invoice initialVoucher refundVoucher settlement costMove guide creator',
 'com.cencomun.core.db.CcmPilotLine':'sale product qty price warrantyQuantity warrantyUnit',
 'com.axelor.apps.base.db.Product':'code costPrice purchasePrice salePrice unit',
 'com.axelor.apps.sale.db.SaleOrder':'company clientPartner stockLocation currency externalReference statusSelect exTaxTotal taxTotal inTaxTotal orderDate',
 'com.axelor.apps.stock.db.StockMove':'company partner fromStockLocation toStockLocation stockMoveSeq statusSelect realDate saleOrder',
 'com.axelor.apps.stock.db.StockMoveLine':'stockMove product qty realQty unitPriceUntaxed unitPriceTaxed wapPrice unit',
 'com.axelor.apps.stock.db.StockLocationLine':'stockLocation product currentQty futureQty avgPrice unit',
 'com.axelor.apps.account.db.Invoice':'company partner invoiceId invoiceDate statusSelect exTaxTotal taxTotal inTaxTotal amountPaid amountRemaining move saleOrder',
 'com.axelor.apps.account.db.InvoiceLine':'invoice product qty price inTaxPrice exTaxTotal inTaxTotal account taxLineSet saleOrderLine',
 'com.axelor.apps.account.db.PaymentVoucher':'company partner ref paymentDate statusSelect paidAmount currency paymentMode generatedMove',
 'com.axelor.apps.account.db.InvoicePayment':'invoice amount paymentDate typeSelect statusSelect move',
 'com.axelor.apps.account.db.Move':'company partner journal reference origin date statusSelect currency invoice',
 'com.axelor.apps.account.db.MoveLine':'move account partner debit credit amountRemaining currencyAmountRemaining currencyAmount date taxLineSet',
 'com.axelor.apps.account.db.Reconcile':'debitMoveLine creditMoveLine amount date statusSelect',
}
def capture(client):
 out={}
 for model,fields in FIELDS.items():
  r=client.request('/ws/rest/'+model+'/search',{'fields':['id','version',*fields.split()],'limit':10000})
  assert r['status']==0,r
  rows=r.get('data',[]);assert len(rows)==r.get('total',0),'Snapshot must not be truncated'
  out[model]=sorted(rows,key=lambda x:x['id'])
 return out
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def diff(before,after):
 out={}
 for model in sorted(set(before)|set(after)):
  if before.get(model)!=after.get(model):out[model]={'before':before.get(model),'after':after.get(model)}
 return out
