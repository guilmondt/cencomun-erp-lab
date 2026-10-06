package com.cencomun.core;
import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/** Native unallocated receipt now; native reconciliation when the invoice exists later. */
final class PilotPayments {
  static Model receipt(Model sale,boolean refund) {
    BigDecimal amount=(BigDecimal)get(sale,"initial");
    if(amount.signum()==0)return null;
    Model company=(Model)get(sale,"company");
    Model voucher=record(PilotService.ACCOUNT+"PaymentVoucher","company",company,"partner",get(sale,"customer"),
        "currency",get(company,"currency"),"paymentMode",one(PilotService.ACCOUNT+"PaymentMode","self.code = ?1",refund?"CCM-PILOT-REFUND":"CCM-CASH"),
        "paymentDate",PilotService.DATE,"ref",get(sale,"reference")+(refund?"-REFUND":"-INITIAL"),"paidAmount",amount,
        "operationTypeSelect",refund?4:3,"user",AuthUtils.getUser(),"payVoucherElementToPayList",new ArrayList<Model>(),"payVoucherDueElementList",new ArrayList<Model>());
    call(service("com.axelor.apps.account.service.payment.paymentvoucher.PaymentVoucherConfirmService"),"confirmPaymentVoucher",voucher);
    return managed(voucher);
  }
  static Model receivable(Model move,boolean debit) {
    for(Object row:(List<?>)get(move,"moveLineList"))if("CCM-AR".equals(get(get(row,"account"),"code"))
        && ((BigDecimal)get(row,debit?"debit":"credit")).signum()>0)return (Model)row;
    throw new CoreFault(409,"Native receivable line missing");
  }
  static void initializePaymentCollection(Model invoice) {
    if(get(invoice,"invoicePaymentList")==null)set(invoice,"invoicePaymentList",new ArrayList<Model>());
  }
  static void applyToInvoice(Model sale) {
    Model invoice=managed((Model)get(sale,"invoice")),voucher=managed((Model)get(sale,"initialVoucher"));
    initializePaymentCollection(invoice);invoice=save(invoice);
    Model debit=receivable((Model)get(invoice,"move"),true),credit=receivable((Model)get(voucher,"generatedMove"),false);
    call(service("com.axelor.apps.account.service.reconcile.ReconcileService"),"reconcile",debit,credit,false,true);
  }
  static void matchRefund(Model sale) {
    Model receipt=(Model)get(sale,"initialVoucher"),refund=(Model)get(sale,"refundVoucher");
    call(service("com.axelor.apps.account.service.reconcile.ReconcileService"),"reconcile",
        receivable((Model)get(refund,"generatedMove"),true),receivable((Model)get(receipt,"generatedMove"),false),false,true);
  }
  private PilotPayments() {}
}
