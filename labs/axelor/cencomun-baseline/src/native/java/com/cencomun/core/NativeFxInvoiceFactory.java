package com.cencomun.core;

import com.axelor.apps.account.db.Invoice;
import com.axelor.apps.account.db.PaymentCondition;
import com.axelor.apps.account.db.PaymentMode;
import com.axelor.apps.account.db.repo.InvoiceRepository;
import com.axelor.apps.account.service.invoice.generator.InvoiceGenerator;
import com.axelor.apps.base.AxelorException;
import com.axelor.apps.base.db.Company;
import com.axelor.apps.base.db.Currency;
import com.axelor.apps.base.db.Partner;
import com.axelor.db.Model;
import java.time.LocalDate;

/** Official AOS invoice header initialization; no recreated status transition. */
public class NativeFxInvoiceFactory {
  public Model create(Model company, Model partner, Model mode, Model condition,
      Model currency, LocalDate day, String reference) throws AxelorException {
    Invoice invoice = new InvoiceGenerator(InvoiceRepository.OPERATION_TYPE_CLIENT_SALE,
        (Company) company, (PaymentCondition) condition, (PaymentMode) mode, null,
        (Partner) partner, null, (Currency) currency, null, reference, reference,
        false, null, null, false, null) {
      @Override public Invoice generate() throws AxelorException { return createInvoiceHeader(); }
    }.generate();
    invoice.setInvoiceDate(day);
    return invoice;
  }
}
