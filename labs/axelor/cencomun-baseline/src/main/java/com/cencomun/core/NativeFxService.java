package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthService;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import jakarta.ws.rs.ForbiddenException;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.WebApplicationException;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

/** Payment-day rates are native AOS rows, not a parallel currency table. */
public class NativeFxService {
  private static final String BASE = "com.axelor.apps.base.db.";
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
    return Map.of("company_id", company.getId(), "manager_id", user.getId());
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
    return Map.of("native_conversion_id", conversion.getId(), "authorization_id", authorization.getId());
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
    return Map.of("rates", rates, "authorizations", authorizations);
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
