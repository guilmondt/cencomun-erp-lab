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
}
