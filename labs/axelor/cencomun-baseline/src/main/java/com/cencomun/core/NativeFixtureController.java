package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import static com.cencomun.core.NativeGateService.record;
import com.axelor.db.Model;
import com.axelor.inject.Beans;
import com.axelor.rpc.ActionRequest;
import com.axelor.rpc.ActionResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.google.inject.persist.Transactional;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Native fixture metadata/export only. Role existence does not attest functional permissions. */
public class NativeFixtureController {
  static final Map<String, String> ROLES = Map.of(
      "reader", "CCM Reader", "operator", "CCM Operator", "buyer", "CCM Buyer",
      "manager", "CCM Manager", "director", "CCM Director", "simulator", "CCM Simulator",
      "mcp", "CCM MCP", "selfbuyer", "CCM Selfbuyer", "other", "CCM Other");

  public void prepare(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    response.setValue("core_result", Beans.get(NativeFixtureController.class).prepareRoles());
  }

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> prepareRoles() throws Exception {
    NativeIndependentController.fixtureAdmin();
    FixtureBundle.verify();
    List<String> declared = new ArrayList<>();
    FixtureBundle.json("permissions.json").fieldNames().forEachRemaining(declared::add);
    declared.remove("statuses");
    if (!ROLES.keySet().equals(new java.util.HashSet<>(declared)))
      throw new IllegalStateException("Frozen fixture role mapping differs");
    for (String name : ROLES.values()) {
      if (one("com.axelor.auth.db.Role", "self.name = ?1", name) == null)
        record("com.axelor.auth.db.Role", "name", name,
            "description", "Synthetic LAB fixture role; functional permissions tested separately");
    }
    // No users, passwords or permission grants are added or changed.
    return Map.of("role_metadata_count", ROLES.size(), "permissions_changed", false);
  }

  public void inspect(ActionRequest request, ActionResponse response) throws Exception {
    NativeIndependentController.fixtureAdmin();
    FixtureBundle.verify();
    Model company = one("com.axelor.apps.base.db.Company", "self.code = ?1", "CCM-LAB-001");
    if (company == null) throw new IllegalStateException("Native fixture company missing");
    Map<String, Object> result = new LinkedHashMap<>();
    List<Map<String, Object>> hashes = new ArrayList<>();
    for (JsonNode entry : FixtureBundle.json("manifest.json").get("files")) {
      String file = entry.get("path").asText(); byte[] value = FixtureBundle.bytes(file);
      hashes.add(Map.of("file", file, "bytes", value.length, "sha256", FixtureBundle.sha(value)));
    }
    result.put("integrity", Map.of("reference", FixtureBundle.REFERENCE,
        "manifest_sha256", FixtureBundle.sha(FixtureBundle.bytes("manifest.json")), "hashes", hashes));
    result.put("company", Map.of("native_id", company.getId(), "code", get(company, "code")));
    List<Map<String, Object>> products = new ArrayList<>();
    for (Model profile : list(NativeIndependentController.PROFILE, "self.company = ?1", company)) {
      Model product = (Model) get(profile, "product");
      Map<String, Object> item = new LinkedHashMap<>();
      item.put("native_id", product.getId()); item.put("native_profile_id", profile.getId());
      item.put("native_company_id", ((Model) get(profile, "company")).getId());
      item.put("id", get(product, "code")); item.put("name", get(product, "name"));
      item.put("price", get(product, "salePrice").toString());
      item.put("cashea_price", get(profile, "casheaPrice").toString());
      for (String[] fields : new String[][] {{"marketplace_enabled", "marketplaceEnabled"},
          {"cashea_enabled", "casheaEnabled"}, {"supplier_reference", "supplierReference"},
          {"warranty_quantity", "warrantyQuantity"}}) item.put(fields[0], get(profile, fields[1]));
      item.put("warranty_unit", get(profile, "warrantyUnit").toString());
      item.put("condition", get(profile, "condition").toString());
      products.add(item);
    }
    result.put("products", products);
    List<Map<String, Object>> customers = new ArrayList<>();
    for (Model partner : list("com.axelor.apps.base.db.Partner", "self.partnerSeq in (?1, ?2, ?3)", "C001", "C002", "CBANK")) {
      Model email = (Model) get(partner, "emailAddress");
      customers.add(Map.of("native_id", partner.getId(), "id", get(partner, "partnerSeq"),
          "name", get(partner, "name"), "email", get(email, "address"), "phone", get(partner, "mobilePhone"),
          "native_company_ids", ((java.util.Set<Model>) get(partner, "companySet")).stream().map(Model::getId).toList()));
    }
    result.put("customers", customers);
    List<Map<String, Object>> roles = new ArrayList<>();
    for (Map.Entry<String, String> entry : ROLES.entrySet()) {
      Model role = one("com.axelor.auth.db.Role", "self.name = ?1", entry.getValue());
      if (role != null) roles.add(Map.of("native_id", role.getId(), "fixture_role", entry.getKey(), "name", get(role, "name")));
    }
    result.put("roles", roles);
    List<Map<String, Object>> currencies = new ArrayList<>();
    for (Model currency : list("com.axelor.apps.base.db.Currency", "self.codeISO in (?1, ?2)", "USD", "VES"))
      currencies.add(Map.of("native_id", currency.getId(), "code", get(currency, "codeISO"),
          "decimals", get(currency, "numberOfDecimals")));
    result.put("currencies", currencies);
    response.setValue("core_result", result);
  }
}
