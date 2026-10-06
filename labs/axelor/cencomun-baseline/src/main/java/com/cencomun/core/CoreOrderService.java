package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthUtils;
import com.axelor.db.JPA;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.inject.persist.Transactional;
import jakarta.persistence.LockModeType;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.stream.Collectors;

/** Authenticated native ERP workflow. Economic effects, key, audit and outbox commit together. */
public class CoreOrderService {
  static final String DB = "com.cencomun.core.db.";
  static final ObjectMapper JSON = new ObjectMapper();
  static final Map<String,String> ROLE_NAMES = Map.of("reader", "CCM Reader", "operator", "CCM Operator",
      "buyer", "CCM Buyer", "manager", "CCM Manager", "director", "CCM Director",
      "simulator", "CCM Simulator", "mcp", "CCM MCP", "selfbuyer", "CCM Selfbuyer", "other", "CCM Other");

  static Model company(JsonNode input) {
    if (!"1".equals(System.getenv("CCM_CORE_LAB"))) throw new CoreFault(404, "LAB workflow disabled");
    if (AuthUtils.getUser() == null) throw new CoreFault(401, "Authentication required");
    Model company = (Model) get(AuthUtils.getUser(), "activeCompany");
    if (company == null || !input.path("company_id").asText().equals(get(company, "code")))
      throw new CoreFault(403, "Company denied");
    return company;
  }
  static Set<String> roles() {
    return ROLE_NAMES.entrySet().stream().filter(e -> AuthUtils.hasRole(AuthUtils.getUser(), e.getValue()))
        .map(Map.Entry::getKey).collect(Collectors.toSet());
  }
  static String encode(Object value) {
    try { return JSON.writeValueAsString(value); }
    catch (Exception error) { throw new IllegalStateException("Native evidence serialization failed", error); }
  }
  private static Object canonical(JsonNode value) {
    if (value.isObject()) {
      Map<String,Object> result = new TreeMap<>();
      value.fields().forEachRemaining(e -> result.put(e.getKey(), canonical(e.getValue()))); return result;
    }
    if (value.isArray()) { List<Object> result = new ArrayList<>(); value.forEach(e -> result.add(canonical(e))); return result; }
    return value;
  }
  static String hash(JsonNode input) {
    try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(encode(canonical(input)).getBytes(StandardCharsets.UTF_8))); }
    catch (java.security.NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
  }
  private static String key(JsonNode input) {
    String value = input.path("request_key").asText();
    if (value.isBlank() || value.length() > 180) throw new CoreFault(422, "Stable request key required");
    return value;
  }
  private Map<String,Object> replay(Model company, String domain, JsonNode input) {
    Model stored = one(DB+"CcmRequestKey", "self.company = ?1 AND self.domain = ?2 AND self.requestKey = ?3", company, domain, key(input));
    if (stored == null) return null;
    if (!hash(input).equals(get(stored, "payloadHash"))) throw new CoreFault(409, "Idempotency payload conflict");
    try {
      Map<String,Object> result = JSON.readValue((String) get(stored, "result"), Map.class);
      result.put("replayed", true); return result;
    } catch (java.io.IOException error) { throw new IllegalStateException("Persisted idempotency result invalid", error); }
  }
  private void remember(Model company, String domain, JsonNode input, Map<String,Object> result) {
    record(DB+"CcmRequestKey", "company", company, "domain", domain, "requestKey", key(input),
        "payloadHash", hash(input), "objectRef", input.path("id").asText(), "result", encode(result));
  }
  /** Company lock serializes creates including competing functional IDs; auth precedes replay. */
  @Transactional(rollbackOn = Exception.class)
  public Map<String,Object> createOrder(JsonNode input) {
    Model company = company(input); CoreOrderPolicy.actor(roles(), "create", "NEW");
    JPA.em().refresh(company, LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> prior = replay(company, "order.create", input); if (prior != null) return prior;
    CoreOrderPolicy.input(input);
    if (one(DB+"CcmOrder", "self.company = ?1 AND self.functionalId = ?2", company, input.path("id").asText()) != null)
      throw new CoreFault(409, "Functional order already exists");
    Model customer = one("com.axelor.apps.base.db.Partner", "self.partnerSeq = ?1", input.path("customer_id").asText());
    if (customer == null || ((java.util.Set<Model>)get(customer,"companySet")).stream().noneMatch(c -> c.getId().equals(company.getId())))
      throw new CoreFault(422,"Native customer does not belong to the fixture company");
    List<Model> lines = new ArrayList<>();
    Model order = create(DB+"CcmOrder");
    set(order, "company", company); set(order, "functionalId", input.get("id").asText());
    setEnum(order, "channel", input.get("channel").asText()); setEnum(order, "state", "NEW");
    set(order, "payload", encode(input)); set(order, "creator", AuthUtils.getUser());
    set(order, "guide", input.path("guide").isNull() ? null : input.path("guide").asText(null));
    for (JsonNode row : input.get("lines")) {
      Model product = one("com.axelor.apps.base.db.Product", "self.code = ?1", row.path("product_id").asText());
      Model profile = product == null ? null : one(NativeIndependentController.PROFILE, "self.company = ?1 AND self.product = ?2", company, product);
      if (profile == null || !Boolean.TRUE.equals(get(profile, "casheaEnabled"))) throw new CoreFault(422, "Product not eligible for Cashea");
      Model line = create(DB+"CcmOrderLine"); set(line, "coreOrder", order); set(line, "product", product);
      set(line, "qty", new BigDecimal(row.get("qty").asText())); set(line, "unitPrice", new BigDecimal(row.get("unit_price").asText())); lines.add(line);
    }
    set(order, "lineList", lines); order = save(order);
    Map<String,Object> result = view(order); result.put("replayed", false);
    remember(company, "order.create", input, result);
    audit(company, order, "order.created", Map.of(), view(order), "Synthetic LAB create", key(input), false);
    return result;
  }

  @Transactional(rollbackOn = Exception.class)
  public Map<String,Object> transition(JsonNode input) throws Exception {
    Model company = company(input); String target = input.path("state").asText();
    CoreOrderPolicy.actor(roles(), "transition", target);
    Model order = one(DB+"CcmOrder", "self.company = ?1 AND self.functionalId = ?2", company, input.path("id").asText());
    if (order == null) throw new CoreFault(404, "Order not found in current company");
    JPA.em().refresh(order, LockModeType.PESSIMISTIC_WRITE);
    Map<String,Object> prior = replay(company, "order.transition", input); if (prior != null) return prior;
    String current = get(order, "state").toString(), channel = get(order, "channel").toString();
    String guide = input.has("guide") ? input.path("guide").asText(null) : (String) get(order, "guide");
    CoreOrderPolicy.transition(channel, current, target, guide);
    String reason = input.path("reason").asText();
    if (reason.isBlank()) throw new CoreFault(422, "Transition reason required");
    Map<String,Object> before = view(order);
    JsonNode payload = JSON.readTree((String) get(order, "payload"));
    NativeGateService nativeFlow = Beans.get(NativeGateService.class);
    NativeGateService.Progress progress = new NativeGateService.Progress();
    if (target.equals("APPROVED")) {
      Model nativeOrder = nativeFlow.approve(progress, payload); order = managed(order); set(order, "saleOrder", nativeOrder);
    } else if (target.equals("FULFILLED") || target.equals("SHIPPED")) {
      ((com.fasterxml.jackson.databind.node.ObjectNode) payload).put("guide", guide);
      Map<String,Model> docs = nativeFlow.deliver(progress, payload, (Model) get(order, "saleOrder"));
      // Explicit LAB failure AFTER real ERP stock/invoice work; outer transaction must roll it all back.
      if (input.path("lab_fail_after_delivery").asBoolean(false)) throw new CoreFault(503, "Synthetic after-native-delivery failure");
      order = managed(order); company = managed(company);
      set(order, "delivery", docs.get("delivery")); set(order, "invoice", docs.get("invoice"));
      NativeFinance.postCost(company, managed((Model) get(docs.get("invoice"), "partner")), docs.get("delivery"), payload);
      order = managed(order);
    } else if (target.equals("SETTLED")) {
      Model invoice = (Model) get(order, "invoice");
      NativeFinance.postSettlement(company, (Model) get(invoice, "partner"), (Model) get(order, "delivery"), invoice, payload);
      if (input.path("lab_fail_after_settlement").asBoolean(false)) throw new CoreFault(503, "Synthetic after-native-settlement failure");
      order = managed(order); company = managed(company);
    } else if (target.equals("CANCELLED") && get(order, "saleOrder") != null) {
      call(service("com.axelor.apps.sale.service.saleorder.status.SaleOrderWorkflowService"), "cancelSaleOrder",
          get(order, "saleOrder"), null, reason);
      order = managed(order);
    }
    setEnum(order, "state", target); set(order, "guide", guide); order = save(order);
    Map<String,Object> result = view(order); result.put("replayed", false); result.put("native_progress", progress.evidence);
    remember(managed(company), "order.transition", input, result);
    audit(managed(company), order, "order.transition", before, view(order), reason, key(input), false);
    if (Set.of("APPROVED", "FULFILLED", "SHIPPED", "SETTLED").contains(target))
      record(DB+"CcmOutboxEvent", "company", managed(company), "coreOrder", order,
          "objectRef", String.valueOf(get(order,"functionalId")), "eventKey", "order:"+order.getId()+":"+target, "kind", "cashea."+target.toLowerCase(), "payload", encode(view(order)));
    return result;
  }

  private void audit(Model company, Model order, String kind, Map<String,Object> before, Map<String,Object> after, String reason, String correlation, boolean rejected) {
    record(DB+"CcmAudit", "company", company, "actor", AuthUtils.getUser(), "actorCode", AuthUtils.getUser().getCode(),
        "objectRef", String.valueOf(get(order, "functionalId")), "kind", kind, "beforeState", encode(before),
        "afterState", encode(after), "reason", reason, "correlation", correlation, "rejected", rejected);
  }
  /** Invoked only by resource AFTER transactional invocation throws/rolls back. */
  @Transactional(rollbackOn = Exception.class)
  public void rejected(JsonNode input, String reason) {
    if (AuthUtils.getUser() == null) return;
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", input.path("company_id").asText());
    if (company == null) return;
    Model order = one(DB+"CcmOrder", "self.company = ?1 AND self.functionalId = ?2", company, input.path("id").asText());
    Map<String,Object> snapshot = order == null ? Map.of() : view(order);
    record(DB+"CcmAudit", "company", company, "actor", AuthUtils.getUser(), "actorCode", AuthUtils.getUser().getCode(),
        "objectRef", input.path("id").asText("invalid"), "kind", "order.denied", "beforeState", encode(snapshot),
        "afterState", encode(snapshot), "reason", reason, "correlation", input.path("request_key").asText("invalid-request"), "rejected", true);
  }
  public static Map<String,Object> view(Model order) {
    Map<String,Object> result = new LinkedHashMap<>();
    result.put("id", get(order, "functionalId")); result.put("native_id", order.getId());
    result.put("company_id", get(get(order, "company"), "code")); result.put("native_company_id", ((Model) get(order, "company")).getId());
    result.put("state", get(order, "state").toString()); result.put("channel", get(order, "channel").toString()); result.put("guide", get(order, "guide"));
    result.put("creator", get(get(order, "creator"), "code"));
    for (String name : List.of("saleOrder", "delivery", "invoice")) {
      Model doc = (Model) get(order, name); result.put(name+"_id", doc == null ? null : doc.getId());
      if (doc != null) result.put(name+"_status", get(doc, "statusSelect"));
    }
    return result;
  }
  public Map<String,Object> inspect(String id) {
    NativeIndependentController.fixtureAdmin();
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", "CCM-LAB-001");
    Model order = one(DB+"CcmOrder", "self.company = ?1 AND self.functionalId = ?2", company, id);
    Map<String,Object> result = new LinkedHashMap<>();
    result.put("order", order == null ? Map.of() : view(order));
    Map<String,Object> nativeExport = Beans.get(NativeGateService.class).inspect(id);
    // Native sequence counters are reserved in an isolated ERP transaction, and are not economic effects.
    nativeExport.remove("sequences"); result.put("native_export", nativeExport);
    result.put("keys", list(DB+"CcmRequestKey", "self.company = ?1 AND self.objectRef = ?2", company, id).stream()
        .map(k -> Map.of("id", k.getId(), "domain", get(k,"domain"), "key", get(k,"requestKey"), "hash", get(k,"payloadHash"))).toList());
    result.put("events", order == null ? List.of() : list(DB+"CcmOutboxEvent", "self.coreOrder = ?1", order).stream()
        .map(e -> Map.of("id", e.getId(), "event_key", get(e,"eventKey"), "kind", get(e,"kind"))).toList());
    result.put("audit", list(DB+"CcmAudit", "self.company = ?1 AND self.objectRef = ?2", company, id).stream().sorted(java.util.Comparator.comparing(Model::getId)).map(a -> {
      Map<String,Object> value = new LinkedHashMap<>(); value.put("id",a.getId()); value.put("actor",get(a,"actorCode"));
      value.put("actor_id",((Model)get(a,"actor")).getId()); value.put("created_on",String.valueOf(get(a,"createdOn")));
      for (String f:List.of("kind","correlation","beforeState","afterState","reason","rejected")) value.put(f,get(a,f)); return value;
    }).toList());
    result.put("read_boundary", "separate-http-after-business-commit-or-rollback"); return result;
  }
}
