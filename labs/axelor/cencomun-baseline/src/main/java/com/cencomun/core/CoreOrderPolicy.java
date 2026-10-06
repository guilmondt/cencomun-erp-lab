package com.cencomun.core;

import com.fasterxml.jackson.databind.JsonNode;
import java.math.BigDecimal;
import java.util.Set;

/** Frozen LAB state/role contract. ERP effects remain in native services. */
public final class CoreOrderPolicy {
  private static final Set<String> STATES = Set.of("NEW", "REVIEWED", "APPROVED", "PREPARING", "FULFILLED", "SHIPPED", "SETTLED", "REJECTED", "CANCELLED");
  public static void actor(Set<String> roles, String operation, String target) {
    Set<String> allowed = operation.equals("create") ? Set.of("operator", "mcp")
        : Set.of("PREPARING", "FULFILLED", "SHIPPED").contains(target) ? Set.of("operator") : Set.of("simulator");
    if (roles.stream().noneMatch(allowed::contains)) throw new CoreFault(403, "Role denied for " + operation + ": " + target);
  }
  public static void transition(String channel, String current, String target, String guide) {
    if (!STATES.contains(target)) throw new CoreFault(409, "Unknown order state");
    boolean allowed = switch (target) {
      case "REVIEWED" -> current.equals("NEW");
      case "APPROVED" -> current.equals("REVIEWED");
      case "PREPARING" -> channel.equals("WEB") && current.equals("APPROVED");
      case "FULFILLED" -> channel.equals("STORE") && current.equals("APPROVED");
      case "SHIPPED" -> channel.equals("WEB") && current.equals("PREPARING");
      case "SETTLED" -> channel.equals("STORE") ? current.equals("FULFILLED") : current.equals("SHIPPED");
      case "REJECTED" -> Set.of("NEW", "REVIEWED").contains(current);
      case "CANCELLED" -> Set.of("NEW", "REVIEWED", "APPROVED").contains(current) || channel.equals("WEB") && current.equals("PREPARING");
      default -> false;
    };
    if (!allowed) throw new CoreFault(409, "Order transition conflict: " + current + " -> " + target);
    if (target.equals("SHIPPED") && (guide == null || guide.isBlank())) throw new CoreFault(422, "WEB dispatch requires guide");
  }
  public static void input(JsonNode input) {
    if (!input.path("id").asText().matches("[A-Z0-9][A-Z0-9-]{0,79}")) throw new CoreFault(422, "Invalid functional order ID");
    if (!Set.of("STORE", "WEB").contains(input.path("channel").asText())) throw new CoreFault(422, "Invalid channel");
    if (!input.path("currency").asText().equals("USD")) throw new CoreFault(422, "Economic order requires its native USD fixture currency");
    if (!input.path("lines").isArray() || input.get("lines").isEmpty()) throw new CoreFault(422, "Order lines required");
    BigDecimal gross = BigDecimal.ZERO;
    for (JsonNode line : input.get("lines")) {
      BigDecimal qty = number(line, "qty"), price = number(line, "unit_price");
      if (qty.signum() <= 0 || qty.stripTrailingZeros().scale() > 0) throw new CoreFault(422, "Quantity must be a positive integer");
      if (price.signum() <= 0 || price.stripTrailingZeros().scale() > 2) throw new CoreFault(422, "Positive price with at most two decimals required");
      gross = gross.add(qty.multiply(price));
    }
    BigDecimal tax = number(input, "tax_rate"), financed = number(input, "financed_amount"), shipping = number(input, "shipping_expense");
    if (!Set.of(BigDecimal.ZERO, new BigDecimal("0.1")).contains(tax.stripTrailingZeros())) throw new CoreFault(422, "Unsupported LAB tax rate");
    if (financed.signum() < 0 || financed.compareTo(gross) > 0 || financed.stripTrailingZeros().scale() > 2 || shipping.signum() < 0 || shipping.stripTrailingZeros().scale() > 2)
      throw new CoreFault(422, "Invalid financed amount or shipping expense");
  }
  private static BigDecimal number(JsonNode node, String field) {
    try { return new BigDecimal(node.path(field).asText()); }
    catch (NumberFormatException error) { throw new CoreFault(422, "Invalid decimal: " + field); }
  }
  private CoreOrderPolicy() {}
}
