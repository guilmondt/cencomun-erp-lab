package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.axelor.apps.base.AxelorException;
import com.axelor.apps.base.db.Address;
import com.axelor.apps.base.db.AddressTemplate;
import com.axelor.apps.base.db.Country;
import com.axelor.apps.base.db.City;
import com.axelor.apps.base.service.address.AddressServiceImpl;
import com.axelor.apps.base.service.address.AddressTemplateServiceImpl;
import com.axelor.db.Model;
import com.axelor.meta.db.MetaField;
import com.axelor.meta.db.MetaModel;
import com.axelor.inject.Beans;
import com.google.inject.Guice;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/** Runs the actual fixed AOS callback without pretending to test database persistence. */
class NativeAddressTemplateTest {
  private Map<String, Model> metadata() {
    MetaModel model = new MetaModel(); model.setName("Address");
    model.setFullName(Address.class.getName());
    Map<String, Model> fields = new LinkedHashMap<>();
    for (String name : new String[] {"floor", "streetName", "postBox", "city", "zip"}) {
      MetaField field = new MetaField(); field.setName(name); field.setMetaModel(model);
      fields.put(name, field);
    }
    return fields; // Unsaved test objects only; production lookup requires real persisted metadata.
  }

  private AddressTemplate template() {
    return (AddressTemplate) NativeFinance.addressTemplate(metadata());
  }

  @BeforeAll static void initializeNativeTemplateContainer() {
    Guice.createInjector().getInstance(Beans.class);
  }

  private Address address(AddressTemplate template) {
    Country country = new Country(); country.setAddressTemplate(template);
    Address address = new Address(); address.setCountry(country);
    address.setSubDepartment("Synthetic LAB customer");
    address.setStreetName("1 Synthetic LAB Street");
    City city = new City(); city.setName("Synthetic LAB City"); city.setCountry(country);
    address.setCity(city); address.setZip("00000");
    return address;
  }

  @Test void fixtureRendersEveryNativeLineIncludingUnusedLines() throws Exception {
    AddressTemplate template = template();
    Address address = address(template);
    AddressTemplateServiceImpl service = new AddressTemplateServiceImpl(null);
    service.setFormattedFullName(address);
    address.setFullName(new AddressServiceImpl(null, null).computeFullName(address).toUpperCase());
    service.checkRequiredAddressFields(address);
    assertEquals("Synthetic LAB customer\n1 Synthetic LAB Street\nSynthetic LAB City 00000", address.getFormattedFullName());
    assertEquals("SYNTHETIC LAB CUSTOMER 1 SYNTHETIC LAB STREET SYNTHETIC LAB CITY 00000", address.getFullName());
    assertEquals("", address.getAddressL3());
    assertEquals("", address.getAddressL5());
    assertEquals(5, template.getAddressTemplateLineList().size());
    assertEquals(Set.of("streetName", "city", "zip"), template.getAddressTemplateLineList().stream()
        .filter(line -> line.getIsRequired()).map(line -> line.getMetaField().getName()).collect(java.util.stream.Collectors.toSet()));
    template.getAddressTemplateLineList().forEach(line -> assertSame(template, line.getAddressTemplate()));
  }

  @Test void missingLineTemplateReproducesTheNativePreparationFailure() {
    AddressTemplate template = template();
    template.setAddressL2Str(null);
    AxelorException failure = assertThrows(AxelorException.class,
        () -> new AddressTemplateServiceImpl(null).setFormattedFullName(address(template)));
    assertInstanceOf(NullPointerException.class, failure.getCause());
  }

  @Test void missingRequiredFieldCollectionReproducesTheNextNativeFailure() {
    AddressTemplate template = template();
    template.setAddressTemplateLineList(null);
    assertThrows(NullPointerException.class,
        () -> new AddressTemplateServiceImpl(null).checkRequiredAddressFields(address(template)));
  }

  @ParameterizedTest @ValueSource(strings = {"streetName", "city", "zip"})
  void fixtureCannotBypassAnyOfficialRequiredField(String field) {
    Address address = address(template());
    NativeAccess.set(address, field, null);
    assertThrows(AxelorException.class,
        () -> new AddressTemplateServiceImpl(null).checkRequiredAddressFields(address));
  }

  @Test void missingRequiredMetadataReproducesTheNativeFailure() {
    AddressTemplate template = template();
    template.getAddressTemplateLineList().stream().filter(line -> line.getIsRequired())
        .findFirst().orElseThrow().setMetaField(null);
    assertThrows(NullPointerException.class,
        () -> new AddressTemplateServiceImpl(null).checkRequiredAddressFields(address(template)));
  }

  @Test void fixtureRejectsIncompleteMetadataBeforeAnySave() {
    Map<String, Model> fields = metadata(); fields.remove("streetName");
    assertThrows(IllegalStateException.class, () -> NativeFinance.addressTemplate(fields));
  }
}
