package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;

import com.axelor.studio.db.AppInvoice;
import org.junit.jupiter.api.Test;

class NativeInvoiceRuntimeTest {
  @Test void labDisablesOnlyAutomaticSalesPdf() {
    AppInvoice app = new AppInvoice();
    app.setAutoGenerateInvoicePrintingFileOnSaleInvoice(true);
    app.setAutoGenerateInvoicePrintingFileOnPurchaseInvoice(true);
    app.setIsVentilationSkipped(false);
    NativeFinance.invoiceRuntime(app);
    assertFalse(app.getAutoGenerateInvoicePrintingFileOnSaleInvoice());
    assertFalse(app.getIsVentilationSkipped());
    assertTrue(app.getAutoGenerateInvoicePrintingFileOnPurchaseInvoice());
    NativeFinance.invoiceRuntime(app);
    assertFalse(app.getAutoGenerateInvoicePrintingFileOnSaleInvoice());
  }

  @Test void skippedVentilationCannotBeSilentlyAccepted() {
    AppInvoice app = new AppInvoice();
    app.setIsVentilationSkipped(true);
    assertThrows(IllegalStateException.class, () -> NativeFinance.invoiceRuntime(app));
    assertTrue(app.getIsVentilationSkipped());
    assertTrue(app.getAutoGenerateInvoicePrintingFileOnSaleInvoice());
  }
}
