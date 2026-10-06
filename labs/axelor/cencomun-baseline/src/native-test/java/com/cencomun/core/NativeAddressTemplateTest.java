package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import com.axelor.apps.base.AxelorException;
import com.axelor.apps.base.db.Address;
import com.axelor.apps.base.db.AddressTemplate;
import com.axelor.apps.base.db.Country;
import com.axelor.apps.base.service.address.AddressTemplateServiceImpl;
import com.axelor.inject.Beans;
import com.google.inject.Guice;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Runs the actual fixed AOS callback without pretending to test database persistence. */
class NativeAddressTemplateTest {
  @BeforeAll static void initializeNativeTemplateContainer() {
    Guice.createInjector().getInstance(Beans.class);
  }

  private Address address(AddressTemplate template) {
    Country country = new Country(); country.setAddressTemplate(template);
    Address address = new Address(); address.setCountry(country);
    address.setAddressL2("Synthetic LAB customer");
    address.setAddressL4("1 Synthetic LAB Street");
    address.setAddressL6("Synthetic LAB City");
    return address;
  }

  @Test void fixtureRendersEveryNativeLineIncludingUnusedLines() throws Exception {
    Address address = address((AddressTemplate) NativeFinance.addressTemplate());
    new AddressTemplateServiceImpl(null).setFormattedFullName(address);
    assertEquals("Synthetic LAB customer\n1 Synthetic LAB Street\nSynthetic LAB City", address.getFormattedFullName());
    assertEquals("", address.getAddressL3());
    assertEquals("", address.getAddressL5());
  }

  @Test void missingLineTemplateReproducesTheNativePreparationFailure() {
    AddressTemplate template = (AddressTemplate) NativeFinance.addressTemplate();
    template.setAddressL2Str(null);
    AxelorException failure = assertThrows(AxelorException.class,
        () -> new AddressTemplateServiceImpl(null).setFormattedFullName(address(template)));
    assertInstanceOf(NullPointerException.class, failure.getCause());
  }
}
