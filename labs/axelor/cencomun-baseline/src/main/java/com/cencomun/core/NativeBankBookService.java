package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Fixed bank-book fixture through native advance receipts; no substitute ledger. */
public class NativeBankBookService {
  private static final String ACCOUNT = "com.axelor.apps.account.db.";
  private static final String BASE = "com.axelor.apps.base.db.";

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> configure() throws Exception {
    NativeIndependentController.fixtureAdmin();
    FixtureBundle.verify();
    Model company = company();
    Model journal = one(ACCOUNT + "Journal", "self.company = ?1 AND self.code = ?2", company, "CCM-BOOK");
    if (journal == null) {
      Model type = record(ACCOUNT + "JournalType", "code", "CCM-BOOK", "name", "CCM LAB bank book", "technicalTypeSelect", 4);
      Model seq = record(BASE + "Sequence", "company", company, "name", "CCM bank book moves",
          "codeSelect", "move", "prefixe", "CCM-BOOK-", "padding", 6, "toBeAdded", 1);
      record(BASE + "SequenceVersion", "sequence", seq, "startDate", LocalDate.of(2026, 1, 1),
          "endDate", LocalDate.of(2026, 12, 31), "nextNum", 1L);
      // The fixed reference contains unallocated advance receipts. A dedicated
      // native journal permits these without altering the economic gate journals.
      journal = record(ACCOUNT + "Journal", "company", company, "name", "CCM LAB advance receipts",
          "code", "CCM-BOOK", "journalType", type, "statusSelect", 1, "sequence", seq, "excessPaymentOk", true);
      Model mode = record(ACCOUNT + "PaymentMode", "name", "CCM LAB bank book receipt", "code", "CCM-BOOK",
          "typeSelect", 9, "inOutSelect", 1, "accountingMethodSelect", 1,
          "accountingTriggerSelect", 1, "moveAccountingDateSelect", 1);
      record(ACCOUNT + "AccountManagement", "company", company, "typeSelect", 3, "paymentMode", mode,
          "cashAccount", one(ACCOUNT + "Account", "self.company = ?1 AND self.code = ?2", company, "CCM-BANK"), "journal", journal);
    }
    return Map.of("company_id", company.getId(), "journal_id", journal.getId(),
        "sequence_id", ((Model) get(journal, "sequence")).getId(), "native_advance_receipts_enabled", get(journal, "excessPaymentOk"));
  }

  /** Called only in a later HTTP request, after the sequence configuration commits. */
  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> post() throws Exception {
    NativeIndependentController.fixtureAdmin();
    FixtureBundle.verify();
    Model company = company();
    Model mode = one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-BOOK");
    if (mode == null) throw new IllegalStateException("Bank-book configuration must commit first");
    for (JsonNode input : FixtureBundle.json("bank-book.json")) {
      Model voucher = one(ACCOUNT + "PaymentVoucher", "self.company = ?1 AND self.ref = ?2", company, input.get("reference").asText());
      if (voucher != null) {
        if (!Integer.valueOf(2).equals(get(voucher, "statusSelect")))
          throw new IllegalStateException("Existing bank-book voucher is not natively confirmed");
        continue;
      }
      Model partner = one(BASE + "Partner", "self.partnerSeq = ?1", input.get("customer_id").asText());
      Model currency = one(BASE + "Currency", "self.codeISO = ?1", input.get("currency").asText());
      if (partner == null || currency == null) throw new IllegalStateException("Native bank-book customer/currency missing");
      voucher = record(ACCOUNT + "PaymentVoucher", "company", company, "partner", partner, "currency", currency,
          "paymentMode", mode, "paymentDate", LocalDate.parse(input.get("date").asText()),
          "ref", input.get("reference").asText(), "paidAmount", new BigDecimal(input.get("amount").asText()),
          "operationTypeSelect", 3, "user", AuthUtils.getUser(),
          "payVoucherElementToPayList", new ArrayList<Model>(), "payVoucherDueElementList", new ArrayList<Model>());
      call(service("com.axelor.apps.account.service.payment.paymentvoucher.PaymentVoucherConfirmService"),
          "confirmPaymentVoucher", voucher);
    }
    return Map.of("native_voucher_ids", list(ACCOUNT + "PaymentVoucher", "self.company = ?1 AND self.paymentMode = ?2", company, mode)
        .stream().map(Model::getId).toList());
  }

  /** Fresh reads prove native payment, posted journal, and unallocated receivable. */
  public Map<String, Object> inspect() throws Exception {
    NativeIndependentController.fixtureAdmin();
    Model company = company();
    Model mode = one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-BOOK");
    List<Map<String, Object>> vouchers = new ArrayList<>();
    if (mode != null) for (Model voucher : list(ACCOUNT + "PaymentVoucher", "self.company = ?1 AND self.paymentMode = ?2", company, mode)) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", voucher.getId()); row.put("reference", get(voucher, "ref"));
      row.put("company_id", company.getId()); row.put("company_code", get(company, "code"));
      row.put("partner_id", ((Model) get(voucher, "partner")).getId()); row.put("customer_id", get(get(voucher, "partner"), "partnerSeq"));
      row.put("currency", get(get(voucher, "currency"), "codeISO")); row.put("payment_date", get(voucher, "paymentDate").toString());
      row.put("paid_amount", get(voucher, "paidAmount").toString()); row.put("remaining_amount", get(voucher, "remainingAmount").toString());
      row.put("status", get(voucher, "statusSelect"));
      row.put("allocation_ids", list(ACCOUNT + "PayVoucherElementToPay", "self.paymentVoucher = ?1", voucher).stream().map(Model::getId).toList());
      Model move = (Model) get(voucher, "generatedMove");
      if (move != null) {
        List<Map<String, Object>> lines = new ArrayList<>();
        for (Object line : (List<?>) get(move, "moveLineList"))
          lines.add(Map.of("id", ((Model) line).getId(), "account", get(get(line, "account"), "code"),
              "debit", get(line, "debit").toString(), "credit", get(line, "credit").toString(),
              "remaining", get(line, "amountRemaining").toString()));
        row.put("move", Map.of("id", move.getId(), "status", get(move, "statusSelect"),
            "voucher_id", ((Model) get(move, "paymentVoucher")).getId(),
            "company_id", ((Model) get(move, "company")).getId(), "date", get(move, "date").toString(), "lines", lines));
      }
      vouchers.add(row);
    }
    return Map.of("vouchers", vouchers, "company_id", company.getId());
  }

  private Model company() {
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    if (company == null) throw new IllegalStateException("Committed native fixture company required");
    return company;
  }
}
