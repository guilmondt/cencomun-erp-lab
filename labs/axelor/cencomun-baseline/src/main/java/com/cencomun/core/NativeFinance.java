package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.HashSet;

/** Synthetic native chart/period configuration and supported journal posting services. */
public final class NativeFinance {
  private static final String ACCOUNT = "com.axelor.apps.account.db.";
  private static final String BASE = "com.axelor.apps.base.db.";
  private static final LocalDate DATE = LocalDate.of(2026, 10, 1);

  public static void configure(Model company) {
    if (one(ACCOUNT + "AccountConfig", "self.company = ?1", company) != null) {
      configureJournalAccounts(company);
      return;
    }
    account(company, "AR", "receivable", true); account(company, "AP", "payable", true);
    account(company, "STOCK", "currentAsset", false); account(company, "REVENUE", "income", false);
    account(company, "COGS", "charge", false); account(company, "COMMISSION", "charge", false);
    account(company, "SHIPPING", "charge", false); account(company, "TAX", "tax", false);
    account(company, "CASH", "cash", false); account(company, "BANK", "cash", false);
    account(company, "OPENING", "equity", false);
    Model sale = journal(company, "SALE", 2); Model general = journal(company, "GENERAL", 5);
    Model cash = journal(company, "CASH", 4); Model bank = journal(company, "BANK", 4);
    configureJournalAccounts(company);
    Model config = record(ACCOUNT + "AccountConfig", "company", company,
        "customerAccount", acct(company, "AR"), "supplierAccount", acct(company, "AP"),
        "customerSalesJournal", sale, "customerCreditNoteJournal", sale,
        "supplierPurchaseJournal", general, "supplierCreditNoteJournal", general,
        "autoMiscOpeJournal", general, "manualMiscOpeJournal", general,
        "saleJournalType", get(sale, "journalType"), "cashJournalType", get(cash, "journalType"));
    set(company, "accountConfig", config); save(company);
    Model invoiceSeq = sequence(company, "invoice", "INV");
    set(config, "custInvSequence", invoiceSeq); set(config, "custRefSequence", sequence(company, "invoice", "REF")); save(config);
    for (String code : List.of("reconcile", "reconcileGroupDraft", "reconcileGroupFinal")) sequence(company, code, code);
    Model year = record(BASE + "Year", "company", company, "code", "CCM-2026", "name", "CCM LAB fiscal 2026",
        "fromDate", LocalDate.of(2026, 1, 1), "toDate", LocalDate.of(2026, 12, 31), "typeSelect", 1);
    record(BASE + "Period", "year", year, "name", "CCM October 2026", "code", "CCM-2026-10",
        "fromDate", LocalDate.of(2026, 10, 1), "toDate", LocalDate.of(2026, 10, 31));
    mode(company, "CASH", 5, cash); mode(company, "BANK", 9, bank);
    Model condition = record(ACCOUNT + "PaymentCondition", "code", "CCM-NET0", "name", "CCM LAB due immediately");
    Model term = record(ACCOUNT + "PaymentConditionLine", "paymentCondition", condition,
        "typeSelect", 1, "sequence", 1, "periodTypeSelect", 1, "paymentTime", 0, "paymentPercentage", new BigDecimal("100"));
    set(condition, "paymentConditionLineList", new ArrayList<>(List.of(term))); save(condition);
    for (Model product : list(BASE + "Product", "self.code in (?1, ?2, ?3)", "P001", "P002", "P003")) {
      record(ACCOUNT + "AccountManagement", "company", company, "typeSelect", 1,
          "product", product, "saleAccount", acct(company, "REVENUE"), "purchaseAccount", acct(company, "COGS"));
    }
  }

  public static void opening(Model company, Model customer, Model warehouse, String caseId) {
    BigDecimal amount = BigDecimal.ZERO;
    for (Model row : list("com.axelor.apps.stock.db.StockLocationLine", "self.stockLocation = ?1", warehouse))
      amount = amount.add(((BigDecimal) get(row, "currentQty")).multiply((BigDecimal) get(row, "avgPrice")));
    if (amount.signum() <= 0) throw new IllegalStateException("Native initial stock has no positive valuation");
    Model opening = move(company, customer, "GENERAL", null, "CCM-" + caseId + "-OPENING");
    List<Model> lines = new ArrayList<>();
    lines.add(line(opening, customer, acct(company, "STOCK"), MoneyPolicy.money(amount), true, 1));
    lines.add(line(opening, customer, acct(company, "OPENING"), MoneyPolicy.money(amount), false, 2));
    appendLines(opening, lines); opening = save(opening);
    call(service("com.axelor.apps.account.service.move.MoveValidateService"), "accounting", opening);
  }

  public static Model tax(Model company, BigDecimal fraction) {
    String code = fraction.signum() == 0 ? "CCM-BASE" : "TAX-LAB-10";
    Model existing = one(ACCOUNT + "Tax", "self.code = ?1", code);
    if (existing != null) return (Model) get(existing, "activeTaxLine");
    Model type = one(ACCOUNT + "TaxType", "self.code = ?1", "CCM-LAB-VAT");
    if (type == null) type = record(ACCOUNT + "TaxType", "name", "Synthetic LAB VAT", "code", "CCM-LAB-VAT", "typeSelect", 1);
    Model tax = record(ACCOUNT + "Tax", "name", code, "code", code, "taxType", type);
    Model line = record(ACCOUNT + "TaxLine", "tax", tax, "value", fraction.multiply(new BigDecimal("100")),
        "startDate", LocalDate.of(2026, 1, 1), "endDate", LocalDate.of(2026, 12, 31));
    set(tax, "activeTaxLine", line); save(tax);
    record(ACCOUNT + "AccountManagement", "company", company, "typeSelect", 2, "tax", tax,
        "saleTaxVatSystem1Account", acct(company, "TAX"), "saleTaxVatSystem2Account", acct(company, "TAX"),
        "purchaseTaxVatSystem1Account", acct(company, "TAX"), "purchaseTaxVatSystem2Account", acct(company, "TAX"));
    return line;
  }

  public static Map<String, Object> post(Model company, Model customer, Model delivery, Model invoice, JsonNode input) {
    // Cost is observed from native realized StockMoveLine WAP, not fixture cost or oracle.
    Map<String, BigDecimal> costs = new LinkedHashMap<>(); BigDecimal totalCost = BigDecimal.ZERO;
    for (Object item : (List<?>) get(delivery, "stockMoveLineList")) {
      Model product = (Model) get(item, "product");
      BigDecimal wap = (BigDecimal) get(item, "wapPrice");
      costs.put((String) get(product, "code"), wap);
      totalCost = totalCost.add(((BigDecimal) get(item, "realQty")).multiply(wap));
    }
    Map<String, BigDecimal> calculation = MoneyPolicy.calculate(input, costs);
    Model cogs = move(company, customer, "GENERAL", null, "CCM-" + input.get("id").asText() + "-COGS");
    List<Model> costLines = new ArrayList<>();
    costLines.add(line(cogs, customer, acct(company, "COGS"), MoneyPolicy.money(totalCost), true, 1));
    costLines.add(line(cogs, customer, acct(company, "STOCK"), MoneyPolicy.money(totalCost), false, 2));
    appendLines(cogs, costLines); cogs = save(cogs);
    call(service("com.axelor.apps.account.service.move.MoveValidateService"), "accounting", cogs);
    invoice = managed(invoice);
    Object createPayment = service("com.axelor.apps.account.service.payment.invoice.payment.InvoicePaymentCreateService");
    Model currency = (Model) get(company, "currency");
    Model cashMode = one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-CASH");
    Model upfront = (Model) call(createPayment, "createInvoicePayment", invoice, calculation.get("upfront"), DATE, currency, cashMode, 2);
    upfront = save(upfront);
    call(service("com.axelor.apps.account.service.payment.invoice.payment.InvoicePaymentValidateService"), "validate", upfront);
    company = managed(company); customer = managed(customer);
    Model bankMode = one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-BANK");
    Model settle = move(company, customer, "BANK", bankMode, "CCM-" + input.get("id").asText() + "-SETTLE");
    List<Model> settlementLines = new ArrayList<>();
    settlementLines.add(line(settle, customer, acct(company, "BANK"), calculation.get("transfer"), true, 1));
    settlementLines.add(line(settle, customer, acct(company, "COMMISSION"), calculation.get("commission"), true, 2));
    if (calculation.get("shipping").signum() != 0) settlementLines.add(line(settle, customer, acct(company, "SHIPPING"), calculation.get("shipping"), true, 3));
    Model credit = line(settle, customer, acct(company, "AR"), new BigDecimal(input.get("financed_amount").asText()), false, 4);
    settlementLines.add(credit); appendLines(settle, settlementLines); settle = save(settle);
    call(service("com.axelor.apps.account.service.move.MoveValidateService"), "accounting", settle);
    invoice = managed(invoice); credit = managed(credit);
    Model invoiceMove = (Model) get(invoice, "move");
    Model invoiceDebit = null;
    for (Object candidate : (List<?>) get(invoiceMove, "moveLineList"))
      if (acct(company, "AR").equals(get(candidate, "account")) && ((BigDecimal) get(candidate, "debit")).signum() > 0) invoiceDebit = (Model) candidate;
    if (invoiceDebit == null) throw new IllegalStateException("Native invoice receivable debit missing");
    // Reconciliation updates native InvoicePayments/terms through the framework service.
    Model reconciliation = (Model) call(service("com.axelor.apps.account.service.reconcile.ReconcileService"), "reconcile", invoiceDebit, credit, false, true);
    return Map.of("cogs_move_id", cogs.getId(), "settlement_move_id", settle.getId(), "reconcile_id", reconciliation.getId(), "upfront_payment_id", upfront.getId(),
        "native_wap_costs", costs, "calculation", calculation);
  }
  private static Model move(Model company, Model partner, String journal, Model mode, String origin) {
    Model j = one(ACCOUNT + "Journal", "self.company = ?1 AND self.code = ?2", company, "CCM-" + journal);
    return (Model) call(service("com.axelor.apps.account.service.move.MoveCreateService"), "createMove", j, company,
        get(company, "currency"), partner, DATE, DATE, mode, null, 2, mode == null ? 6 : 5, origin, origin, null);
  }
  private static Model line(Model move, Model partner, Model account, BigDecimal amount, boolean debit, int n) {
    return (Model) call(service("com.axelor.apps.account.service.moveline.MoveLineCreateService"), "createMoveLine", move, partner, account,
        amount, debit, DATE, n, get(move, "origin"), "CCM synthetic Core posting");
  }
  private static Model acct(Model company, String category) { return one(ACCOUNT + "Account", "self.company = ?1 AND self.code = ?2", company, "CCM-" + category); }
  private static void appendLines(Model move, List<Model> lines) {
    // createMove already persists its collection; retain Hibernate's collection
    // and use the generated native relationship helper, as the ERP does.
    for (Model line : lines) call(move, "addMoveLineListItem", line);
  }
  private static void configureJournalAccounts(Model company) {
    journalAccounts(company, "SALE", "AR", "REVENUE", "TAX");
    journalAccounts(company, "GENERAL", "STOCK", "OPENING", "COGS", "AP");
    journalAccounts(company, "CASH", "CASH", "AR");
    journalAccounts(company, "BANK", "BANK", "AR", "COMMISSION", "SHIPPING");
  }
  static void journalAccounts(Model company, String code, String... categories) {
    Model journal = one(ACCOUNT + "Journal", "self.company = ?1 AND self.code = ?2", company, "CCM-" + code);
    if (journal == null) throw new IllegalStateException("Synthetic journal missing: " + code);
    HashSet<Model> accounts = new HashSet<>();
    for (String category : categories) {
      Model account = acct(company, category);
      if (account == null) throw new IllegalStateException("Synthetic account missing: " + category);
      accounts.add(account);
    }
    set(journal, "validAccountSet", accounts); save(journal);
  }
  private static void account(Model company, String code, String type, boolean reconcile) {
    Model kind = one(ACCOUNT + "AccountType", "self.technicalTypeSelect = ?1", type);
    if (kind == null) kind = record(ACCOUNT + "AccountType", "name", "CCM LAB " + type, "technicalTypeSelect", type);
    record(ACCOUNT + "Account", "company", company, "name", "CCM LAB " + code, "code", "CCM-" + code,
        "accountType", kind, "commonPosition", 0, "statusSelect", 1, "reconcileOk", reconcile, "useForPartnerBalance", reconcile);
  }
  private static Model journal(Model company, String code, int kind) {
    Model type = one(ACCOUNT + "JournalType", "self.code = ?1", "CCM-" + code);
    if (type == null) type = record(ACCOUNT + "JournalType", "name", "CCM LAB " + code, "code", "CCM-" + code, "technicalTypeSelect", kind);
    Model sequence = record(BASE + "Sequence", "company", company, "name", "CCM journal " + code, "codeSelect", "move",
        "prefixe", "CCM-" + code + "-", "padding", 6, "toBeAdded", 1);
    record(BASE + "SequenceVersion", "sequence", sequence, "startDate", LocalDate.of(2026, 1, 1), "endDate", LocalDate.of(2026, 12, 31), "nextNum", 1L);
    return record(ACCOUNT + "Journal", "company", company, "name", "CCM LAB " + code, "code", "CCM-" + code, "journalType", type,
        "statusSelect", 1, "sequence", sequence);
  }
  private static Model sequence(Model company, String code, String prefix) {
    Model seq = record(BASE + "Sequence", "company", company, "name", "CCM " + prefix,
        "codeSelect", code, "prefixe", "CCM-" + prefix + "-", "padding", 6, "toBeAdded", 1);
    record(BASE + "SequenceVersion", "sequence", seq, "startDate", LocalDate.of(2026, 1, 1),
        "endDate", LocalDate.of(2026, 12, 31), "nextNum", 1L);
    return seq;
  }
  private static void mode(Model company, String code, int kind, Model journal) {
    Model mode = record(ACCOUNT + "PaymentMode", "name", "CCM LAB " + code, "code", "CCM-" + code, "typeSelect", kind,
        "inOutSelect", 1, "accountingMethodSelect", 1, "accountingTriggerSelect", 1, "moveAccountingDateSelect", 1);
    record(ACCOUNT + "AccountManagement", "company", company, "typeSelect", 3, "paymentMode", mode, "cashAccount", acct(company, code), "journal", journal);
  }
  private NativeFinance() {}
}
