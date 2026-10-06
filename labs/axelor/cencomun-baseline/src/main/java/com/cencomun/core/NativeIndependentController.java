package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.auth.AuthService;
import com.axelor.auth.AuthUtils;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Fixture-only setup; acceptance writes use authenticated native REST and native repositories. */
public class NativeIndependentController {
  public static final String PROFILE = "com.cencomun.core.db.CcmProductProfile";
  static void fixtureAdmin() {
    if (!"1".equals(System.getenv("CCM_CORE_LAB")) || AuthUtils.getUser() == null
        || !"admin".equals(AuthUtils.getUser().getCode()))
      throw new SecurityException("Synthetic fixture setup requires the LAB administrator");
  }
  public void prepareProducts(ActionRequest request, ActionResponse response) throws Exception {
    fixtureAdmin();
    NativeGateService.Progress progress = new NativeGateService.Progress();
    NativeGateService fixtures = Beans.get(NativeGateService.class);
    fixtures.activate(progress);
    // Independent of either gate's receipt/sale result: preparation consumes no sequence.
    fixtures.prepare(progress, "PROD");
    response.setValue("core_result", Beans.get(NativeIndependentController.class).configureProducts());
  }

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> configureProducts() throws Exception {
    fixtureAdmin();
    FixtureBundle.verify();
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", "CCM-LAB-001");
    List<Map<String, Object>> profiles = new ArrayList<>();
    for (JsonNode input : FixtureBundle.json("products.json")) {
      Model product = one("com.axelor.apps.base.db.Product", "self.code = ?1", input.get("id").asText());
      Model profile = one(PROFILE, "self.company = ?1 AND self.product = ?2", company, product);
      if (profile == null) {
        profile = create(PROFILE);
        set(profile, "company", company); set(profile, "product", product);
        set(profile, "marketplaceEnabled", input.get("marketplace_enabled").asBoolean());
        set(profile, "casheaEnabled", input.get("cashea_enabled").asBoolean());
        set(profile, "casheaPrice", new BigDecimal(input.get("price").asText()));
        set(profile, "supplierReference", input.get("supplier_reference").asText());
        set(profile, "warrantyQuantity", input.get("warranty_quantity").asInt());
        setEnum(profile, "warrantyUnit", input.get("warranty_unit").asText());
        setEnum(profile, "condition", input.get("condition").asText());
        profile = save(profile);
      }
      profiles.add(Map.of("id", profile.getId(), "product_id", product.getId(), "product_code", get(product, "code")));
    }
    Model role = one("com.axelor.auth.db.Role", "self.name = ?1", "CCM Operator");
    if (role == null) role = record("com.axelor.auth.db.Role", "name", "CCM Operator", "description", "Synthetic Core operator");
    Model permission = one("com.axelor.auth.db.Permission", "self.name = ?1", "ccm.lab.product.profile.operator");
    if (permission == null) permission = record("com.axelor.auth.db.Permission",
        "name", "ccm.lab.product.profile.operator", "object", PROFILE,
        "canRead", true, "canWrite", true, "canCreate", false, "canRemove", false,
        "condition", "self.company.id = ?1", "conditionParams", "__user__.activeCompany.id");
    set(permission, "condition", "self.company.id = ?1");
    set(permission, "conditionParams", "__user__.activeCompany.id"); save(permission);
    set(role, "permissions", new HashSet<>(List.of(permission))); save(role);
    Model user = one("com.axelor.auth.db.User", "self.code = ?1", "ccm-operator");
    if (user == null) user = record("com.axelor.auth.db.User", "code", "ccm-operator", "name", "Synthetic Core Operator",
        "password", AuthService.getInstance().encrypt("CoreLab-operator-2026!"), "email", "operator@example.invalid");
    set(user, "roles", new HashSet<>(List.of(role)));
    // AOS overrides AOP's new-user default to blocked=true; only these LAB users
    // are explicitly activated by the authenticated fixture administrator.
    set(user, "blocked", false);
    set(user, "activeCompany", company); set(user, "companySet", new HashSet<>(List.of(company))); save(user);
    Model readerRole = one("com.axelor.auth.db.Role", "self.name = ?1", "CCM Reader");
    if (readerRole == null) readerRole = record("com.axelor.auth.db.Role", "name", "CCM Reader");
    List<Model> reads = new ArrayList<>();
    reads.add(readPermission("profile", PROFILE, "self.company.id = ?1"));
    reads.add(readPermission("partner", "com.axelor.apps.base.db.Partner",
        "self.id IN (SELECT p.id FROM Partner p JOIN p.companySet c WHERE c.id = ?1)"));
    reads.add(readPermission("invoice", "com.axelor.apps.account.db.Invoice", "self.company.id = ?1"));
    reads.add(readPermission("serial", "com.axelor.apps.stock.db.TrackingNumber",
        "EXISTS (SELECT p FROM CcmProductProfile p WHERE p.product = self.product AND p.company.id = ?1)"));
    set(readerRole, "permissions", new HashSet<>(reads)); save(readerRole);
    Model reader = one("com.axelor.auth.db.User", "self.code = ?1", "ccm-reader");
    if (reader == null) reader = record("com.axelor.auth.db.User", "code", "ccm-reader", "name", "Synthetic Core Reader",
        "password", AuthService.getInstance().encrypt("CoreLab-reader-2026!"), "email", "reader@example.invalid");
    set(reader, "roles", new HashSet<>(List.of(readerRole)));
    set(reader, "blocked", false);
    set(reader, "activeCompany", company); set(reader, "companySet", new HashSet<>(List.of(company))); save(reader);
    String serial = FixtureBundle.json("scenarios.json").get("search").get("serial").get("reference").asText();
    if (one("com.axelor.apps.stock.db.TrackingNumber", "self.trackingNumberSeq = ?1", serial) == null)
      record("com.axelor.apps.stock.db.TrackingNumber", "trackingNumberSeq", serial, "serialNumber", serial,
          "product", one("com.axelor.apps.base.db.Product", "self.code = ?1", "P001"));
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("profiles", profiles); result.put("company_id", company.getId());
    result.put("operator_user_id", user.getId()); result.put("operator_role_id", role.getId());
    result.put("native_permission_id", permission.getId());
    return result;
  }
  public void inspectProducts(ActionRequest request, ActionResponse response) {
    fixtureAdmin();
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", "CCM-LAB-001");
    List<Map<String, Object>> profiles = new ArrayList<>();
    for (Model profile : list(PROFILE, "self.company = ?1", company)) {
      Model product = (Model) get(profile, "product");
      profiles.add(Map.of("id", profile.getId(), "company_id", company.getId(),
          "product_id", product.getId(), "product_code", get(product, "code")));
    }
    List<Map<String, Object>> users = new ArrayList<>();
    for (String code : List.of("ccm-operator", "ccm-reader")) {
      com.axelor.auth.db.User user = (com.axelor.auth.db.User) one("com.axelor.auth.db.User", "self.code = ?1", code);
      if (user == null) throw new IllegalStateException("Committed fixture user missing: " + code);
      String password = code.equals("ccm-operator") ? "CoreLab-operator-2026!" : "CoreLab-reader-2026!";
      String role = code.equals("ccm-operator") ? "CCM Operator" : "CCM Reader";
      users.add(Map.of("id", user.getId(), "code", code, "active", AuthUtils.isActive(user),
          "blocked", user.getBlocked(), "role", role, "native_role_present", AuthUtils.hasRole(user, role),
          "credentials_match", AuthService.getInstance().match(password, user.getPassword()),
          "company_id", ((Model) get(user, "activeCompany")).getId()));
    }
    List<Map<String, Object>> customers = new ArrayList<>();
    for (Model partner : list("com.axelor.apps.base.db.Partner", "self.partnerSeq in (?1, ?2, ?3)", "C001", "C002", "CBANK"))
      customers.add(Map.of("id", partner.getId(), "code", get(partner, "partnerSeq"),
          "name", get(partner, "name"), "mobile_phone", get(partner, "mobilePhone"),
          "company_ids", ((java.util.Set<Model>) get(partner, "companySet")).stream().map(Model::getId).toList()));
    response.setValue("core_result", Map.of("company_id", company.getId(), "profiles", profiles, "users", users, "customers", customers));
  }
  private Model readPermission(String label, String model, String condition) {
    String name = "ccm.lab.reader." + label;
    Model found = one("com.axelor.auth.db.Permission", "self.name = ?1", name);
    if (found == null) found = record("com.axelor.auth.db.Permission", "name", name, "object", model,
        "canRead", true, "canWrite", false, "canCreate", false, "canRemove", false,
        "condition", condition, "conditionParams", "__user__.activeCompany.id");
    set(found, "condition", condition);
    set(found, "conditionParams", "__user__.activeCompany.id");
    return save(found);
  }
}
