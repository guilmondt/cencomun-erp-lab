package com.cencomun.core;

import java.util.Set;

/** Fixed LAB authority: MCP can create a purchase draft, never operate finance. */
public final class CoreFinancePolicy {
  public static void actor(Set<String> roles, String operation) {
    Set<String> allowed = operation.equals("purchase.create")
        ? Set.of("operator", "mcp") : Set.of("operator");
    if (roles.stream().noneMatch(allowed::contains))
      throw new CoreFault(403, "Role denied for " + operation);
  }
  public static boolean privateRead(Set<String> roles) { return roles.contains("manager"); }
  private CoreFinancePolicy() {}
}
