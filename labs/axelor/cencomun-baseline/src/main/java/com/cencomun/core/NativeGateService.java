package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.Model;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.HashSet;
import com.axelor.auth.AuthUtils;

/** Integration gate against the real pinned AOS services, not an in-memory ledger. */
public class NativeGateService {
  private static final String BASE = "com.axelor.apps.base.db.";
  private static final String STOCK = "com.axelor.apps.stock.db.";
  private static final String SALE = "com.axelor.apps.sale.db.";
  private static final String ACCOUNT = "com.axelor.apps.account.db.";
  private static final LocalDate DATE = LocalDate.of(2026, 10, 1);
  public static final class Progress {
    public String stage = "fixture-integrity";
    public final Map<String, Object> evidence = new LinkedHashMap<>();
    public void stage(String value) { stage = value; }
  }

  public void activate(Progress p) {
    p.stage("native-app-installation");
    Object apps = service("com.axelor.studio.app.service.AppService");
    List<Map<String, Object>> installed = new ArrayList<>();
    for (String code : List.of("base", "sale", "stock", "account", "supplychain")) {
      Model app = one("com.axelor.studio.db.App", "self.code = ?1", code);
      if (app == null) throw new IllegalStateException("Native App metadata missing: " + code);
      if (!Boolean.TRUE.equals(call(apps, "isApp", code))) call(apps, "installApp", app, "en");
      if (!Boolean.TRUE.equals(call(apps, "isApp", code))) throw new IllegalStateException("Native App installation did not activate " + code);
      installed.add(Map.of("code", code, "id", app.getId(), "active", true));
    }
    p.evidence.put("apps", installed);
  }

  @Transactional(rollbackOn = Exception.class)
  public void prepare(Progress p, String caseId) throws Exception {
    p.stage("native-catalog-and-configuration");
    Model usd = one(BASE + "Currency", "self.codeISO = ?1", "USD");
    if (usd == null) usd = record(BASE + "Currency", "name", "US Dollar LAB", "code", "USD", "codeISO", "USD", "numberOfDecimals", 2);
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    if (company == null) company = record(BASE + "Company", "code", "CCM-LAB-001", "name", "Cencomun synthetic LAB", "currency", usd);
    Model unit = one(BASE + "Unit", "self.name = ?1", "CCM-LAB-UNIT");
    if (unit == null) unit = record(BASE + "Unit", "name", "CCM-LAB-UNIT");
    Model warehouse = location(company, "WH-LAB-001-" + caseId, 1, true);
    Model supplierLocation = location(company, "CCM-LAB-SUPPLIER", 3, false);
    Model customerLocation = location(company, "CCM-LAB-CUSTOMER", 3, false);
    Model stockConfig = one(STOCK + "StockConfig", "self.company = ?1", company);
    if (stockConfig == null) {
      stockConfig = record(STOCK + "StockConfig", "company", company,
          "receiptDefaultStockLocation", warehouse, "pickupDefaultStockLocation", warehouse,
          "customerVirtualStockLocation", customerLocation, "supplierVirtualStockLocation", supplierLocation,
          "inventoryVirtualStockLocation", supplierLocation, "stockValuationTypeSelect", 5, "inventoryValuationTypeSelect", 5);
      set(company, "stockConfig", stockConfig); save(company);
    }
    sequence(company, "inStockMove"); sequence(company, "outStockMove"); sequence(company, "saleOrder");
    Object apps = service("com.axelor.studio.app.service.AppService");
    Model appBase = (Model) call(apps, "getApp", "base");
    if (appBase == null) throw new IllegalStateException("Native AppBase missing after supported installation");
    set(appBase, "todayDateT", ZonedDateTime.parse("2026-10-01T10:00:00-04:00"));
    set(appBase, "nbDecimalDigitForUnitPrice", 2); set(appBase, "nbDecimalDigitForQty", 2);
    set(appBase, "nbDecimalDigitForTaxRate", 6); save(appBase);
    for (JsonNode fixture : FixtureBundle.json("products.json")) {
      String code = fixture.get("id").asText();
      Model product = one(BASE + "Product", "self.code = ?1", code);
      if (product == null) product = record(BASE + "Product", "code", code, "name", fixture.get("name").asText(),
          "unit", unit, "salePrice", dec(fixture, "price"), "purchasePrice", dec(fixture, "cost"),
          "costPrice", dec(fixture, "cost"), "stockManaged", true, "costTypeSelect", 3, "productTypeSelect", "storable",
          "saleCurrency", usd, "purchaseCurrency", usd);
    }
    // The native Partner repository initializes AccountingSituation for companySet.
    // It requires the company's real AccountConfig before any associated partner save.
    NativeFinance.configure(company);
    NativeFinance.configureCompanyPartner(company);
    for (JsonNode fixture : FixtureBundle.json("customers.json")) {
      Model partner = one(BASE + "Partner", "self.partnerSeq = ?1", fixture.get("id").asText());
      if (partner == null) {
        Model email = record("com.axelor.message.db.EmailAddress", "address", fixture.get("email").asText());
        partner = record(BASE + "Partner", "partnerSeq", fixture.get("id").asText(),
            "name", fixture.get("name").asText(), "mobilePhone", fixture.get("phone").asText(), "emailAddress", email,
            "companySet", new HashSet<>(List.of(company)), "isCustomer", true, "partnerTypeSelect", 2, "currency", usd);
      }
      NativeFinance.configurePartner(company, partner);
    }
    Model customer = one(BASE + "Partner", "self.partnerSeq = ?1", "C001");
    set(AuthUtils.getUser(), "activeCompany", company);
    set(AuthUtils.getUser(), "companySet", new HashSet<>(List.of(company))); save(AuthUtils.getUser());
    if (one(SALE + "SaleConfig", "self.company = ?1", company) == null) {
      Model config = record(SALE + "SaleConfig", "company", company);
      set(company, "saleConfig", config); save(company);
    }
    if (one("com.axelor.apps.supplychain.db.SupplyChainConfig", "self.company = ?1", company) == null) {
      record("com.axelor.apps.supplychain.db.SupplyChainConfig", "company", company);
    }
    NativeFinance.tax(company, BigDecimal.ZERO);
    NativeFinance.tax(company, new BigDecimal("0.10"));
    p.evidence.put("company_id", company.getId());
    p.evidence.put("warehouse_id", warehouse.getId());
    p.evidence.put("customer_id", customer.getId());
    p.stage("native-fixture-prepared");
  }

  /** Fixture receipt runs only after the preparation HTTP request has committed.
   * Native Sequence reservations read configuration in a separate TenantAware transaction.
   * Flushing the preparing transaction would not make its rows visible to that reader.
   */
  @Transactional(rollbackOn = Exception.class)
  public void seed(Progress p, String caseId) throws Exception {
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    Model warehouse = one(STOCK + "StockLocation", "self.name = ?1", "WH-LAB-001-" + caseId);
    Model supplierLocation = one(STOCK + "StockLocation", "self.name = ?1", "CCM-LAB-SUPPLIER");
    Model customer = one(BASE + "Partner", "self.partnerSeq = ?1", "C001");
    Model unit = one(BASE + "Unit", "self.name = ?1", "CCM-LAB-UNIT");
    if (company == null || warehouse == null || supplierLocation == null || customer == null || unit == null)
      throw new IllegalStateException("Fixture preparation must commit before the stock receipt");
    p.stage("native-initial-stock-receipt");
    Object stock = service("com.axelor.apps.stock.service.StockMoveService");
    Model move = (Model) call(stock, "createStockMove", null, null, company,
        supplierLocation, warehouse, DATE, DATE, "CCM initial fixture " + caseId, 3);
    Object lines = service("com.axelor.apps.stock.service.StockMoveLineService");
    for (JsonNode fixture : FixtureBundle.json("products.json")) {
      Model product = one(BASE + "Product", "self.code = ?1", fixture.get("id").asText());
      BigDecimal cost = dec(fixture, "cost");
      Model line = (Model) call(lines, "createStockMoveLine", product, get(product, "name"), "LAB initial stock",
          BigDecimal.valueOf(fixture.get("stock").asInt()), cost, cost, unit, move, 2, false,
          BigDecimal.ZERO, supplierLocation, warehouse);
      set(line, "realQty", BigDecimal.valueOf(fixture.get("stock").asInt()));
      call(move, "addStockMoveLineListItem", line);
    }
    move = save(move); call(stock, "plan", move);
    move = managed(move);
    p.evidence.put("planned_initial_stock_move_id", move.getId());
    p.evidence.put("planned_initial_stock_move_status", get(move, "statusSelect"));
    if (!Integer.valueOf(2).equals(get(move, "statusSelect"))) throw new IllegalStateException("Native plan did not persist PLANNED");
    call(stock, "realize", move); move = managed(move);
    company = managed(company); customer = managed(customer); warehouse = managed(warehouse);
    p.stage("native-initial-stock-accounting");
    NativeFinance.opening(company, customer, warehouse, caseId);
    p.evidence.put("initial_stock_move_id", move.getId());
    p.evidence.put("initial_stock_move_status", get(move, "statusSelect"));
  }

  @Transactional(rollbackOn = Exception.class)
  public void sell(Progress p, JsonNode input) {
    String caseId = input.get("id").asText();
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    Model customer = one(BASE + "Partner", "self.partnerSeq = ?1", "C001");
    Model warehouse = one(STOCK + "StockLocation", "self.name = ?1", "WH-LAB-001-" + caseId);
    p.stage("native-sale-order");
    Model so = (Model) call(service("com.axelor.apps.sale.service.saleorder.SaleOrderCreateService"), "createSaleOrder",
        AuthUtils.getUser(), company, null, get(company, "currency"), DATE,
        null, "CCM-" + caseId, null, customer, null, null, null, null);
    p.evidence.put("native_created_sale_order_status", get(so, "statusSelect"));
    set(so, "orderDate", DATE);
    set(so, "externalReference", "CCM-" + caseId); set(so, "stockLocation", warehouse); set(so, "inAti", true);
    set(so, "paymentMode", one(ACCOUNT + "PaymentMode", "self.code = ?1", "CCM-CASH"));
    set(so, "paymentCondition", one(ACCOUNT + "PaymentCondition", "self.code = ?1", "CCM-NET0"));
    List<Model> saleLines = new ArrayList<>();
    for (JsonNode item : input.get("lines")) {
      Model product = one(BASE + "Product", "self.code = ?1", item.get("product_id").asText());
      Model line = create(SALE + "SaleOrderLine");
      set(line, "saleOrder", so); set(line, "product", product); set(line, "productName", get(product, "name"));
      set(line, "unit", get(product, "unit")); set(line, "qty", dec(item, "qty"));
      set(line, "price", dec(item, "unit_price")); set(line, "inTaxPrice", dec(item, "unit_price"));
      set(line, "taxLineSet", new HashSet<>(List.of(NativeFinance.tax(company, dec(input, "tax_rate")))));
      saleLines.add(line);
    }
    set(so, "saleOrderLineList", saleLines); so = save(so);
    call(service("com.axelor.apps.sale.service.saleorder.SaleOrderComputeService"), "computeSaleOrder", so);
    so = managed(so);
    p.stage("native-sale-order-finalization");
    call(service("com.axelor.apps.sale.service.saleorder.status.SaleOrderFinalizeService"), "finalizeQuotation", so);
    so = managed(so);
    p.stage("native-sale-order-confirmation");
    call(service("com.axelor.apps.sale.service.saleorder.status.SaleOrderConfirmService"), "confirmSaleOrder", so);
    so = managed(so);
    p.stage("native-sale-delivery");
    Object moveIds = call(service("com.axelor.apps.supplychain.service.saleorder.SaleOrderStockService"), "createStocksMovesFromSaleOrder", so);
    if (!(moveIds instanceof List<?> ids) || ids.size() != 1) throw new IllegalStateException("Expected exactly one native delivery");
    Model delivery = one(STOCK + "StockMove", "self.id = ?1", ids.getFirst());
    if (input.get("guide") != null && !input.get("guide").isNull()) set(delivery, "trackingNumber", input.get("guide").asText());
    Object stock = service("com.axelor.apps.stock.service.StockMoveService");
    // createStocksMovesFromSaleOrder already calls the native planWithNoSplit.
    call(stock, "copyQtyToRealQty", delivery); delivery = managed(delivery);
    call(stock, "realize", delivery); delivery = managed(delivery); so = managed(so);
    p.stage("native-invoice-generation");
    int invoiceAll;
    try { invoiceAll = type(SALE + "repo.SaleOrderRepository").getField("INVOICE_ALL").getInt(null); }
    catch (ReflectiveOperationException error) {
      throw new IllegalStateException("Pinned native INVOICE_ALL unavailable", error);
    }
    Object invoicing = service("com.axelor.apps.supplychain.service.saleorder.SaleOrderInvoiceService");
    // Same native guard and full overload as the pinned invoicing wizard.
    // INVOICE_ALL does not consume quantity maps or timetable selections.
    call(invoicing, "displayErrorMessageIfSaleOrderIsInvoiceable", so, BigDecimal.ZERO,
        invoiceAll, Map.of(), Map.of(), Map.of(), false);
    Model invoice = (Model) call(invoicing, "generateInvoice", so, invoiceAll,
        BigDecimal.ZERO, false, Map.of(), List.of());
    if (caseId.equals("CO00")) try {
      set(invoice, "externalReference", FixtureBundle.json("scenarios.json").get("search").get("invoice").get("reference").asText());
    } catch (java.io.IOException error) { throw new IllegalStateException("Fixed search fixture unavailable", error); }
    set(invoice, "invoiceDate", DATE); invoice = save(invoice);
    call(service("com.axelor.apps.account.service.invoice.InvoiceService"), "validateAndVentilate", invoice);
    invoice = managed(invoice); delivery = managed(delivery);
    company = managed(company); customer = managed(customer);
    p.evidence.put("sale_order_id", so.getId()); p.evidence.put("delivery_id", delivery.getId());
    p.evidence.put("invoice_id", invoice.getId());
    p.stage("native-cogs-and-settlement");
    p.evidence.put("finance", NativeFinance.post(company, customer, delivery, invoice, input));
    p.stage("native-flow-complete");
  }

  /** Fresh repository reads after success/rollback; transient IDs never count as evidence. */
  public Map<String, Object> inspect(String caseId) {
    Map<String, Object> result = new LinkedHashMap<>();
    Model company = one(BASE + "Company", "self.code = ?1", "CCM-LAB-001");
    result.put("case", caseId);
    List<Map<String, Object>> quantities = new ArrayList<>();
    Model warehouse = one(STOCK + "StockLocation", "self.name = ?1", "WH-LAB-001-" + caseId);
    if (warehouse != null) {
      for (Model line : list(STOCK + "StockLocationLine", "self.stockLocation = ?1", warehouse)) {
        Model product = (Model) get(line, "product");
        quantities.add(Map.of("id", line.getId(), "product_id", product.getId(), "code", get(product, "code"),
            "current_qty", get(line, "currentQty").toString(), "avg_price", get(line, "avgPrice").toString()));
      }
      result.put("stock", quantities);
      result.put("stock_move_ids", list(STOCK + "StockMove", "self.fromStockLocation = ?1 OR self.toStockLocation = ?1", warehouse)
          .stream().map(Model::getId).toList());
    } else { result.put("stock", List.of()); result.put("stock_move_ids", List.of()); }
    result.put("fixture_configuration", company == null ? Map.of() : NativeFinance.inspectConfiguration(company));
    result.put("sale_order_ids", list(SALE + "SaleOrder", "self.externalReference = ?1", "CCM-" + caseId).stream().map(Model::getId).toList());
    List<Map<String, Object>> invoices = new ArrayList<>();
    List<Map<String, Object>> moves = new ArrayList<>();
    for (Model so : list(SALE + "SaleOrder", "self.externalReference = ?1", "CCM-" + caseId)) {
      // Preserve the official reader and independently verify header and line FKs.
      for (Model invoice : (List<Model>) call(service(
          "com.axelor.apps.supplychain.service.saleorder.SaleOrderInvoiceService"), "getInvoices", so)) {
        Map<String, Object> inv = new LinkedHashMap<>();
        inv.put("id", invoice.getId());
        inv.put("native_source_linkage", NativeInvoiceLinks.inspect(invoice));
        Model address = (Model) get(invoice, "address");
        inv.put("invoicing_address_id", address == null ? 0L : address.getId());
        inv.put("native_vat_liability", get(invoice, "vatSystemSelect"));
        for (String field : List.of("statusSelect", "exTaxTotal", "taxTotal", "inTaxTotal", "amountPaid", "amountRemaining"))
          inv.put(field, String.valueOf(get(invoice, field)));
        List<Map<String, Object>> invoiceLines = new ArrayList<>();
        for (Object item : (List<?>) get(invoice, "invoiceLineList")) {
          Model product = (Model) get(item, "product");
          if (product != null) invoiceLines.add(Map.of("id", ((Model) item).getId(), "product_id", product.getId(),
              "code", get(product, "code"), "qty", get(item, "qty").toString(),
              "ex_tax_total", get(item, "exTaxTotal").toString(), "in_tax_total", get(item, "inTaxTotal").toString()));
        }
        inv.put("lines", invoiceLines);
        List<Map<String, Object>> payments = new ArrayList<>();
        for (Model pay : list(ACCOUNT + "InvoicePayment", "self.invoice = ?1", invoice)) {
          payments.add(Map.of("id", pay.getId(), "amount", get(pay, "amount").toString(), "status", get(pay, "statusSelect")));
          Model move = (Model) get(pay, "move"); if (move != null) moves.add(exportMove(move));
        }
        inv.put("payments", payments); invoices.add(inv);
        Model move = (Model) get(invoice, "move"); if (move != null) moves.add(exportMove(move));
      }
    }
    for (Model move : list(ACCOUNT + "Move", "self.origin = ?1 OR self.origin = ?2", "CCM-" + caseId + "-COGS", "CCM-" + caseId + "-SETTLE"))
      if (moves.stream().noneMatch(m -> move.getId().equals(m.get("id")))) moves.add(exportMove(move));
    result.put("invoices", invoices); result.put("moves", moves);
    result.put("fixture_opening_moves", list(ACCOUNT + "Move", "self.origin = ?1", "CCM-" + caseId + "-OPENING")
        .stream().map(this::exportMove).toList());
    List<Map<String, Object>> deliveries = new ArrayList<>();
    if (warehouse != null) for (Model move : list(STOCK + "StockMove", "self.fromStockLocation = ?1", warehouse))
      deliveries.add(Map.of("id", move.getId(), "status", get(move, "statusSelect"), "type", get(move, "typeSelect")));
    result.put("deliveries", deliveries);
    result.put("company_ids", list(BASE + "Company", "self.code = ?1", "CCM-LAB-001").stream().map(Model::getId).toList());
    List<Map<String, Object>> sequences = new ArrayList<>();
    if (company != null) for (Model seq : list(BASE + "Sequence", "self.company = ?1", company)) {
      List<Map<String, Object>> versions = new ArrayList<>();
      for (Model version : list(BASE + "SequenceVersion", "self.sequence = ?1", seq))
        versions.add(Map.of("id", version.getId(), "next_num", get(version, "nextNum"),
            "start_date", get(version, "startDate").toString(), "end_date", get(version, "endDate").toString()));
      sequences.add(Map.of("id", seq.getId(), "code", get(seq, "codeSelect"), "prefix", get(seq, "prefixe"), "versions", versions));
    }
    result.put("sequences", sequences);
    return result;
  }
  private Map<String, Object> exportMove(Model move) {
    List<Map<String, Object>> lines = new ArrayList<>();
    for (Object line : (List<?>) get(move, "moveLineList")) {
      Model account = (Model) get(line, "account");
      lines.add(Map.of("id", ((Model) line).getId(), "account_id", account.getId(), "account_code", get(account, "code"),
          "debit", get(line, "debit").toString(), "credit", get(line, "credit").toString(), "remaining", get(line, "amountRemaining").toString()));
    }
    return Map.of("id", move.getId(), "status", get(move, "statusSelect"), "lines", lines);
  }
  private Model location(Model company, String name, int kind, boolean valued) {
    Model found = one(STOCK + "StockLocation", "self.name = ?1", name);
    return found != null ? found : record(STOCK + "StockLocation", "company", company, "name", name, "typeSelect", kind, "isValued", valued);
  }
  private void sequence(Model company, String code) {
    if (one(BASE + "Sequence", "self.company = ?1 AND self.codeSelect = ?2", company, code) != null) return;
    Model seq = record(BASE + "Sequence", "company", company, "name", "CCM LAB " + code, "codeSelect", code,
        "prefixe", "CCM-" + code + "-", "padding", 6, "toBeAdded", 1);
    record(BASE + "SequenceVersion", "sequence", seq, "startDate", LocalDate.of(2026, 1, 1),
        "endDate", LocalDate.of(2026, 12, 31), "nextNum", 1L);
  }
  public static Model record(String type, Object... properties) {
    Model model = create(type);
    for (int i = 0; i < properties.length; i += 2) set(model, (String) properties[i], properties[i + 1]);
    return save(model);
  }
  private static BigDecimal dec(JsonNode obj, String key) { return new BigDecimal(obj.get(key).asText()); }
}
