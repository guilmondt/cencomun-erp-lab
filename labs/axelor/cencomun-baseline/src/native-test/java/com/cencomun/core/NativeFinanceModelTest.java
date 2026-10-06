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
  @Test void benchmarkReferenceBelongsToTheNativeStatementLine() throws Exception {
    com.cencomun.core.db.CcmBankRow row=new com.cencomun.core.db.CcmBankRow();
    com.axelor.apps.bankpayment.db.BankStatementLine line=new com.axelor.apps.bankpayment.db.BankStatementLine();
    line.setReference("BENCH-B0000");row.setStatementLine(line);
    assertEquals("BENCH-B0000",NativeAccess.get(NativeAccess.get(row,"statementLine"),"reference"));
    assertThrows(NoSuchMethodException.class,()->row.getClass().getMethod("getReference"));
  }
  @Test void purchaseRateRetainsTheSameStringTypeBeforeAndAfterReplaySerialization() throws Exception {
    com.axelor.apps.base.db.Company company=new com.axelor.apps.base.db.Company();company.setId(1L);company.setCode("CCM-LAB-001");
    com.axelor.auth.db.User creator=new com.axelor.auth.db.User();creator.setCode("ccm-mcp");
    com.axelor.apps.base.db.Currency currency=new com.axelor.apps.base.db.Currency();currency.setCodeISO("USD");
    PurchaseOrder order=new PurchaseOrder();order.setId(2L);order.setCurrency(currency);order.setOrderDate(java.time.LocalDate.of(2026,10,1));order.setStatusSelect(1);order.setPurchaseOrderLineList(new java.util.ArrayList<>());
    com.cencomun.core.db.CcmPurchase purchase=new com.cencomun.core.db.CcmPurchase();purchase.setId(3L);purchase.setCompany(company);purchase.setCreator(creator);purchase.setPurchaseOrder(order);purchase.setFunctionalId("MCP-PO");purchase.setUsdBase(new java.math.BigDecimal("199.99"));purchase.setRequestRate(java.math.BigDecimal.ZERO);
    CorePurchaseService service=new CorePurchaseService();java.util.Map<String,Object> first=service.view(purchase);
    assertInstanceOf(String.class,first.get("request_rate"));assertEquals("0",first.get("request_rate"));
    purchase.setRequestRate(java.math.BigDecimal.ZERO.setScale(6));java.util.Map<String,Object> persisted=service.view(purchase);
    assertEquals(first,persisted);
    java.util.Map<String,Object> replay=CoreOrderService.JSON.readValue(CoreOrderService.encode(persisted),java.util.Map.class);
    assertInstanceOf(String.class,replay.get("request_rate"));assertEquals(first.get("request_rate"),replay.get("request_rate"));
    // Compare the complete wire JSON: native Long IDs can deserialize as Integer
    // internally, but their public numeric value remains identical.
    assertEquals(CoreOrderService.JSON.readTree(CoreOrderService.encode(first)),CoreOrderService.JSON.readTree(CoreOrderService.encode(replay)));
  }
  @Test void immutableNativeAuditRepositoryReturnsPermissionDenialBeforePersistence() {
    com.cencomun.core.db.CcmAudit audit=new com.cencomun.core.db.CcmAudit();audit.setId(1L);
    CcmAuditWorkflowRepository repository=new CcmAuditWorkflowRepository();
    assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->repository.save(audit)).getResponse().getStatus());
    assertEquals(403,assertThrows(jakarta.ws.rs.ForbiddenException.class,()->repository.remove(audit)).getResponse().getStatus());
  }
}
