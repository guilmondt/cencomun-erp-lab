package com.cencomun.core;

import static org.junit.jupiter.api.Assertions.*;
import java.util.Set;
import org.junit.jupiter.api.Test;

class CoreFinancePolicyTest {
  @Test void mcpDraftDoesNotAuthorizeFinanceOrPurchaseProgression() {
    CoreFinancePolicy.actor(Set.of("mcp"),"purchase.create");
    for(String operation: Set.of("purchase.request","purchase.revise","cash.prepare","bank.import")) {
      assertEquals(403,assertThrows(CoreFault.class,()->CoreFinancePolicy.actor(Set.of("mcp"),operation)).status);
      CoreFinancePolicy.actor(Set.of("operator"),operation);
    }
  }
  @Test void privateReadsAreNotBusinessReads() {
    for(String role:Set.of("reader","mcp","operator","buyer","director","simulator","other"))
      assertFalse(CoreFinancePolicy.privateRead(Set.of(role)),role);
    assertTrue(CoreFinancePolicy.privateRead(Set.of("manager")));
    CoreOrderPolicy.actor(Set.of("mcp"),"create","NEW");
  }
}
