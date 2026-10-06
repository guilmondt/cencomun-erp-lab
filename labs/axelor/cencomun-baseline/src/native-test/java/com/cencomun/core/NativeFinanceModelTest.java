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
}
