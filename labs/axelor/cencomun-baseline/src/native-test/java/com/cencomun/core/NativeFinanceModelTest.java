package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.axelor.apps.base.db.Bank;
import com.axelor.apps.base.db.BankDetails;
import com.axelor.apps.purchase.db.PurchaseOrder;
import com.axelor.apps.purchase.db.PurchaseOrderLine;
import com.axelor.apps.purchase.service.PurchaseOrderLineService;
import org.junit.jupiter.api.Test;

/** Checks the fixed native API; ERP values/transactions are accepted only in CI. */
class NativeFinanceModelTest {
  @org.junit.jupiter.api.BeforeAll static void initializeRepositoryConstructorOnly() {
    NativeOrderModelTest.initializeRepositoryConstructorOnly();
  }
  @Test void pinnedSessionProvidesActualJdbcExecutionCallbacks() throws Exception {
    assertNotNull(org.hibernate.engine.spi.SessionImplementor.class.getMethod("getEventListenerManager"));
    assertNotNull(org.hibernate.engine.spi.SessionEventListenerManager.class.getMethod("addListener",org.hibernate.SessionEventListener[].class));
    for(String method:java.util.List.of("jdbcExecuteStatementStart","jdbcExecuteStatementEnd","jdbcExecuteBatchStart","jdbcExecuteBatchEnd"))
      assertNotNull(org.hibernate.SessionEventListener.class.getMethod(method));
  }
  @Test void bankCodeIsTheNativeBicAndBankNameIsTheSupportedField() {
    Bank bank=new Bank();bank.setBankName("Synthetic LAB bank");bank.setCode("LABOUS00XXX");
    BankDetails details=new BankDetails();details.setBank(bank);details.setIban("GB82WEST12345698765432");
    assertEquals("Synthetic LAB bank",bank.getBankName());assertEquals("LABOUS00XXX",details.getBank().getCode());
    assertThrows(NoSuchMethodException.class,()->Bank.class.getMethod("setName",String.class));
    assertThrows(NoSuchMethodException.class,()->Bank.class.getMethod("setBic",String.class));
  }
  @Test void nativeLineComputeAcceptsTheLineAndItsOrderBeforeHeaderTotals() throws Exception {
    assertNotNull(PurchaseOrderLineService.class.getMethod("compute",PurchaseOrderLine.class,PurchaseOrder.class));
    PurchaseOrderLine line=new PurchaseOrderLine();assertEquals(0,line.getPriceDiscounted().signum());
  }
  @Test void decimalSerializationIsIdenticalAfterPersistenceChangesScale() {
    for(String value:java.util.List.of("199.99","0","1")) {
      java.math.BigDecimal amount=new java.math.BigDecimal(value);
      assertEquals(CorePurchaseService.decimal(amount),CorePurchaseService.decimal(amount.setScale(10)));
    }
  }
  @Test void immutableNativeAuditRepositoryReturnsPermissionDenialBeforePersistence() {
    com.cencomun.core.db.CcmAudit audit=new com.cencomun.core.db.CcmAudit();audit.setId(1L);
    CcmAuditWorkflowRepository repository=new CcmAuditWorkflowRepository();
    assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->repository.save(audit)).getResponse().getStatus());
    assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->repository.remove(audit)).getResponse().getStatus());
  }
}
