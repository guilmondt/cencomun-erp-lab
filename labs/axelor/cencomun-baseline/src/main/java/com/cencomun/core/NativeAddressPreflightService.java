package com.cencomun.core;

import static com.cencomun.core.NativeAccess.*;
import com.axelor.db.JpaRepository;
import com.axelor.db.Model;
import com.google.inject.persist.Transactional;
import java.util.List;
import java.util.Map;

/** Fixture-only address save, independent of stock, invoices and economic gates. */
public class NativeAddressPreflightService {
  private static final String ADDRESS = "com.axelor.apps.base.db.Address";
  private static final String RECIPIENT = "Synthetic LAB preflight";

  @Transactional(rollbackOn = Exception.class)
  public Map<String, Object> prepare() {
    Model address = one(ADDRESS, "self.subDepartment = ?1", RECIPIENT);
    if (address == null) address = NativeFinance.address(NativeFinance.addressCountry(), RECIPIENT);
    return Map.of("address_id", address.getId(), "repository", JpaRepository.of(type(ADDRESS)).getClass().getName());
  }

  public Map<String, Object> inspect() {
    Model address = one(ADDRESS, "self.subDepartment = ?1", RECIPIENT);
    if (address == null || address.getId() == null) throw new IllegalStateException("Address preflight did not commit");
    Model country = (Model) get(address, "country");
    Model template = (Model) get(country, "addressTemplate");
    List<Map<String, Object>> lines = ((List<?>) get(template, "addressTemplateLineList")).stream().map(item -> {
      Model line = (Model) item; Model metadata = (Model) get(line, "metaField");
      return Map.<String, Object>of("id", line.getId(), "field_id", metadata.getId(),
          "field", get(metadata, "name"), "model", get(get(metadata, "metaModel"), "fullName"),
          "required", get(line, "isRequired"), "template_id", ((Model) get(line, "addressTemplate")).getId());
    }).toList();
    return Map.of("address_id", address.getId(), "template_id", template.getId(), "country_id", country.getId(),
        "street", get(address, "streetName"), "city", get(get(address, "city"), "name"), "zip", get(address, "zip"),
        "full_name", get(address, "fullName"), "formatted_full_name", get(address, "formattedFullName"),
        "lines", lines, "read_boundary", "separate-http-after-address-commit");
  }
}
