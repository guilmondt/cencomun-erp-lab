package com.cencomun.baseline.module;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.axelor.app.AxelorModule;
import com.google.inject.Guice;
import com.google.inject.Stage;
import java.util.Properties;
import org.junit.jupiter.api.Test;

class CencomunModuleTest {

  @Test
  void registersWithThePlatformInjectorWithoutADatabase() {
    var injector = Guice.createInjector(Stage.PRODUCTION, new CencomunModule());
    assertInstanceOf(AxelorModule.class, injector.getInstance(CencomunModule.class));
  }

  @Test
  void generatedMetadataIdentifiesTheCustomModule() throws Exception {
    var resources = getClass().getClassLoader().getResources("META-INF/axelor-module.properties");
    Properties module = null;
    int matches = 0;
    while (resources.hasMoreElements()) {
      var properties = new Properties();
      try (var stream = resources.nextElement().openStream()) {
        properties.load(stream);
      }
      if ("cencomun-baseline".equals(properties.getProperty("name"))) {
        module = properties;
        matches++;
      }
    }
    assertEquals(1, matches, "The generated module must be discoverable exactly once");
    assertNotNull(module);
    assertEquals("com.cencomun", module.getProperty("mavenGroup"));
    assertEquals("0.1.0", module.getProperty("version"));
    assertEquals("Cencomun Baseline", module.getProperty("title"));
  }
}
