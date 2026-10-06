package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthService;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import jakarta.ws.rs.ForbiddenException;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.WebApplicationException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

/** Payment-day rates are native AOS rows, not a parallel currency table. */
public class NativeFxService {
  private static final String BASE = "com.axelor.apps.base.db.";
  private static final String ACCOUNT = "com.axelor.apps.account.db.";
  private static final String AUTHORIZATION = "com.cencomun.core.db.CcmRateAuthorization";

  static Model require(String code, boolean manager) {
    if (!"1".equals(System.getenv("CCM_CORE_LAB"))) throw new NotFoundException();
    if (AuthUtils.getUser() == null || !AuthUtils.hasRole(AuthUtils.getUser(),
        manager ? new String[]{"CCM Manager"} : new String[]{"CCM Operator", "CCM Manager"}))
      throw new ForbiddenException("Core currency role required");
    Model company = (Model) get(AuthUtils.getUser(), "activeCompany");
    if (company == null || !"CCM-LAB-001".equals(code) || !code.equals(get(company, "code")))
      throw new ForbiddenException("Company denied");
    return company;
  }

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> prepare() throws Exception {
    NativeIndependentController.fixtureAdmin(); FixtureBundle.verify();
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    if (company == null) throw new IllegalStateException("Catalog must commit first");
    Model ves = currency("VES");
    if (ves == null) record(BASE + "Currency", "name", "Bolivar synthetic LAB", "code", "VES", "codeISO", "VES", "numberOfDecimals", 2);
    configurePayments(company);
    // The deterministic LAB clock advances to the last fixture payment day.
    // Keep the native rejection of future invoices, not a validation bypass.
    LocalDate lastDay = LocalDate.MIN;
    for (JsonNode payment : FixtureBundle.json("fx.json").get("payments")) {
      LocalDate day = LocalDate.parse(payment.get("date").asText());
      if (day.isAfter(lastDay)) lastDay = day;
    }
    Model baseApp = (Model) call(service("com.axelor.studio.app.service.AppService"), "getApp", "base");
    set(baseApp, "todayDateT", ZonedDateTime.parse(lastDay + "T10:00:00-04:00")); save(baseApp);
    JsonNode rates = FixtureBundle.json("profile.json").get("rates");
    for (var it = rates.fields(); it.hasNext();) {
      var entry = it.next(); LocalDate day = LocalDate.parse(entry.getKey());
      if (rateAt(day) == null) addRate(day, new BigDecimal(entry.getValue().asText()));
    }
    Model role = one("com.axelor.auth.db.Role", "self.name = ?1", "CCM Manager");
    if (role == null) role = record("com.axelor.auth.db.Role", "name", "CCM Manager", "description", "Synthetic Core rate manager");
    Model user = one("com.axelor.auth.db.User", "self.code = ?1", "ccm-manager");
    if (user == null) user = record("com.axelor.auth.db.User", "code", "ccm-manager", "name", "Synthetic Core Manager",
        "password", AuthService.getInstance().encrypt("CoreLab-manager-2026!"), "email", "manager@example.invalid");
    // Supported custom service enforces the native role on every write; this
    // role gets no general Currency/AppBase CRUD permission.
    set(user, "roles", new HashSet<>(List.of(role))); set(user, "blocked", false);
    set(user, "activeCompany", company); set(user, "companySet", new HashSet<>(List.of(company))); save(user);
    return Map.of("company_id", company.getId(), "manager_id", user.getId(), "native_lab_today", lastDay.toString());
  }

  public Map<String, Object> convert(JsonNode input) {
    require(input.path("company_id").asText(), false);
    LocalDate day = LocalDate.parse(input.path("date").asText());
    if (!input.path("lines").isArray() || input.get("lines").isEmpty())
      throw new WebApplicationException("Payment lines required", 422);
    Object nativeCurrency = service("com.axelor.apps.base.service.CurrencyService");
    BigDecimal rate;
    try { rate = (BigDecimal) call(nativeCurrency, "getCurrencyConversionRate", currency("USD"), currency("VES"), day); }
    catch (NativeFailure failure) {
      if (rateAt(day) == null && failure.getCause().getClass().getName().equals("com.axelor.apps.base.AxelorException"))
        throw new WebApplicationException("Native missing payment-day rate: " + failure.getCause().getMessage(), 422);
      throw failure;
    }
    List<String> lines = new ArrayList<>(); BigDecimal total = BigDecimal.ZERO;
    for (JsonNode item : input.get("lines")) {
      BigDecimal amount = new BigDecimal(item.asText()); MoneyPolicy.positiveMoney(amount);
      BigDecimal converted = (BigDecimal) call(nativeCurrency, "getAmountCurrencyConvertedAtDate", currency("USD"), currency("VES"), amount, day);
      lines.add(converted.setScale(2).toPlainString()); total = total.add(converted);
    }
    Model conversion = rateAt(day);
    return Map.of("id", input.path("id").asText(), "date", day.toString(), "rate", rate.toPlainString(),
        "native_conversion_id", conversion.getId(), "lines", lines, "total", total.setScale(2).toPlainString());
  }

  /** Invoice and every line payment commit together; preparation committed earlier. */
  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> payment(JsonNode input) throws Exception {
    Model company = require(input.path("company_id").asText(), false);
    Map<String, Object> conversion = convert(input); // Missing rate rejects before any effect.
    String id = input.path("id").asText();
    if (!List.of("FX01", "FX02", "MONEY-ROUND").contains(id))
      throw new WebApplicationException("Unknown fixed LAB payment case", 422);
    String reference = "FX-" + id;
    if (one(ACCOUNT + "Invoice", "self.company = ?1 AND self.externalReference = ?2", company, reference) != null)
      throw new WebApplicationException("LAB payment case already posted", 409);
    Model customer = one(BASE + "Partner", "self.partnerSeq = ?1 AND ?2 MEMBER OF self.companySet", "C002", company);
    Model mode = one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-FX");
    if (customer == null || mode == null) throw new IllegalStateException("Committed FX customer/payment configuration required");
    LocalDate day = LocalDate.parse(input.path("date").asText());
    BigDecimal usdTotal = BigDecimal.ZERO;
    for (JsonNode item : input.get("lines")) usdTotal = usdTotal.add(new BigDecimal(item.asText()));
    // The full AOS build supplies this supported InvoiceGenerator subclass.
    Object factory = Beans.get(Class.forName("com.cencomun.core.NativeFxInvoiceFactory"));
    Model invoice = (Model) call(factory, "create", company, customer, mode,
        one(ACCOUNT + "PaymentCondition", "self.code = ?1", "CCM-NET0"), currency("USD"), day, reference);
    Model product = one(BASE + "Product", "self.code = ?1", "P002");
    Model line = create(ACCOUNT + "InvoiceLine");
    set(line, "invoice", invoice); set(line, "product", product); set(line, "productName", get(product, "name"));
    set(line, "unit", get(product, "unit")); set(line, "qty", BigDecimal.ONE); set(line, "price", usdTotal);
    set(line, "account", one(ACCOUNT + "Account", "self.company = ?1 AND self.code = ?2", company, "CCM-REVENUE"));
    set(line, "taxLineSet", new HashSet<>(List.of(NativeFinance.tax(company, BigDecimal.ZERO))));
    call(service("com.axelor.apps.account.service.invoice.InvoiceLineService"), "compute", invoice, line);
    call(invoice, "addInvoiceLineListItem", line); invoice = save(invoice);
    call(service("com.axelor.apps.account.service.invoice.InvoiceService"), "validateAndVentilate", invoice);
    List<Long> payments = new ArrayList<>(); int index = 0;
    for (String value : (List<String>) conversion.get("lines")) {
      invoice = managed(invoice);
      Model payment = (Model) call(service("com.axelor.apps.account.service.payment.invoice.payment.InvoicePaymentCreateService"),
          "createInvoicePayment", invoice, new BigDecimal(value), day, currency("VES"), mode, 2);
      set(payment, "invoicePaymentRef", reference + "-" + (++index));
      set(payment, "description", "Synthetic FX receipt " + reference);
      call(invoice, "addInvoicePaymentListItem", payment);
      call(service("com.axelor.apps.account.service.payment.invoice.payment.InvoiceTermPaymentService"),
          "createInvoicePaymentTerms", payment, null);
      payment = save(payment);
      call(service("com.axelor.apps.account.service.payment.invoice.payment.InvoicePaymentValidateService"), "validate", payment);
      payments.add(payment.getId());
    }
    Map<String, Object> result = new LinkedHashMap<>(conversion);
    result.put("native_invoice_id", invoice.getId()); result.put("native_payment_ids", payments);
    return result;
  }

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> authorize(JsonNode input) {
    Model company = require(input.path("company_id").asText(), true);
    LocalDate day = LocalDate.parse(input.path("date").asText());
    BigDecimal rate = new BigDecimal(input.path("rate").asText());
    String reason = input.path("reason").asText(), id = input.path("id").asText();
    if (rate.signum() <= 0 || rate.stripTrailingZeros().scale() > 6 || reason.isBlank() || id.isBlank())
      throw new WebApplicationException("Positive rate, reason and identifier required", 422);
    if (rateAt(day) != null) throw new WebApplicationException("Payment-day rate already exists", 409);
    Model conversion = addRate(day, rate);
    Model authorization = record(AUTHORIZATION, "company", company, "conversion", conversion,
        "approvedBy", AuthUtils.getUser(), "externalId", id, "reason", reason);
    CoreRecordSupport.audit(company,id,"rate.authorized",Map.of("date",day.toString(),"rate","ABSENT"),
        Map.of("date",day.toString(),"rate",rate.toPlainString(),"native_conversion_id",conversion.getId(),"authorization_id",authorization.getId()),
        reason,input.path("request_key").asText(id),false);
    return Map.of("native_conversion_id", conversion.getId(), "authorization_id", authorization.getId());
  }

  @Transactional(rollbackOn=Exception.class)
  public void rejectedAuthorization(JsonNode input,String reason) {
    if(AuthUtils.getUser()==null)return;
    Model company=one(BASE+"Company","self.code = ?1",input.path("company_id").asText());if(company==null)return;
    Map<String,Object> snapshot=new LinkedHashMap<>();snapshot.put("date",input.path("date").asText());
    try {Model rate=rateAt(LocalDate.parse(input.path("date").asText()));snapshot.put("rate",rate==null?"ABSENT":get(rate,"exchangeRate").toString());}
    catch(java.time.format.DateTimeParseException invalid){snapshot.put("rate","INVALID_DATE");}
    CoreRecordSupport.audit(company,input.path("id").asText("invalid"),"rate.denied",snapshot,snapshot,
        reason,input.path("request_key").asText("invalid-request"),true);
  }

  public Map<String, Object> inspect() {
    NativeIndependentController.fixtureAdmin();
    List<Map<String, Object>> rates = new ArrayList<>(), authorizations = new ArrayList<>();
    for (Model row : list(BASE + "CurrencyConversionLine", "self.startCurrency = ?1 AND self.endCurrency = ?2", currency("USD"), currency("VES")))
      rates.add(Map.of("id", row.getId(), "from_date", get(row, "fromDate").toString(), "to_date", get(row, "toDate").toString(),
          "source", get(get(row, "startCurrency"), "codeISO"), "target", get(get(row, "endCurrency"), "codeISO"), "rate", get(row, "exchangeRate").toString()));
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    for (Model row : list(AUTHORIZATION, "self.company = ?1", company))
      authorizations.add(Map.of("id", row.getId(), "native_conversion_id", ((Model) get(row, "conversion")).getId(),
          "company_id", company.getId(), "external_id", get(row, "externalId"), "reason", get(row, "reason"),
          "approved_by", get(get(row, "approvedBy"), "code")));
    List<Map<String, Object>> invoices = new ArrayList<>(), payments = new ArrayList<>();
    for (Model invoice : list(ACCOUNT + "Invoice", "self.company = ?1 AND self.externalReference in (?2, ?3, ?4)",
        company, "FX-FX01", "FX-FX02", "FX-MONEY-ROUND")) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", invoice.getId()); row.put("reference", get(invoice, "externalReference"));
      row.put("company_id", company.getId()); row.put("customer", get(get(invoice, "partner"), "partnerSeq"));
      row.put("date", get(invoice, "invoiceDate").toString()); row.put("currency", get(get(invoice, "currency"), "codeISO"));
      row.put("status", get(invoice, "statusSelect")); row.put("total", get(invoice, "inTaxTotal").toString());
      row.put("paid", get(invoice, "amountPaid").toString()); row.put("remaining", get(invoice, "amountRemaining").toString());
      if (get(invoice, "move") != null) row.put("move", exportMove((Model) get(invoice, "move")));
      invoices.add(row);
      for (Model payment : list(ACCOUNT + "InvoicePayment", "self.invoice = ?1", invoice)) {
        Map<String, Object> pay = new LinkedHashMap<>();
        pay.put("id", payment.getId()); pay.put("reference", get(payment, "invoicePaymentRef"));
        pay.put("invoice_id", invoice.getId()); pay.put("date", get(payment, "paymentDate").toString());
        pay.put("currency", get(get(payment, "currency"), "codeISO")); pay.put("amount", get(payment, "amount").toString());
        pay.put("status", get(payment, "statusSelect"));
        // Read native daily configuration anew; these are observed lookups,
        // not invented foreign keys on InvoicePayment.
        Model daily = rateAt((LocalDate) get(payment, "paymentDate"));
        if (daily != null) {
          pay.put("observed_payment_day_conversion_id", daily.getId());
          pay.put("observed_payment_day_rate", get(daily, "exchangeRate").toString());
        }
        if (get(payment, "move") != null) pay.put("move", exportMove((Model) get(payment, "move")));
        Model reconcile = (Model) get(payment, "reconcile");
        if (reconcile != null) pay.put("reconcile", Map.of("id", reconcile.getId(), "status", get(reconcile, "statusSelect"),
            "amount", get(reconcile, "amount").toString(), "debit_line_id", ((Model) get(reconcile, "debitMoveLine")).getId(),
            "credit_line_id", ((Model) get(reconcile, "creditMoveLine")).getId()));
        payments.add(pay);
      }
    }
    return Map.of("rates", rates, "authorizations", authorizations, "company_id", company.getId(),
        "company_code", get(company, "code"), "invoices", invoices, "payments", payments,
        "invoice_runtime_configuration", NativeFinance.inspectInvoiceRuntime());
  }

  private static Map<String, Object> exportMove(Model move) {
    List<Map<String, Object>> lines = new ArrayList<>();
    for (Object line : (List<?>) get(move, "moveLineList")) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("id", ((Model) line).getId()); row.put("account", get(get(line, "account"), "code"));
      for (String field : List.of("debit", "credit", "currencyAmount", "currencyRate", "amountRemaining"))
        row.put(field, get(line, field).toString());
      lines.add(row);
    }
    return Map.of("id", move.getId(), "status", get(move, "statusSelect"), "company_id", ((Model) get(move, "company")).getId(),
        "date", get(move, "date").toString(), "currency", get(get(move, "currency"), "codeISO"),
        "company_currency", get(get(move, "companyCurrency"), "codeISO"), "lines", lines);
  }

  private static void configurePayments(Model company) {
    if (one(ACCOUNT + "Journal", "self.company = ?1 AND self.code = ?2", company, "CCM-FX") != null) return;
    Model kind = one(ACCOUNT + "AccountType", "self.technicalTypeSelect = ?1", "cash");
    Model cash = record(ACCOUNT + "Account", "company", company, "name", "CCM LAB cash VES", "code", "CCM-CASH-VES",
        "accountType", kind, "statusSelect", 1, "commonPosition", 0);
    Model type = record(ACCOUNT + "JournalType", "code", "CCM-FX", "name", "CCM LAB VES receipts", "technicalTypeSelect", 4);
    Model seq = record(BASE + "Sequence", "company", company, "name", "CCM FX payment moves", "codeSelect", "move",
        "prefixe", "CCM-FX-", "padding", 6, "toBeAdded", 1);
    record(BASE + "SequenceVersion", "sequence", seq, "startDate", LocalDate.of(2026, 1, 1), "endDate", LocalDate.of(2026, 12, 31), "nextNum", 1L);
    Model ar = one(ACCOUNT + "Account", "self.company = ?1 AND self.code = ?2", company, "CCM-AR");
    Model journal = record(ACCOUNT + "Journal", "company", company, "name", "CCM LAB VES receipts", "code", "CCM-FX",
        "journalType", type, "statusSelect", 1, "sequence", seq, "validAccountSet", new HashSet<>(List.of(cash, ar)));
    Model mode = record(ACCOUNT + "PaymentMode", "name", "CCM LAB cash VES receipt", "code", "CCM-FX", "typeSelect", 5,
        "inOutSelect", 1, "accountingMethodSelect", 1, "accountingTriggerSelect", 1, "moveAccountingDateSelect", 1);
    record(ACCOUNT + "AccountManagement", "company", company, "typeSelect", 3, "paymentMode", mode, "cashAccount", cash, "journal", journal);
    Model config = (Model) get(company, "accountConfig");
    set(config, "generateMoveForInvoicePayment", true); save(config);
  }

  private static Model currency(String code) { return one(BASE + "Currency", "self.codeISO = ?1", code); }
  private static Model rateAt(LocalDate day) {
    return one(BASE + "CurrencyConversionLine", "self.startCurrency = ?1 AND self.endCurrency = ?2 AND self.fromDate <= ?3 AND self.toDate >= ?3", currency("USD"), currency("VES"), day);
  }
  private static Model addRate(LocalDate day, BigDecimal value) {
    Model app = (Model) call(service("com.axelor.studio.app.service.AppService"), "getApp", "base");
    Model line = create(BASE + "CurrencyConversionLine");
    set(line, "appBase", app); set(line, "startCurrency", currency("USD")); set(line, "endCurrency", currency("VES"));
    set(line, "fromDate", day); set(line, "toDate", day); set(line, "exchangeRate", value);
    call(service("com.axelor.apps.base.service.CurrencyService"), "checkOverLappingPeriod", line, get(app, "currencyConversionLineList"));
    line = save(line); call(app, "addCurrencyConversionLineListItem", line); save(app); return line;
  }
}
