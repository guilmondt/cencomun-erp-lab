package com.cencomun.core;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.math.BigDecimal;
class NativePilotTest {
  @org.junit.jupiter.api.BeforeAll static void initialize(){NativeOrderModelTest.initializeRepositoryConstructorOnly();}
  @Test void firstReceiptReconciliationStartsWithAnEmptyPaymentCollection() {
    var invoice=new com.axelor.apps.account.db.Invoice();invoice.setInvoicePaymentList(null);
    PilotPayments.initializePaymentCollection(invoice);assertNotNull(invoice.getInvoicePaymentList());assertTrue(invoice.getInvoicePaymentList().isEmpty());
    var existing=new com.axelor.apps.account.db.InvoicePayment();invoice.addInvoicePaymentListItem(existing);
    PilotPayments.initializePaymentCollection(invoice);assertEquals(java.util.List.of(existing),invoice.getInvoicePaymentList());
  }
  @Test void receiptNegativeCostCannotPassPilotBoundary() {
    var line=new com.axelor.apps.stock.db.StockMoveLine();
    line.setUnitPriceUntaxed(new BigDecimal("-0.01"));
    assertEquals(422,assertThrows(CoreFault.class,()->PilotCostGuard.check(line,"unitPriceUntaxed","wapPrice")).status);
    line.setUnitPriceUntaxed(new BigDecimal("30.00"));PilotCostGuard.check(line,"unitPriceUntaxed","wapPrice");
  }
  @Test void productAndNativeAverageCostCannotBeNegative() {
    var product=new com.axelor.apps.base.db.Product();product.setCostPrice(new BigDecimal("-0.01"));
    assertThrows(CoreFault.class,()->PilotCostGuard.check(product,"costPrice","purchasePrice"));
    var row=new com.axelor.apps.stock.db.StockLocationLine();row.setAvgPrice(new BigDecimal("-0.01"));
    assertThrows(CoreFault.class,()->PilotCostGuard.check(row,"avgPrice"));
  }
  @Test void genericWritesAndDeletionCannotBypassPilotWorkflow() {
    var session=new com.cencomun.core.db.CcmPilotSession();session.setId(1L);session.setState("CONFIRMED");
    var repository=new CcmPilotSessionWorkflowRepository();
    assertEquals(403,assertThrows(CoreFault.class,()->repository.save(session)).status);
    assertThrows(CoreFault.class,()->repository.remove(session));
    var sale=new com.cencomun.core.db.CcmPilotSale();sale.setId(2L);
    assertEquals(403,assertThrows(CoreFault.class,()->new CcmPilotSaleWorkflowRepository().save(sale)).status);
  }
  @Test void saleStoresNativePaymentSeparatelyFromBankSettlementAndSession() throws Exception {
    Class<?> sale=com.cencomun.core.db.CcmPilotSale.class;
    assertEquals(com.axelor.apps.account.db.PaymentVoucher.class,sale.getMethod("getInitialVoucher").getReturnType());
    assertEquals(com.axelor.apps.account.db.Move.class,sale.getMethod("getSettlement").getReturnType());
    assertEquals(com.cencomun.core.db.CcmPilotSession.class,sale.getMethod("getSession").getReturnType());
  }

  @Test void nativeActionsAndAdministrativeChainsCannotBypassPilotScreens() {
    PilotActionGuard.check("ccm-pilot-deliver");
    PilotActionGuard.check("ccm-pilot-flags,com.axelor.meta.web.MetaController:moreAttrs");
    for(String action:java.util.List.of("com.axelor.meta.web.MetaController:restoreAll","action-sale-order-method-confirm-cancel","ccm-pilot-deliver,com.axelor.meta.web.MetaController:restoreAll","ccm-pilot-prepare"))
      assertThrows(CoreFault.class,()->PilotActionGuard.check(action));
  }
  private com.axelor.apps.account.db.Move invoiceMove(String tax,String receivable) {
    var move=new com.axelor.apps.account.db.Move();
    var company=new com.axelor.apps.base.db.Company();company.setId(1L);move.setCompany(company);
    for(String code:java.util.List.of("REVENUE","TAX","AR")) {
      var account=new com.axelor.apps.account.db.Account();account.setCode("CCM-"+code);
      var line=new com.axelor.apps.account.db.MoveLine();line.setAccount(account);
      if(code.equals("REVENUE"))line.setCredit(new BigDecimal("81.81"));
      else if(code.equals("TAX"))line.setCredit(new BigDecimal(tax));
      else line.setDebit(new BigDecimal(receivable));
      move.addMoveLineListItem(line);
    }
    return move;
  }
  @Test void taxInclusiveLineRoundingIsExactAndBalancedWithoutTolerance() {
    var expected=java.util.Map.of("gross",new BigDecimal("90.00"),"revenue",new BigDecimal("81.81"),"tax",new BigDecimal("8.19"));
    PilotInvoiceTaxGuard.check(invoiceMove("8.19","90.00"),1L,expected);
    // Even balanced one- and two-cent tax discrepancies are rejected.
    for(String[] values:new String[][]{{"8.18","89.99"},{"8.21","90.02"},{"8.19","90.01"}})
      assertThrows(CoreFault.class,()->PilotInvoiceTaxGuard.check(invoiceMove(values[0],values[1]),1L,expected));
    assertThrows(CoreFault.class,()->PilotInvoiceTaxGuard.check(invoiceMove("8.19","90.00"),2L,expected));
  }
}
