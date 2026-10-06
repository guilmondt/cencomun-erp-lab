package com.cencomun.baseline.module;

import com.axelor.app.AxelorModule;

/** Supported Cencomun repository bindings; independent AOP profile has no native entities. */
public class CencomunModule extends AxelorModule {
  @Override @SuppressWarnings({"rawtypes", "unchecked"})
  protected void configure() {
    if("1".equals(System.getenv("CCM_AXELOR_FULL_STACK"))) {
      // Supported Guice interception, confined to this disposable Core runtime.
      // Reflection keeps the independent AOP module free of native AOS dependency pins.
      java.util.Map<String,java.util.Set<String>> guarded=java.util.Map.ofEntries(
          java.util.Map.entry("com.axelor.apps.purchase.service.PurchaseOrderCreateService",java.util.Set.of("createPurchaseOrder")),
          java.util.Map.entry("com.axelor.apps.purchase.service.PurchaseOrderService",java.util.Set.of("requestPurchaseOrder")),
          java.util.Map.entry("com.axelor.apps.purchase.service.PurchaseOrderWorkflowService",java.util.Set.of("validatePurchaseOrder","cancelPurchaseOrder","draftPurchaseOrder")),
          java.util.Map.entry("com.axelor.apps.sale.service.saleorder.SaleOrderCreateService",java.util.Set.of("createSaleOrder")),
          java.util.Map.entry("com.axelor.apps.sale.service.saleorder.status.SaleOrderWorkflowService",java.util.Set.of("cancelSaleOrder")),
          java.util.Map.entry("com.axelor.apps.sale.service.saleorder.status.SaleOrderConfirmService",java.util.Set.of("confirmSaleOrder")),
          java.util.Map.entry("com.axelor.apps.sale.service.saleorder.status.SaleOrderFinalizeService",java.util.Set.of("finalizeQuotation")),
          java.util.Map.entry("com.axelor.apps.stock.service.StockMoveService",java.util.Set.of("plan","realize","cancel")),
          java.util.Map.entry("com.axelor.apps.account.service.invoice.InvoiceService",java.util.Set.of("validate","ventilate","validateAndVentilate")),
          java.util.Map.entry("com.axelor.apps.account.service.payment.invoice.payment.InvoicePaymentValidateService",java.util.Set.of("validate")),
          java.util.Map.entry("com.axelor.apps.account.service.payment.paymentvoucher.PaymentVoucherConfirmService",java.util.Set.of("confirmPaymentVoucher")),
          java.util.Map.entry("com.axelor.apps.account.service.move.MoveValidateService",java.util.Set.of("accounting")),
          java.util.Map.entry("com.axelor.apps.bankpayment.service.bankstatement.BankStatementImportService",java.util.Set.of("runImport")),
          java.util.Map.entry("com.axelor.apps.bankpayment.service.bankstatementline.BankStatementLineCreationService",java.util.Set.of("createBankStatementLine")),
          java.util.Map.entry("com.axelor.apps.bankpayment.service.bankreconciliation.BankReconciliationLineService",java.util.Set.of("reconcileBRLAndMoveLine")),
          java.util.Map.entry("com.axelor.apps.bankpayment.service.bankreconciliation.BankReconciliationValidateService",java.util.Set.of("validate")));
      if ("1".equals(System.getenv("CCM_PILOT_LAB"))) {
        bindInterceptor(com.google.inject.matcher.Matchers.subclassesOf(com.axelor.meta.ActionExecutor.class),
            new com.google.inject.matcher.AbstractMatcher<java.lang.reflect.Method>() {
              @Override public boolean matches(java.lang.reflect.Method m) {return m.getName().equals("execute");}
            },new com.cencomun.core.PilotActionGuard());
        bindInterceptor(com.google.inject.matcher.Matchers.subclassesOf(com.axelor.db.JpaRepository.class),
            new com.google.inject.matcher.AbstractMatcher<java.lang.reflect.Method>() {
              @Override public boolean matches(java.lang.reflect.Method m) {return java.util.Set.of("save","remove").contains(m.getName());}
            }, new com.cencomun.core.PilotCostGuard());
        try {
          bindInterceptor(com.google.inject.matcher.Matchers.subclassesOf(Class.forName("com.axelor.apps.account.service.move.MoveValidateService")),
              new com.google.inject.matcher.AbstractMatcher<java.lang.reflect.Method>() {
                @Override public boolean matches(java.lang.reflect.Method m) {return m.getName().equals("checkTaxAmount");}
              },new com.cencomun.core.PilotInvoiceTaxGuard());
          bindInterceptor(com.google.inject.matcher.Matchers.subclassesOf(Class.forName("com.axelor.apps.stock.service.StockMoveService")),
              new com.google.inject.matcher.AbstractMatcher<java.lang.reflect.Method>() {
                @Override public boolean matches(java.lang.reflect.Method m) {return java.util.Set.of("plan","planWithNoSplit","realize").contains(m.getName());}
              }, new com.cencomun.core.PilotCostGuard());
        } catch(ClassNotFoundException error) {throw new IllegalStateException(error);}
      }
      guarded.forEach((name,methods)-> {
        try {
          Class<?> service=Class.forName(name);
          for(String method:methods)if(java.util.Arrays.stream(service.getMethods()).noneMatch(m->m.getName().equals(method)))
            throw new IllegalStateException("Pinned critical native method missing: "+name+"."+method);
          bindInterceptor(com.google.inject.matcher.Matchers.subclassesOf(service),
              new com.google.inject.matcher.AbstractMatcher<java.lang.reflect.Method>() {
                @Override public boolean matches(java.lang.reflect.Method method){return methods.contains(method.getName());}
              },new com.cencomun.core.CoreNativePermissionInterceptor());
        }catch(ClassNotFoundException missing){throw new IllegalStateException("Pinned native permission service missing: "+name,missing);}
      });
    }
    for(String name : new String[]{"CcmOrder","CcmOrderLine","CcmRequestKey","CcmOutboxEvent","CcmAudit","CcmPurchase","CcmCashClose","CcmBankImport","CcmBankRow","CcmPilotSale","CcmPilotSession","CcmPilotLine"}) {
      try {
        Class repository=Class.forName("com.cencomun.core.db.repo."+name+"Repository");
        Class extension=Class.forName("com.cencomun.core."+name+"WorkflowRepository");
        bind(repository).to(extension);
      } catch(ClassNotFoundException missing) {
        if("1".equals(System.getenv("CCM_AXELOR_FULL_STACK")))
          throw new IllegalStateException("Native Core repository binding missing: "+name,missing);
      }
    }
  }
}
